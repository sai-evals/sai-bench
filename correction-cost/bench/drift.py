"""Does a correction stick? Compare a corrected scenario with its no-correction control.

Usage:
  python3 correction-cost/bench/drift.py --pair trip-pace --preference pace \
      --target anthropic:<model-id> --judge anthropic:<model-id>

Reads results/<pair>-corrected/ and results/<pair>-control/ judged files and reports, per turn,
the mean score in both runs. Then, for the turns after the correction:
  default level    the control's mean score: what the model does when never corrected
  corrected level  each corrected run's score on the correction turn
  drift-back       a corrected run drifts back if a later turn scores at least 1 point below its
                   corrected level, moving toward the default. Measured against the control, not a
                   guessed default, so drift (toward the default) is kept apart from noise.
  how far back     per later turn, (corrected level - score) / (corrected level - default), averaged
                   over runs where the correction lifted the score above the default."""
import argparse, json, os, statistics
from runner import TOPIC, REPO, load_scenario, safe


def load(scenario, target, judge, pref):
    path = os.path.join(REPO, "results", scenario, f"judged__{safe(target)}__by__{safe(judge)}.jsonl")
    runs = {}
    for line in open(path):
        r = json.loads(line)
        if r["preference"] == pref and r["result"]:
            runs.setdefault(r["run"], {})[r["turn"]] = r["result"]["score"]
    return runs


def mean(xs):
    return statistics.mean(xs) if xs else None


def fmt(x):
    return f"{x:5.2f}" if x is not None else "    -"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", required=True, help="scenario prefix, e.g. trip-pace")
    ap.add_argument("--preference", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--judge", required=True)
    a = ap.parse_args()
    corrected_id, control_id = f"{a.pair}-corrected", f"{a.pair}-control"
    scen = load_scenario(corrected_id)
    fix = next(i for i, t in enumerate(scen["turns"]) if t.get("corrects") == a.preference)
    later = list(range(fix + 1, len(scen["turns"])))
    cor = load(corrected_id, a.target, a.judge, a.preference)
    con = load(control_id, a.target, a.judge, a.preference)

    print(f"target {a.target}   judge {a.judge}   preference {a.preference}")
    print(f"runs: {len(cor)} corrected, {len(con)} control\n")
    print("turn  corrected  control")
    for i in range(len(scen["turns"])):
        note = "  <- correction" if i == fix else ""
        c1 = mean([r[i] for r in cor.values() if i in r])
        c2 = mean([r[i] for r in con.values() if i in r])
        print(f"{i:>4}  {fmt(c1):>9}  {fmt(c2):>7}{note}")

    default = mean([r[i] for r in con.values() for i in later if i in r])
    drifted, fallbacks, shares = 0, [], {i: [] for i in later}
    for r in cor.values():
        if fix not in r:
            continue
        level = r[fix]
        drops = [level - r[i] for i in later if i in r]
        fallbacks.append(mean(drops) or 0)
        if default is not None and default < level and any(d >= 1 for d in drops):
            drifted += 1
        if default is not None and default < level:  # share of the gap back to the default, per turn
            for i in later:
                if i in r:
                    shares[i].append((level - r[i]) / (level - default))
    print(f"\ndefault level (control, turns {later[0]}-{later[-1]}): {fmt(default)}")
    print(f"corrected level (turn {fix}):              {fmt(mean([r[fix] for r in cor.values() if fix in r]))}")
    print(f"drift-back: {drifted}/{len(fallbacks)} runs fell back >= 1 point toward the default")
    print(f"mean fallback per later turn: {fmt(mean(fallbacks))} points")
    print("how far back toward the default (0% = held the correction, 100% = back at the default):")
    for i in later:
        s = mean(shares[i])
        print(f"  turn {i}: " + (f"{s:6.0%}  over {len(shares[i])} runs" if s is not None else "     -  (no run where corrected level > default)"))


if __name__ == "__main__":
    main()
