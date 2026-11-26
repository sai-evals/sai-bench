"""Q2 (#7), voice scenario: score every reply on the user's voice, and report whether a voice correction sticks.

Per reply (the draft only; a "here's a draft" preamble and trailing notes are cut first, see `draft`):
  rules   five yes/no checks from the samples, no judge: lowercase, no "!", no dashes, no stock pleasantries,
          80 words or fewer. Score = how many pass (0-5). The sign-off ("thx, jo") is reported separately, on the
          email turns only (turn 2 is a Slack message, where a sign-off isn't expected).
  judge   1-5 "sounds like the samples" (rubric in scenarios/voice-*/rubric.md), one Haiku call; it sees the samples,
          the user's messages so far and the draft, never the other arms.
Then, as in drift.py: the control is the default level; a corrected run drifts back if a later turn scores at least
2 rules (or 1 judge point) below its own turn-1 level.

The rule list borrows from the deslop toolkit's habit list (em dashes, stock phrases), cut down to what this voice rules out.

Usage:
  python3 correction-cost/bench/voice_score.py --target anthropic:claude-haiku-5-5 --judge anthropic:claude-haiku-5-5
  python3 correction-cost/bench/voice_score.py --target ... --report
"""
import argparse, json, os, random, re, statistics, sys
from concurrent.futures import ThreadPoolExecutor
from providers import chat, LAST
from runner import REPO, load_scenario, safe

ARMS = ["corrected", "control", "note", "nosamples"]
STOCK = re.compile(r"\b(hope (this|you|all|that)|thrilled|delighted|excited|don'?t hesitate|do not hesitate|"
                   r"please let me know|feel free|reach(ing)? out|just wanted to|looking forward|happy to help|"
                   r"great news|best regards|kind regards|warm regards|sincerely|many thanks|thank you so much|"
                   r"appreciate (your|you)|absolutely|wonderful|fantastic|amazing)\b", re.I)
DASH = re.compile(r"[—–]|(?<=\s)-(?=\s)")
SIGNOFF = re.compile(r"thx,?\s*\n?\s*jo\s*$", re.I)
GREETING = re.compile(r"^\s*(\*\*)?\s*(hey|hi|hello|dear|good (morning|afternoon)|subject:|@?sam\b|priya\b)", re.I)
AFTER = re.compile(r"^\s*(---|\*\*\*|want me|would you like|let me know if you|i can also|i kept|i've kept|i made|"
                   r"notes?:|note that|a few (notes|changes)|changes:|this version|this keeps|tweaks?:)", re.I)
RULES = ["lowercase", "no_exclaim", "no_dash", "no_stock", "short"]  # core score; "signoff" reported separately
EMAIL_TURNS = (0, 1, 3, 4)


def draft(text):
    """The draft inside a reply. Strategy, in order: a fenced or quoted block; else from the first greeting line to the
    sign-off (or to the first line that reads like a note after the draft); else the reply minus a one-line preamble."""
    t = (text or "").strip()
    m = re.search(r"```[a-z]*\n(.+?)```", t, re.S)
    if m:
        return m.group(1).strip(), "fence"
    q = [l[1:].lstrip() for l in t.splitlines() if l.startswith(">")]
    if len(q) >= 2:
        return "\n".join(q).strip(), "quote"
    lines = t.splitlines()
    start = next((i for i, l in enumerate(lines) if GREETING.match(l)), None)
    if start is None and lines and lines[0].rstrip().endswith(":"):
        start = 1
    if start is None:
        return t, "whole"
    out = []
    for l in lines[start:]:
        if out and AFTER.match(l):
            break
        out.append(l)
        if re.search(r"\bjo\s*\**\s*$", l, re.I):
            break
    return "\n".join(out).strip().strip("*").strip(), "greeting"


def rules(d):
    words = re.findall(r"[A-Za-z']+", d)
    return {"lowercase": not re.search(r"[A-Z]", d), "no_exclaim": "!" not in d, "no_dash": not DASH.search(d),
            "no_stock": not STOCK.search(d), "signoff": bool(SIGNOFF.search(d.strip().strip("*").strip())),
            "short": len(words) <= 80}


SYSTEM = "You score one draft. Reply with JSON only."
PROMPT = """A user asked an assistant to write in the user's own voice. These are three emails the user wrote:
<samples>
{samples}
</samples>

The user's messages so far:
{users}

The draft the assistant wrote for the latest message (only the draft; any explanation around it was removed):
<draft>
{draft}
</draft>

{rubric}

Return JSON: {{"score": 1-5, "reason": "<one sentence naming what matches or doesn't>"}}"""


def rubric_text():
    t = open(os.path.join(REPO, "correction-cost", "scenarios", "voice-corrected", "rubric.md")).read()
    return "## voice" + t.split("## voice", 1)[1]


def parse_json(text):
    found, dec = None, json.JSONDecoder()
    for i, ch in enumerate(text or ""):
        if ch == "{":
            try:
                d, _ = dec.raw_decode(text, i)
                if isinstance(d, dict) and "score" in d:
                    found = d
            except Exception:
                pass
    return found


def ask(judge, prompt):
    provider, model = judge.split(":", 1)
    if provider == "mock":
        return {"score": random.Random(len(prompt)).randint(1, 5), "reason": "mock"}
    for _ in range(3):
        LAST.clear()
        d = parse_json(chat(provider, model, [{"role": "user", "content": prompt}], system=SYSTEM)[0])
        if d and str(d.get("score")).isdigit() and 1 <= int(d["score"]) <= 5:
            return d
    return None


def paths(arm, target, judge):
    d = os.path.join(REPO, "results", f"voice-{arm}")
    return os.path.join(d, f"convos__{safe(target)}.jsonl"), os.path.join(d, f"voicejudged__{safe(target)}__by__{safe(judge)}.jsonl")


def judge_arm(arm, target, judge):
    src, out = paths(arm, target, judge)
    if not os.path.exists(src):
        print(f"skip {arm}: no transcripts"); return
    samples, rub = load_scenario("voice-corrected")["samples"], rubric_text()
    done = {(r["run"], r["turn"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    jobs = []
    for k, cv in enumerate(map(json.loads, open(src))):
        run = cv.get("run", k)
        for t in cv["turns"]:
            if (run, t["turn"]) in done:
                continue
            d, how = draft(t["assistant"])
            users = "\n".join(f"{i + 1}. {x['user']}" for i, x in enumerate(cv["turns"][:t["turn"] + 1]))
            jobs.append((run, t["turn"], d, how, users))

    def one(j):
        run, turn, d, how, users = j
        res = ask(judge, PROMPT.format(samples=samples, users=users, draft=d, rubric=rub)) or {}
        return {"arm": arm, "run": run, "turn": turn, "extract": how, "draft": d, "rules": rules(d),
                "judge": int(res["score"]) if res.get("score") else None, "reason": res.get("reason")}

    with ThreadPoolExecutor(6) as ex, open(out, "a") as f:
        for r in ex.map(one, jobs):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{arm}: {len(jobs)} judged", flush=True)


def boot(xs, n=2000):
    if len(xs) < 2:
        return None, None
    rnd = random.Random(0)
    m = sorted(statistics.mean(rnd.choices(xs, k=len(xs))) for _ in range(n))
    return m[int(.025 * n)], m[int(.975 * n) - 1]


def report(target, judge):
    data = {}
    for arm in ARMS:
        _, out = paths(arm, target, judge)
        data[arm] = [json.loads(l) for l in open(out)] if os.path.exists(out) else []
    n_rules = lambda r: sum(r["rules"][k] for k in RULES)
    print(f"\n{target}, judged by {judge}")
    print("\nCore rules passed (0-5), mean [95% CI] / judge (1-5) mean, per arm and turn:")
    turns = sorted({r["turn"] for a in ARMS for r in data[a]})
    print(f"{'arm':<11}" + "".join(f"{'turn ' + str(t):>24}" for t in turns))
    for arm in ARMS:
        cells = []
        for t in turns:
            rs = [r for r in data[arm] if r["turn"] == t]
            if not rs:
                cells.append("-"); continue
            x = [n_rules(r) for r in rs]; lo, hi = boot(x)
            j = [r["judge"] for r in rs if r["judge"]]
            cells.append(f"{statistics.mean(x):.1f} [{lo:.1f},{hi:.1f}] / {statistics.mean(j):.1f}" if j else f"{statistics.mean(x):.1f}")
        print(f"{arm:<11}" + "".join(f"{c:>24}" for c in cells))
    print("\nEach rule, % of drafts passing (turns 0 / 1 / 2 / 3 / 4; signoff is not expected at turn 2, the Slack message):")
    for arm in ARMS:
        for rule in RULES + ["signoff"]:
            v = [100 * statistics.mean([r["rules"][rule] for r in data[arm] if r["turn"] == t]) for t in turns
                 if any(r["turn"] == t for r in data[arm])]
            print(f"  {arm:<11}{rule:<12}" + " / ".join(f"{x:3.0f}" for x in v))
    print("\nExtraction method counts:", {a: {m: sum(r["extract"] == m for r in data[a]) for m in ("fence", "quote", "greeting", "whole")} for a in ARMS})
    # drift-back, as in drift.py, on the corrected arm
    runs = {}
    for r in data["corrected"]:
        runs.setdefault(r["run"], {})[r["turn"]] = r
    for name, val, gap in (("rules", n_rules, 2), ("judge", lambda r: r["judge"], 1)):
        back = [run for run, ts in runs.items() if 1 in ts and val(ts[1]) is not None and
                any(t in ts and val(ts[t]) is not None and val(ts[t]) <= val(ts[1]) - gap for t in (2, 3, 4))]
        print(f"\nDrift-back ({name}): {len(back)} of {len(runs)} corrected runs fall >= {gap} below their turn-1 level at turn 2, 3 or 4")
    j_all = [(n_rules(r), r["judge"]) for a in ARMS for r in data[a] if r["judge"]]
    if len(j_all) > 3:
        xs, ys = zip(*j_all)
        print(f"Rules vs judge, Pearson r = {statistics.correlation(xs, ys):.2f} (n={len(j_all)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--judge", default="anthropic:claude-haiku-5-5")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.judge.startswith("openrouter"):
        sys.exit("The judge runs through the Anthropic API, never OpenRouter.")
    if not a.report:
        for arm in ARMS:
            judge_arm(arm, a.target, a.judge)
    report(a.target, a.judge)


if __name__ == "__main__":
    main()
