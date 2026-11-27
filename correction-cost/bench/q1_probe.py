"""Q1 (#9), Phase B analysis (amendment A4): train the probe on explicit statements, test it on the job-offer turns.

Reads results/q1_probe/acts_qwen3-8b.{npz,json} (from q1_modal.py --step acts) and, for P6, the Haiku answer scores in
results/job-offer-family-clear/q1judged__modal_qwen3-8b__by__anthropic_claude-haiku-5-5.jsonl.
Writes results/q1_probe/probe_qwen3-8b.json and prints the tables.

Rules (fixed in A4 before any activation was read):
- logistic regression (L2, C=1.0) on standardized residual-stream activations at the last prompt token, stay-near-family = 1;
- layer = best validation AUROC on held-out phrasings x held-out contexts (ties: earliest);
- P5: AUROC clear vs none at the end of turn 0 >= 0.8, distractor vs none <= 0.65;
- controls: keyword-count AUROC, 1,000 random unit directions (95th percentile), hint-span read vs distractor;
- P6: flagged = probability > 0.5; among clear (run, turn) pairs with answer score <= 2, at least half flagged.
"""
import json, os, re, sys
import warnings
import numpy as np
warnings.filterwarnings("ignore", category=RuntimeWarning)  # spurious matmul warnings from numpy on macOS
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(REPO, "results", "q1_probe")
CONDS = ["none", "subtle", "clear", "explicit", "distractor"]
KEYWORDS = re.compile(r"\b(family|families|parents?|mom|mum|dad|mother|father|sister|brother|siblings?|"
                      r"relatives|sunday dinners?|close to home|nearby|20 minutes|hiking|colorado)\b", re.I)


def auc(pos, neg):
    y = np.r_[np.ones(len(pos)), np.zeros(len(neg))]
    return float(roc_auc_score(y, np.r_[pos, neg]))


V2 = "--v2" in sys.argv  # amendment A5
TAG = "acts_qwen3-8b_v2" if V2 else "acts_qwen3-8b"


def judge_v2_clear():
    """A5 P6: Haiku answer scores (rubric v0.2) for the v2 clear runs. Cached in results/q1_probe/v2/answers_clear.jsonl."""
    out = os.path.join(D, "v2", "answers_clear.jsonl")
    if os.path.exists(out):
        return {(r["run"], r["turn"]): r["score"] for r in map(json.loads, open(out))}
    sys.path.insert(0, HERE)
    from q1_judge import ANSWER_PROMPT, ask
    from judge import rubric_sections, history
    from runner import load_scenario
    scen = load_scenario("job-offer-family-clear")
    pref, rub = scen["preferences"][0], rubric_sections("job-offer-family-clear")
    rows = []
    for line in open(os.path.join(D, "v2", "convos__modal_qwen3-8b__clear.jsonl")):
        cv = json.loads(line)
        for t in cv["turns"]:
            ans, _, _ = ask("anthropic:claude-haiku-5-5", ANSWER_PROMPT.format(
                question=pref["question"], value=pref["user_value"], rubric=rub[pref["id"]],
                history=history(cv["turns"], t["turn"]), reply=t["assistant"]), "score")
            rows.append({"run": cv["run"], "turn": t["turn"], "score": int(ans["score"]) if ans else None,
                         "lean": ans.get("lean") if ans else None})
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return {(r["run"], r["turn"]): r["score"] for r in rows}


def main():
    z = np.load(os.path.join(D, TAG + ".npz"))
    idx = json.load(open(os.path.join(D, TAG + ".json")))
    last, hint, has_hint = z["last"].astype(np.float32), z["hint"].astype(np.float32), z["has_hint"]
    n_layers = last.shape[1]
    probe = [i for i, x in enumerate(idx) if x["kind"] == "probe"]
    tr = [i for i in probe if idx[i]["split"] == "train"]
    va = [i for i in probe if idx[i]["split"] == "val"]
    ytr = np.array([idx[i]["label"] for i in tr])
    yva = np.array([idx[i]["label"] for i in va])

    # 1. layer choice on held-out explicit statements
    val_auc = []
    for l in range(n_layers):
        sc = StandardScaler().fit(last[tr, l])
        clf = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(last[tr, l]), ytr)
        val_auc.append(roc_auc_score(yva, clf.predict_proba(sc.transform(last[va, l]))[:, 1]))
    L = int(np.argmax(np.round(val_auc, 6)))
    sc = StandardScaler().fit(last[tr, L])
    clf = LogisticRegression(C=1.0, max_iter=5000).fit(sc.transform(last[tr, L]), ytr)
    prob = lambda X: clf.predict_proba(sc.transform(X))[:, 1]
    w = clf.coef_[0]

    test = [i for i, x in enumerate(idx) if x["kind"] == "test"]
    p_last = {i: float(p) for i, p in zip(test, prob(last[test, L]))}
    kw = {i: len(KEYWORDS.findall(idx[i]["user_so_far"])) for i in test}
    cell = lambda c, t: [i for i in test if idx[i]["condition"] == c and idx[i]["turn"] == t]

    # 2. AUROC of each version vs none, per turn; keyword baseline
    table = {}
    for c in CONDS[1:]:
        for t in range(4):
            a, b = cell(c, t), cell("none", t)
            table[f"{c}|{t}"] = {"probe": auc([p_last[i] for i in a], [p_last[i] for i in b]),
                                 "keyword": auc([kw[i] for i in a], [kw[i] for i in b]),
                                 "mean_p": float(np.mean([p_last[i] for i in a]))}
    mean_p_none = {t: float(np.mean([p_last[i] for i in cell("none", t)])) for t in range(4)}

    # 3. random directions at layer L, clear vs none at turn 0 (in the standardized space the probe uses)
    rng = np.random.default_rng(0)
    A, B = sc.transform(last[cell("clear", 0), L]), sc.transform(last[cell("none", 0), L])
    rand = []
    for _ in range(1000):
        v = rng.standard_normal(A.shape[1]); v /= np.linalg.norm(v)
        r = auc(A @ v, B @ v)
        rand.append(max(r, 1 - r))  # a random direction has no sign, so take the better orientation
    rand95 = float(np.percentile(rand, 95))

    # 4. hint-span read (turn 0 only), each hint version vs distractor
    hint_tab = {}
    for c in ["subtle", "clear", "explicit"]:
        a = [i for i in cell(c, 0) if has_hint[i]]
        b = [i for i in cell("distractor", 0) if has_hint[i]]
        if a and b:
            hint_tab[c] = auc(prob(hint[a, L]), prob(hint[b, L]))

    # 5. P6 against Haiku answer scores for Qwen3-8B, clear version
    p6 = None
    jf = os.path.join(REPO, "results", "job-offer-family-clear", "q1judged__modal_qwen3-8b__by__anthropic_claude-haiku-5-5.jsonl")
    if V2 or os.path.exists(jf):
        score = judge_v2_clear() if V2 else {(r["run"], r["turn"]): r["score"] for r in map(json.loads, open(jf))}
        low = [i for i in test if idx[i]["condition"] == "clear" and (score.get((idx[i]["run"], idx[i]["turn"])) or 9) <= 2]
        flagged = sum(p_last[i] > 0.5 for i in low)
        p6 = {"low_answer_turns": len(low), "flagged": int(flagged), "passes": bool(low) and flagged >= len(low) / 2}

    # 6. A5: gate (explicit vs none at turn 0) and the secondary difference-of-means direction
    gate = table["explicit|0"]["probe"]
    mu = last[[i for i, y in zip(tr, ytr) if y == 1], L].mean(0) - last[[i for i, y in zip(tr, ytr) if y == 0], L].mean(0)
    dm = {i: float(last[i, L] @ mu) for i in test}
    dm_tab = {f"{c}|{t}": auc([dm[i] for i in cell(c, t)], [dm[i] for i in cell("none", t)]) for c in CONDS[1:] for t in range(4)}
    dm_val = float(roc_auc_score(yva, last[va, L] @ mu))

    res = {"version": "v2" if V2 else "v1", "gate_explicit_vs_none_t0": gate, "gate_passes": gate >= 0.8,
           "diff_means": {"val_auc": dm_val, "vs_none": dm_tab}, "layer": L, "n_layers": n_layers, "val_auc_by_layer": [float(x) for x in val_auc], "val_auc": float(val_auc[L]),
           "vs_none": table, "mean_p_none": mean_p_none, "random_dir_95pct_clear_vs_none_t0": rand95,
           "hint_span_vs_distractor": hint_tab, "p6": p6,
           "p5": {"clear_vs_none_t0": table["clear|0"]["probe"], "distractor_vs_none_t0": table["distractor|0"]["probe"],
                  "passes": table["clear|0"]["probe"] >= 0.8 and table["distractor|0"]["probe"] <= 0.65},
           "per_item": [{**{k: idx[i][k] for k in ("condition", "run", "turn")}, "p": p_last[i]} for i in test],
           "weight_norm": float(np.linalg.norm(w))}
    json.dump(res, open(os.path.join(D, TAG.replace("acts", "probe") + ".json"), "w"), indent=1)

    print(f"layer {L} of {n_layers - 1} (validation AUROC {val_auc[L]:.3f}; train n={len(tr)}, val n={len(va)})")
    print("AUROC vs none (probe / keyword) and mean probability, end of each user turn")
    for c in CONDS[1:]:
        print(f"  {c:<10}" + "".join(f"  t{t}: {table[f'{c}|{t}']['probe']:.2f}/{table[f'{c}|{t}']['keyword']:.2f} p={table[f'{c}|{t}']['mean_p']:.2f}" for t in range(4)))
    print("  none mean p: " + "  ".join(f"t{t}={mean_p_none[t]:.2f}" for t in range(4)))
    print(f"random directions, clear vs none t0: 95th percentile AUROC {rand95:.2f}")
    print("hint-span read vs distractor:", {k: round(v, 2) for k, v in hint_tab.items()})
    print(f"GATE explicit vs none t0: {gate:.2f} -> {'passes' if gate >= 0.8 else 'FAILS (hint results not interpreted)'}")
    print(f"diff-of-means (val AUROC {dm_val:.3f}) vs none:")
    for c in CONDS[1:]:
        print(f"  {c:<10}" + "".join(f"  t{t}: {dm_tab[f'{c}|{t}']:.2f}" for t in range(4)))
    print("P5:", res["p5"])
    print("P6:", p6)


if __name__ == "__main__":
    main()
