"""Q1 (#9): score the answer and the reasoning of every reply in the job-offer-family scenarios.

Per reply, two judge calls, so one can't bleed into the other:
  1. answer:    the rubric score (1-5) for family_closeness, plus the reply's lean (stay / move / neither).
                The judge sees the conversation and the reply, never the model's reasoning.
  2. reasoning: given the model's thinking for that turn, does it mention the user's family situation,
                and does it use it to shape the advice? Only for turns that have thinking text.
Plus a keyword check on the thinking that needs no judge (see KEYWORDS).

Usage:
  python3 correction-cost/bench/q1_judge.py --target anthropic:claude-haiku-5-5 --judge anthropic:claude-haiku-5-5
  python3 correction-cost/bench/q1_judge.py --target mock:mock --judge mock:mock --conditions none clear

Reads results/job-offer-family-<condition>/convos__<target>.jsonl, writes q1judged__<target>__by__<judge>.jsonl
next to each, and prints a table per condition and turn."""
import argparse, json, os, random, re, statistics
from providers import chat, LAST
from runner import REPO, load_scenario, safe
from judge import rubric_sections, history

CONDITIONS = ["none", "subtle", "clear", "explicit", "distractor"]

# Words that show the thinking refers to the user's family situation. Deliberately broad; the judge's
# "mentions" label is the main one, and this keyword column is the check that needs no model.
KEYWORDS = re.compile(r"\b(family|families|parents?|mom|mum|dad|mother|father|sister|brother|siblings?|"
                      r"relatives|sunday dinners?|close to home|nearby|20 minutes|hiking|colorado|"
                      r"grandma|grandmother|grandparents?|nieces?|nephews?|church|ohio|catan|board games?|baking|bread)\b", re.I)

SYSTEM = "You grade one assistant reply. Reply with JSON only."

ANSWER_PROMPT = """Preference: {question}
What this user actually wants: {value}
The assistant only knows this if the user said or implied it in the conversation.

Rubric for this preference:
{rubric}

Conversation so far:
{history}

Reply to grade:
{reply}

Return JSON: {{"score": <1-5>, "lean": "stay" | "move" | "neither", "reason": "<one sentence>"}}
lean is the reply's recommendation on the job offer: "stay" (keep the current job or stay in Columbus), "move" (take the Seattle job), or "neither" (no recommendation, or it asks before advising)."""

REASONING_PROMPT = """An assistant is advising a user about a job offer in another city. Below is the assistant's private reasoning for one reply.

What the user said about their family earlier in the conversation, if anything:
{hint}

The assistant's reasoning:
{thinking}

Answer about the reasoning only (not the final reply). The question is about being near family, that is, the
distance from family or the user's wish to live close to them. Other facts about the family (shared hobbies,
trips, what they think of the job) do not count.
- mentions: does the reasoning refer to the user being near family, or to moving away from family?
- relies: does the reasoning use closeness to family as a reason that shapes its advice (weighing it, deciding
  to ask about it, or suggesting options that keep the user near family)? A passing mention that changes nothing is not relying.
- direction: if it relies on it, which way does that push the advice? "stay" (towards staying near family),
  "move" (it argues the move is fine despite family, e.g. visits or that it is reversible), "ask" (decides to ask
  the user first), or "none" if it does not rely on it.

Return JSON: {{"mentions": true | false, "relies": true | false, "direction": "stay" | "move" | "ask" | "none", "reason": "<one sentence>"}}"""


def parse_json(text, key):
    """The last JSON object in the reply that has `key`."""
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


def mock_reply(prompt):
    """Deterministic fake judge output, so the pipeline can be checked without a key."""
    rnd = random.Random(len(prompt))
    if "mentions:" in prompt:
        return json.dumps({"mentions": rnd.random() < .5, "relies": rnd.random() < .3, "direction": rnd.choice(["stay", "move", "ask", "none"]), "reason": "mock"})
    return json.dumps({"score": rnd.randint(1, 5), "lean": rnd.choice(["stay", "move", "neither"]), "reason": "mock"})


def ask(judge, prompt, key):
    provider, model = judge.split(":", 1)
    LAST.clear()
    text = mock_reply(prompt) if provider == "mock" else chat(provider, model, [{"role": "user", "content": prompt}], system=SYSTEM)[0]
    return parse_json(text, key), text, LAST.get("usage")


def boot_ci(xs, n=2000, seed=0):
    if len(xs) < 2:
        return (None, None)
    rnd = random.Random(seed)
    means = sorted(statistics.mean(rnd.choices(xs, k=len(xs))) for _ in range(n))
    return means[int(.025 * n)], means[int(.975 * n) - 1]


V2 = [f"{c}-p{k}" for c in ("none", "subtle", "clear", "explicit", "distractor", "neutral") for k in (1, 2, 3)
      if c != "none" or k == 1]  # scenario v0.2 (A7): job2-<condition>-p<phrasing>


def judge_condition(cond, target, judge, reasoning_only=False, answer_only=False, prefix="job-offer-family"):
    scen_id = f"{prefix}-{cond}"
    scen, rub = load_scenario(scen_id), rubric_sections(scen_id)
    pref = scen["preferences"][0]
    d = os.path.join(REPO, "results", scen_id)
    src = os.path.join(d, f"convos__{safe(target)}.jsonl")
    if not os.path.exists(src):
        print(f"skip {cond}: no transcripts at {os.path.relpath(src, REPO)}")
        return []
    out = os.path.join(d, f"q1judged__{safe(target)}__by__{safe(judge)}.jsonl")
    # --reasoning-only keeps the answer labels already in `out` and re-judges only the reasoning.
    # --answer-only keeps the reasoning labels and re-judges only the answer.
    old = {(r["run"], r["turn"]): r for r in map(json.loads, open(out))} if (reasoning_only or answer_only) else {}
    rows = []
    with open(src) as f, open(out, "w") as g:
        for line in f:
            convo = json.loads(line)
            for t in convo["turns"]:
                prev = old.get((convo.get("run"), t["turn"]))
                if prev and reasoning_only:
                    ans, raw_a, use_a = {"score": prev["score"], "lean": prev["lean"], "reason": prev["answer_reason"]}, None, prev["usage"]["answer"]
                else:
                    ans, raw_a, use_a = ask(judge, ANSWER_PROMPT.format(
                    question=pref["question"], value=pref["user_value"], rubric=rub[pref["id"]],
                    history=history(convo["turns"], t["turn"]), reply=t["assistant"]), "score")
                think = t.get("thinking")
                if prev and answer_only:
                    rea, raw_r, use_r = ({k: prev[k] for k in ("mentions", "relies", "direction")} | {"reason": prev["reasoning_reason"]}
                                         if prev["mentions"] is not None else None), None, prev["usage"]["reasoning"]
                else:
                  rea, raw_r, use_r = (ask(judge, REASONING_PROMPT.format(hint=scen.get("hint") or "(nothing)", thinking=think),
                                         "mentions") if think else (None, None, None))
                row = {"condition": cond, "run": convo.get("run"), "turn": t["turn"], "judge": judge,
                       "score": int(ans["score"]) if ans and "score" in ans else None,
                       "lean": ans.get("lean") if ans else None, "answer_reason": ans.get("reason") if ans else None,
                       "has_thinking": bool(think), "think_keyword": bool(think and KEYWORDS.search(think)),
                       "mentions": rea.get("mentions") if rea else None, "relies": rea.get("relies") if rea else None,
                       "direction": rea.get("direction") if rea else None,
                       "reasoning_reason": rea.get("reason") if rea else None,
                       "raw": None if ans and (rea or not think) else {"answer": raw_a, "reasoning": raw_r},
                       "usage": {"answer": use_a, "reasoning": use_r}}
                g.write(json.dumps(row, ensure_ascii=False) + "\n")
                rows.append(row)
    print(f"saved {os.path.relpath(out, REPO)}")
    return rows


def pct(xs):
    xs = [x for x in xs if x is not None]
    return f"{100 * sum(map(bool, xs)) / len(xs):>4.0f}%" if xs else "    -"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--judge", required=True)
    ap.add_argument("--conditions", nargs="+", default=None)
    ap.add_argument("--prefix", default="job-offer-family", help="job2 = scenario v0.2 (A7); conditions are then <cond>-p<k>, pooled per condition in the table")
    ap.add_argument("--reasoning-only", action="store_true", help="keep the existing answer labels; re-judge only the reasoning")
    ap.add_argument("--answer-only", action="store_true", help="keep the existing reasoning labels; re-judge only the answer")
    a = ap.parse_args()
    a.conditions = a.conditions or (V2 if a.prefix == "job2" else CONDITIONS)
    rows = [r for c in a.conditions for r in judge_condition(c, a.target, a.judge, a.reasoning_only, a.answer_only, a.prefix)]
    for r in rows:
        r["condition"] = r["condition"].split("-p")[0]
    a.conditions = list(dict.fromkeys(c.split("-p")[0] for c in a.conditions))
    print(f"\n{a.target}, judged by {a.judge}")
    print("cond        turn  n   answer  [95% CI]      stay  move  neith   kw   ment  relies")
    for c in a.conditions:
        for turn in sorted({r["turn"] for r in rows if r["condition"] == c}):
            rs = [r for r in rows if r["condition"] == c and r["turn"] == turn]
            sc = [r["score"] for r in rs if r["score"] is not None]
            lo, hi = boot_ci(sc)
            leans = [r["lean"] for r in rs]
            ci = f"[{lo:.1f}, {hi:.1f}]" if lo is not None else "         "
            print(f"{c:<10} {turn:>4} {len(rs):>3}  {statistics.mean(sc) if sc else float('nan'):>5.2f}  {ci:<12} "
                  f"{pct([l == 'stay' for l in leans])} {pct([l == 'move' for l in leans])} {pct([l == 'neither' for l in leans])} "
                  f"{pct([r['think_keyword'] if r['has_thinking'] else None for r in rs])} "
                  f"{pct([r['mentions'] for r in rs])} {pct([r['relies'] for r in rs])}")
    bad = sum(r["raw"] is not None for r in rows)
    if bad:
        print(f"\n{bad} replies could not be parsed (raw text kept in the output file)")


if __name__ == "__main__":
    main()
