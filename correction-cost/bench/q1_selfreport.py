"""Q1 (#9), amendment A8: report the direct-question answers of the open models (q1_selfreport_modal.py output), and
label each turn-3 reply's lean (stay / move / neither) with Haiku 5.5, using the Q1 answer prompt.

Usage: python3 correction-cost/bench/q1_selfreport.py [--judge anthropic:claude-haiku-5-5]
"""
import argparse, glob, json, os
from concurrent.futures import ThreadPoolExecutor
from runner import REPO, load_scenario
from judge import rubric_sections, history
import q1_judge as q1

D = os.path.join(REPO, "results", "q1_probe", "selfreport")
CONDS = ["none", "subtle", "clear", "explicit", "distractor"]


def lean_file(src, judge):
    out = src.replace(".jsonl", f"__lean__{judge.replace(':', '_').replace('/', '_')}.jsonl")
    done = {(r["condition"], r["run"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    scen, rub = load_scenario("job-offer-family-clear"), rubric_sections("job-offer-family-clear")
    pref = scen["preferences"][0]
    todo = [cv for cv in map(json.loads, open(src)) if (cv["condition"], cv["run"]) not in done]

    def one(cv):
        d, _, _ = q1.ask(judge, q1.ANSWER_PROMPT.format(question=pref["question"], value=pref["user_value"], rubric=rub[pref["id"]],
                                                        history=history(cv["turns"], 3), reply=cv["turns"][3]["assistant"]), "score")
        return {"condition": cv["condition"], "run": cv["run"], "score": (d or {}).get("score"), "lean": (d or {}).get("lean")}

    with ThreadPoolExecutor(6) as ex, open(out, "a") as f:
        for r in ex.map(one, todo):
            f.write(json.dumps(r) + "\n")
    return {(r["condition"], r["run"]): r for r in map(json.loads, open(out))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", default="anthropic:claude-haiku-5-5")
    a = ap.parse_args()
    for src in sorted(glob.glob(os.path.join(D, "*.jsonl"))):
        if "__lean__" in src:
            continue
        rows = [json.loads(l) for l in open(src)]
        leans = lean_file(src, a.judge)
        print(f"\n== {os.path.basename(src)[:-6]}  ({len(rows)} conversations, "
              f"{sum(t['stop_reason'] == 'max_tokens' for r in rows for t in r['turns'])} turns cut off)")
        print("says 'close to family' (argmax), % of runs, turns 0-3   | turn-3 lean stay/move/neither | among turn-3 'close': stay/move/neither")
        for c in CONDS:
            rs = [r for r in rows if r["condition"] == c]
            close = [[max(range(3), key=lambda j: r["self"][t][j]) == 0 for r in rs] for t in range(4)]
            ln = [leans.get((c, r["run"]), {}).get("lean") for r in rs]
            ln_close = [leans.get((c, r["run"]), {}).get("lean") for r, cl in zip(rs, close[3]) if cl]
            print(f"  {c:<11}" + " ".join(f"{100 * sum(x) / len(x):>4.0f}%" for x in close)
                  + f"   | {ln.count('stay'):>2}/{ln.count('move'):>2}/{ln.count('neither'):>2}"
                  + f"   | {ln_close.count('stay')}/{ln_close.count('move')}/{ln_close.count('neither')} of {len(ln_close)}")


if __name__ == "__main__":
    main()
