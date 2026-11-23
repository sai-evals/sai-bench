"""Play a scenario's scripted user turns against a target model and save the transcript.

Usage:
  python3 correction-cost/bench/runner.py --scenario trip-planning --target mock:mock
  python3 correction-cost/bench/runner.py --scenario trip-planning --target anthropic:<model-id> --n 3

A target is provider:model. Providers: anthropic, openai, google, deepseek, mock.
Transcripts go to results/<scenario>/convos__<target>.jsonl (git ignores results/)."""
import argparse, json, os, time
from providers import chat, LAST

HERE = os.path.dirname(os.path.abspath(__file__))
TOPIC = os.path.dirname(HERE)
REPO = os.path.dirname(TOPIC)


def load_scenario(name):
    with open(os.path.join(TOPIC, "scenarios", name, "scenario.json")) as f:
        return json.load(f)


def safe(target):
    return target.replace(":", "_").replace("/", "_")


def run_once(scen, target):
    provider, model = target.split(":", 1)
    messages, turns, used = [], [], None
    for i, t in enumerate(scen["turns"]):
        messages.append({"role": "user", "content": t["user"]})
        LAST.clear()
        text, used = chat(provider, model, messages, system=scen.get("system"))
        messages.append({"role": "assistant", "content": text})
        turns.append({"turn": i, "user": t["user"], "assistant": text, "corrects": t.get("corrects"),
                      "stop_reason": LAST.get("stop_reason"), "usage": LAST.get("usage")})
        if LAST.get("stop_reason") == "max_tokens":
            print(f"  warning: turn {i} hit max_tokens, the reply is cut off")
    return {"scenario": scen["id"], "scenario_version": scen.get("version"), "target": target,
            "model_used": used, "time": time.strftime("%Y-%m-%dT%H:%M:%S"), "turns": turns}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--n", type=int, default=1)
    ap.add_argument("--fresh", action="store_true", help="replace earlier transcripts for this scenario and target instead of appending")
    a = ap.parse_args()
    scen = load_scenario(a.scenario)
    out_dir = os.path.join(REPO, "results", a.scenario)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"convos__{safe(a.target)}.jsonl")
    with open(out, "w" if a.fresh else "a") as f:
        for k in range(a.n):
            rec = run_once(scen, a.target)
            rec["run"] = k
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()  # so a long run can be watched while it goes
            print(f"run {k + 1}/{a.n} done ({len(rec['turns'])} turns)", flush=True)
    print("saved", os.path.relpath(out, REPO))


if __name__ == "__main__":
    main()
