"""Second judge from another company (#1 follow-up): re-score a fixed sample of Q1-Q4 items with a non-Anthropic judge,
using the exact prompt each question's judge uses, and report agreement with Haiku 5.5.

Why: Haiku 5.5 judges its own replies in every question. If a judge from another company, on the same prompt, gives the
same scores, the numbers are about the replies rather than about Haiku's taste.

The sample is fixed by a seed and stratified, and only Haiku-target replies are used (where self-judging bias would show):
  Q1  40 answer scores        job-offer-family-*, 8 per condition (q1_judge.ANSWER_PROMPT)
  Q2  40 pace scores          trip-pace-corrected, 10 per turn 1-4 (judge.PROMPT)
  Q3  60 labels               trip / job offer / laptop / dinner, stratified by Haiku's label (q3_judge.PROMPT)
  Q4  30 replies x 4 prefs    lisbon4, separate scoring (q4_judge.ONE)
Writes results/cross_judge__<judge>.jsonl (resumable) and prints agreement.

Usage: python3 correction-cost/bench/cross_judge.py --judge nim:google/gemma-4-31b-it [--report]
The judge never runs through OpenRouter.
"""
import argparse, glob, json, os, random, statistics, sys, time
from concurrent.futures import ThreadPoolExecutor
from providers import chat, LAST
from runner import REPO, load_scenario, safe
import judge as q2, q1_judge as q1, q3_judge as q3, q4_judge as q4

HAIKU = "anthropic:claude-haiku-5-5"
R = os.path.join(REPO, "results")


def jl(p):
    return [json.loads(l) for l in open(p) if l.strip()] if os.path.exists(p) else []


def convos(scen, target):
    return {c.get("run", k): c for k, c in enumerate(jl(os.path.join(R, scen, f"convos__{safe(target)}.jsonl")))}


def strat(rows, key, per, rnd):
    out = []
    for v in sorted({key(r) for r in rows}, key=str):
        grp = [r for r in rows if key(r) == v]
        out += rnd.sample(grp, min(per, len(grp)))
    return out


def items():
    rnd = random.Random(0)
    its = []
    # Q1
    for cond in q1.CONDITIONS:
        sid = f"job-offer-family-{cond}"
        cv, scen, rub = convos(sid, HAIKU), load_scenario(sid), q2.rubric_sections(sid)
        pref = scen["preferences"][0]
        rows = [r for r in jl(os.path.join(R, sid, f"q1judged__{safe(HAIKU)}__by__{safe(HAIKU)}.jsonl")) if r["score"]]
        for r in rnd.sample(rows, 8):
            c = cv[r["run"]]
            its.append({"id": f"q1|{sid}|{r['run']}|{r['turn']}", "q": "Q1", "kind": "score", "key": "score", "haiku": r["score"],
                        "system": q1.SYSTEM, "prompt": q1.ANSWER_PROMPT.format(
                            question=pref["question"], value=pref["user_value"], rubric=rub[pref["id"]],
                            history=q2.history(c["turns"], r["turn"]), reply=c["turns"][r["turn"]]["assistant"])})
    # Q2
    sid, tgt = "trip-pace-corrected", "openrouter:anthropic/claude-haiku-5.5"
    cv, scen, rub = convos(sid, tgt), load_scenario(sid), q2.rubric_sections(sid)
    pref = next(p for p in scen["preferences"] if p["id"] == "pace")
    rows = [r for r in jl(os.path.join(R, sid, f"judged__{safe(tgt)}__by__{safe(HAIKU)}.jsonl"))
            if r["preference"] == "pace" and r["result"] and r["turn"] >= 1]
    for r in strat(rows, lambda r: r["turn"], 10, rnd):
        c = cv[r["run"]]
        its.append({"id": f"q2|{sid}|{r['run']}|{r['turn']}", "q": "Q2", "kind": "score", "key": "score", "haiku": r["result"]["score"],
                    "system": q2.SYSTEM, "prompt": q2.PROMPT.format(
                        question=pref["question"], value=pref["user_value"], rubric=rub["pace"],
                        history=q2.history(c["turns"], r["turn"]), reply=c["turns"][r["turn"]]["assistant"])})
    # Q3
    rows = [r for r in q3.load(HAIKU) if r["target"] == safe(HAIKU) and r["scenario"] in q3.SCENARIOS]
    for r in strat(rows, lambda r: r["label"], 12, rnd):
        c = convos(r["scenario"], HAIKU)[r["run"]]
        lean_def = dict(q3.prefs_of(r["scenario"]))[r["pref"]]
        eg = q3.IGNORE_EG.get(r["pref"])
        users = "\n".join(f"{i + 1}. {x['user']}" for i, x in enumerate(c["turns"][:r["turn"] + 1]))
        its.append({"id": f"q3|{r['scenario']}|{r['pref']}|{r['run']}|{r['turn']}", "q": "Q3", "kind": "label", "key": "label",
                    "haiku": r["label"], "system": q3.SYSTEM, "prompt": q3.PROMPT.format(
                        question=q3.QUESTIONS[r["pref"]], lean_def=lean_def, users=users, reply=c["turns"][r["turn"]]["assistant"],
                        leans=" | ".join(f'"{x}"' for x in q3.LEANS[r["pref"]]), ignore_eg=eg or "dates or budget",
                        else_eg=(eg + ", who is coming") if eg else "dates, budget, who is coming, whether they have kids")})
    # Q4
    q4.PREFIX = "lisbon4"
    q4.INTRO, q4.SECTIONS = q4.rubric()
    rows = []
    for arm in q4.ARMS:
        rows += [r | {"arm": arm} for r in jl(q4.path(arm, HAIKU, HAIKU))]
    for r in rnd.sample(rows, 30):
        c = convos(f"lisbon4-{r['arm']}", HAIKU)[r["run"]]
        users = "\n".join(f"{i + 1}. {x['user']}" for i, x in enumerate(c["turns"][:r["turn"] + 1]))
        for p in q4.PREFS:
            if r["separate"][p] is None:
                continue
            its.append({"id": f"q4|{r['arm']}|{r['run']}|{r['turn']}|{p}", "q": "Q4", "kind": "score", "key": "score",
                        "haiku": r["separate"][p], "system": q4.SYSTEM, "prompt": q4.ONE.format(
                            users=users, reply=c["turns"][r["turn"]]["assistant"], intro=q4.INTRO, pref=p, section=q4.SECTIONS[p])})
    return its


def ask(judge, system, prompt, key):
    provider, model = judge.split(":", 1)
    for _ in range(3):
        for wait in range(12):  # free tiers limit tokens per minute: wait and retry instead of failing the run
            try:
                LAST.clear()
                text = chat(provider, model, [{"role": "user", "content": prompt}], system=system)[0]
                break
            except RuntimeError as e:
                if "429" not in str(e):
                    raise
                time.sleep(20 + 10 * wait)
        else:
            return None
        d = q1.parse_json(text, key)
        if d is not None:
            return d
    return None


def kappa(a, b):
    labs = sorted(set(a) | set(b))
    po = sum(x == y for x, y in zip(a, b)) / len(a)
    pe = sum((a.count(l) / len(a)) * (b.count(l) / len(b)) for l in labs)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def spearman(a, b):
    def rank(x):
        s = sorted(range(len(x)), key=lambda i: x[i]); r = [0] * len(x); i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and x[s[j + 1]] == x[s[i]]:
                j += 1
            for k in range(i, j + 1):
                r[s[k]] = (i + j) / 2
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    return statistics.correlation(ra, rb) if len(set(a)) > 1 and len(set(b)) > 1 else float("nan")


def report(out):
    rows = [r for r in jl(out) if r["other"] is not None]
    print(f"\n{len(rows)} items scored by the second judge")
    for qn in ("Q1", "Q2", "Q3", "Q4"):
        rs = [r for r in rows if r["q"] == qn]
        if not rs:
            continue
        if qn == "Q3":
            a, b = [r["haiku"] for r in rs], [r["other"] for r in rs]
            print(f"{qn}: n={len(rs)}  same label {100 * sum(x == y for x, y in zip(a, b)) / len(rs):.0f}%  Cohen's kappa {kappa(a, b):.2f}")
            labs = q3.LABELS
            print("     Haiku label ->  " + "  ".join(f"{l[:6]:>6}" for l in labs) + "   (second judge's label, counts)")
            for l in labs:
                print(f"     {l:<14}" + "  ".join(f"{sum(r['haiku'] == l and r['other'] == m for r in rs):>6}" for m in labs))
        else:
            for sub in sorted({r["id"].split("|")[-1] if qn == "Q4" else "all" for r in rs}):
                ss = [r for r in rs if qn != "Q4" or r["id"].endswith("|" + sub)]
                a, b = [r["haiku"] for r in ss], [r["other"] for r in ss]
                d = [y - x for x, y in zip(a, b)]
                print(f"{qn} {sub:<7} n={len(ss):>3}  exact {100 * sum(x == 0 for x in d) / len(d):>3.0f}%  within 1 "
                      f"{100 * sum(abs(x) <= 1 for x in d) / len(d):>3.0f}%  mean (other - Haiku) {statistics.mean(d):+.2f}  "
                      f"Spearman {spearman(a, b):.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="nim:google/gemma-4-31b-it")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--workers", type=int, default=1)
    a = ap.parse_args()
    if a.judge.startswith(("openrouter", "anthropic")):
        sys.exit("The second judge must be from another company and must not run through OpenRouter.")
    out = os.path.join(R, f"cross_judge__{safe(a.judge)}.jsonl")
    if not a.report:
        done = {r["id"] for r in jl(out) if r["other"] is not None}
        todo = [i for i in items() if i["id"] not in done]
        print(f"{len(todo)} items to score")

        def one(it):
            d = ask(a.judge, it["system"], it["prompt"], it["key"])
            v = (d or {}).get(it["key"])
            if it["kind"] == "score":
                v = q4.num(v)
            elif v not in q3.LABELS:
                v = None
            return {k: it[k] for k in ("id", "q", "haiku")} | {"other": v, "judge": a.judge, "reason": (d or {}).get("reason")}

        with ThreadPoolExecutor(a.workers) as ex, open(out, "a") as f:
            for r in ex.map(one, todo):
                f.write(json.dumps(r, ensure_ascii=False) + "\n"); f.flush()
                print(time.strftime("%H:%M:%S"), r["id"], r["haiku"], r["other"], flush=True)
    report(out)


if __name__ == "__main__":
    main()
