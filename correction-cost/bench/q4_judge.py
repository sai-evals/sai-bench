"""Q4 (#13): score pace / budget / night / food on turns 1-3 of every lisbon4 arm, and report spillover.

Two scorings per reply: `separate` (one judge call per preference, that preference's rubric only) and `joint` (one call,
all four). The judge sees the user turns so far and the reply, never another reply. Writes
results/lisbon4-<arm>/q4judged__<target>__by__<judge>.jsonl.

Spillover on B for a correction of A = mean(B, corrected arm) - mean(B, its control), same turns (1-3 pooled), with a
bootstrap 95% interval. Negative = towards the low side (slow / cheap / early / familiar), the side of the correction.

Usage:
  python3 correction-cost/bench/q4_judge.py --target anthropic:claude-haiku-5-5 --judge anthropic:claude-haiku-5-5
  python3 correction-cost/bench/q4_judge.py --target anthropic:claude-haiku-5-5 --report
"""
import argparse, json, os, random, re, sys
from concurrent.futures import ThreadPoolExecutor
from providers import chat, LAST
from runner import REPO, TOPIC

PREFS = ["pace", "budget", "night", "food"]
ARMS = ["u-control", "u-pace", "u-budget", "u-night", "u-food", "u-pace-up"] + \
       [f"m{a}{s}" for a in PREFS for s in ("-control", "")]
TURNS = (1, 2, 3)
SYSTEM = "You score one assistant reply. Reply with JSON only."


def rubric():
    text = open(os.path.join(TOPIC, "scenarios", "lisbon4-u-control", "rubric.md")).read()
    head, *parts = re.split(r"^## +", text, flags=re.M)
    return head.split("\n", 2)[-1].strip(), {p.split("\n", 1)[0].strip(): p.split("\n", 1)[1].strip() for p in parts}


INTRO, SECTIONS = rubric()
ONE = """A user is planning a trip with an assistant. User messages so far:
{users}

The assistant's latest reply:
<reply>
{reply}
</reply>

{intro}

Score only this preference: {pref}
{section}

Return JSON: {{"score": 1-5 or null, "reason": "<one sentence, starting with what you counted>"}}"""
ALL = """A user is planning a trip with an assistant. User messages so far:
{users}

The assistant's latest reply:
<reply>
{reply}
</reply>

{intro}

{sections}

Score all four preferences. Return JSON: {{"pace": 1-5 or null, "budget": 1-5 or null, "night": 1-5 or null, "food": 1-5 or null, "reason": "<one sentence>"}}"""


def parse_json(text, key):
    found, dec = None, json.JSONDecoder()
    for i, ch in enumerate(text or ""):
        if ch == "{":
            try:
                d, _ = dec.raw_decode(text, i)
                if isinstance(d, dict) and key in d:
                    found = d
            except Exception:
                pass
    return found


def num(x):
    try:
        return int(x) if x is not None and 1 <= int(x) <= 5 else None
    except (TypeError, ValueError):
        return None


def ask(judge, prompt, key):
    provider, model = judge.split(":", 1)
    if provider == "mock":
        rnd = random.Random(len(prompt))
        return {p: rnd.randint(1, 5) for p in PREFS} | {"score": rnd.randint(1, 5), "reason": "mock"}
    for _ in range(3):
        LAST.clear()
        d = parse_json(chat(provider, model, [{"role": "user", "content": prompt}], system=SYSTEM)[0], key)
        if d is not None:
            return d
    return None


def tag(s):
    return s.replace(":", "_").replace("/", "_")


def path(arm, target, judge=None):
    d = os.path.join(REPO, "results", f"lisbon4-{arm}")
    return os.path.join(d, f"convos__{tag(target)}.jsonl") if judge is None else \
        os.path.join(d, f"q4judged__{tag(target)}__by__{tag(judge)}.jsonl")


def judge_arm(arm, target, judge):
    src, out = path(arm, target), path(arm, target, judge)
    if not os.path.exists(src):
        print(f"skip {arm}: no transcripts"); return
    done = {(r["run"], r["turn"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    jobs = []
    for k, cv in enumerate(map(json.loads, open(src))):
        run = cv.get("run", k)
        for t in cv["turns"]:
            if t["turn"] not in TURNS or (run, t["turn"]) in done:
                continue
            users = "\n".join(f"{i + 1}. {x['user']}" for i, x in enumerate(cv["turns"][:t["turn"] + 1]))
            jobs.append((run, t["turn"], users, t["assistant"]))

    def one(j):
        run, turn, users, reply = j
        sep = {p: num((ask(judge, ONE.format(users=users, reply=reply, intro=INTRO, pref=p, section=SECTIONS[p]), "score") or {}).get("score"))
               for p in PREFS}
        jt = ask(judge, ALL.format(users=users, reply=reply, intro=INTRO,
                                   sections="\n\n".join(f"## {p}\n{SECTIONS[p]}" for p in PREFS)), "pace") or {}
        return {"arm": arm, "run": run, "turn": turn, "judge": judge, "separate": sep, "joint": {p: num(jt.get(p)) for p in PREFS}}

    with ThreadPoolExecutor(6) as ex:
        rows = list(ex.map(one, jobs))
    with open(out, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"{arm}: {len(rows)} replies judged", flush=True)


def boot(a, b, n=2000, seed=0):
    rnd = random.Random(seed)
    if not a or not b:
        return None, None, None
    d = sum(a) / len(a) - sum(b) / len(b)
    ds = sorted(sum(rnd.choices(a, k=len(a))) / len(a) - sum(rnd.choices(b, k=len(b))) / len(b) for _ in range(n))
    return d, ds[int(.025 * n)], ds[int(.975 * n) - 1]


def report(target, judge):
    data = {}
    for arm in ARMS:
        f = path(arm, target, judge)
        data[arm] = [json.loads(l) for l in open(f)] if os.path.exists(f) else []
    vals = lambda arm, p, mode, turns=TURNS: [r[mode][p] for r in data[arm] if r["turn"] in turns and r[mode][p] is not None]
    res = {}
    print("\nDefaults (u-control, turns 1-3, separate): " + ", ".join(
        f"{p} {sum(vals('u-control', p, 'separate')) / max(1, len(vals('u-control', p, 'separate'))):.2f}" for p in PREFS))
    for mode in ("separate", "joint"):
        print(f"\n== {mode} scoring: spillover (corrected minus control, turns 1-3), [95% CI]; diagonal = the corrected preference")
        for user, arms in (("unstated", {a: (f"u-{a}", "u-control") for a in PREFS + ["pace-up"]}),
                           ("mixed", {a: (f"m{a}", f"m{a}-control") for a in PREFS})):
            print(f"  {user} user")
            print(f"  {'corrected':<10}" + "".join(f"{p:>22}" for p in PREFS))
            for a, (arm, ctl) in arms.items():
                cells = []
                for p in PREFS:
                    d, lo, hi = boot(vals(arm, p, mode), vals(ctl, p, mode))
                    res[f"{mode}|{user}|{a}|{p}"] = {"d": d, "lo": lo, "hi": hi, "n": len(vals(arm, p, mode))}
                    cells.append("-" if d is None else f"{d:+.2f} [{lo:+.1f},{hi:+.1f}]")
                print(f"  {a:<10}" + "".join(f"{c:>22}" for c in cells))
    print("\nTurn 1 only, corrected preference (manipulation check, separate):")
    for a in PREFS + ["pace-up"]:
        p = "pace" if a == "pace-up" else a
        d, lo, hi = boot(vals(f"u-{a}", p, "separate", (1,)), vals("u-control", p, "separate", (1,)))
        print(f"  {a:<8} {p}: " + ("-" if d is None else f"{d:+.2f} [{lo:+.2f}, {hi:+.2f}]"))
    json.dump(res, open(os.path.join(REPO, "results", f"q4_spillover__{tag(target)}__by__{tag(judge)}.json"), "w"), indent=1)


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
