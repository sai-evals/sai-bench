"""Score every assistant reply on every preference. Each preference gets its own judge call,
so a score on one preference can't bleed into another.

Usage:
  python3 correction-cost/bench/judge.py --scenario trip-planning --target mock:mock --judge mock:mock

Reads results/<scenario>/convos__<target>.jsonl, writes judged__<target>__by__<judge>.jsonl
next to it, and prints the mean score per turn and preference."""
import argparse, json, os, re, statistics
from providers import chat, LAST
from runner import TOPIC, REPO, load_scenario, safe

SYSTEM = "You grade one assistant reply against one user preference. Reply with JSON only."

PROMPT = """Preference: {question}
What this user actually wants: {value}
The assistant only knows this if the user said it in the conversation.

Rubric for this preference:
{rubric}

Conversation so far:
{history}

Reply to grade:
{reply}

Return JSON: {{"score": <1-5>, "handling": "asked" | "stated_assumption" | "silent", "reason": "<one sentence>"}}
handling is "asked" if the reply asks the user about this preference, "stated_assumption" if it says what it assumed, and "silent" otherwise."""


def rubric_sections(name):
    with open(os.path.join(TOPIC, "scenarios", name, "rubric.md")) as f:
        parts = re.split(r"^## +", f.read(), flags=re.M)[1:]
    return {p.split("\n", 1)[0].strip(): p.split("\n", 1)[1].strip() for p in parts}


def history(turns, upto):
    lines = []
    for t in turns[:upto]:
        lines += [f"USER: {t['user']}", f"ASSISTANT: {t['assistant']}"]
    lines.append(f"USER: {turns[upto]['user']}")
    return "\n".join(lines)


def parse(text):
    """The last JSON object in the reply that has a score. Judges sometimes write one, then a corrected one."""
    found, dec = None, json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                d, _ = dec.raw_decode(text, i)
                if isinstance(d, dict) and "score" in d:
                    d["score"] = int(d["score"]); found = d
            except Exception:
                pass
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--judge", required=True)
    a = ap.parse_args()
    scen, rub = load_scenario(a.scenario), rubric_sections(a.scenario)
    missing = [p["id"] for p in scen["preferences"] if p["id"] not in rub]
    if missing:
        raise SystemExit(f"rubric.md has no section for: {', '.join(missing)}")
    provider, model = a.judge.split(":", 1)
    d = os.path.join(REPO, "results", a.scenario)
    src = os.path.join(d, f"convos__{safe(a.target)}.jsonl")
    out = os.path.join(d, f"judged__{safe(a.target)}__by__{safe(a.judge)}.jsonl")
    scores = {}
    with open(src) as f, open(out, "w") as g:
        for line in f:
            convo = json.loads(line)
            for t in convo["turns"]:
                for p in scen["preferences"]:
                    prompt = PROMPT.format(question=p["question"], value=p["user_value"], rubric=rub[p["id"]],
                                           history=history(convo["turns"], t["turn"]), reply=t["assistant"])
                    LAST.clear()
                    text, _ = chat(provider, model, [{"role": "user", "content": prompt}], system=SYSTEM)
                    r = parse(text)
                    g.write(json.dumps({"run": convo.get("run"), "turn": t["turn"], "preference": p["id"],
                                        "judge": a.judge, "result": r, "raw": None if r else text,
                                        "usage": LAST.get("usage")},
                                       ensure_ascii=False) + "\n")
                    if r:
                        scores.setdefault((t["turn"], p["id"]), []).append(r["score"])
    ids = [p["id"] for p in scen["preferences"]]
    notes = {i: f"user corrects {t['corrects']}" for i, t in enumerate(scen["turns"]) if t.get("corrects")}
    print("turn  " + "  ".join(f"{i:>8}" for i in ids))
    for i in range(len(scen["turns"])):
        cells = [statistics.mean(scores[(i, p)]) if scores.get((i, p)) else None for p in ids]
        row = "  ".join(f"{c:>8.1f}" if c is not None else f"{'-':>8}" for c in cells)
        print(f"{i:>4}  {row}  {notes.get(i, '')}")
    print("saved", os.path.relpath(out, REPO))


if __name__ == "__main__":
    main()
