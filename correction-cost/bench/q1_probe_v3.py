"""Q1 (#9), Phase B analysis for amendment A6 (rules fixed in correction-cost/notes/q1-unstated-preference.md before the run).

Reads results/q1_probe/acts_qwen3-8b_v3.{npz,json} (from q1_modal.py --version v3 --step acts) and the v3 transcripts.
Labels are Qwen3-8B's own answer to the multiple-choice question (stay close = 1). Probe: standardize -> PCA(40) ->
logistic regression (C = 1.0) on the last prompt token; layer = best validation AUROC against the self-labels.
Judges the clear and explicit test runs with Haiku (Anthropic API) for P6/P7; cached in results/q1_probe/v3/answers.jsonl.
Writes results/q1_probe/probe_qwen3-8b_v3.json and prints the tables.
"""
import json, os, re, sys, warnings
import numpy as np
warnings.filterwarnings("ignore", category=RuntimeWarning)
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(REPO, "results", "q1_probe")
CONDS = ["none", "subtle", "clear", "explicit", "distractor"]
KEYWORDS = re.compile(r"\b(family|families|parents?|mom|mum|dad|mother|father|sister|brother|siblings?|grand\w+|"
                      r"relatives|dinner|close to home|nearby|20 minutes|neighborhood|hiking|colorado|baseball|gardening)\b", re.I)
SAFE = "modal_qwen3-8b"


def auc(pos, neg):
    return float(roc_auc_score(np.r_[np.ones(len(pos)), np.zeros(len(neg))], np.r_[pos, neg]))


def judge_answers():
    """Haiku answer score (rubric v0.2) and lean for every turn of the clear and explicit v3 runs."""
    out = os.path.join(D, "v3", "answers.jsonl")
    if os.path.exists(out):
        return {(r["condition"], r["run"], r["turn"]): r for r in map(json.loads, open(out))}
    sys.path.insert(0, HERE)
    from concurrent.futures import ThreadPoolExecutor
    from q1_judge import ANSWER_PROMPT, ask
    from judge import rubric_sections, history
    from runner import load_scenario
    jobs = []
    for c in ("clear", "explicit"):
        scen = load_scenario(f"job-offer-family-{c}")
        pref, rub = scen["preferences"][0], rubric_sections(f"job-offer-family-{c}")[scen["preferences"][0]["id"]]
        for line in open(os.path.join(D, "v3", f"convos__{SAFE}__{c}.jsonl")):
            cv = json.loads(line)
            for t in cv["turns"]:
                jobs.append((c, cv["run"], t["turn"], ANSWER_PROMPT.format(question=pref["question"], value=pref["user_value"],
                             rubric=rub, history=history(cv["turns"], t["turn"]), reply=t["assistant"])))
    with ThreadPoolExecutor(6) as ex:
        res = list(ex.map(lambda j: (j, ask("anthropic:claude-haiku-5-5", j[3], "score")[0]), jobs))
    rows = [{"condition": j[0], "run": j[1], "turn": j[2], "score": int(a["score"]) if a else None,
             "lean": a.get("lean") if a else None} for j, a in res]
    with open(out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return {(r["condition"], r["run"], r["turn"]): r for r in rows}


def main():
    z = np.load(os.path.join(D, "acts_qwen3-8b_v3.npz"))
    idx = json.load(open(os.path.join(D, "acts_qwen3-8b_v3.json")))
    X, P = z["last"].astype(np.float32), z["self"]
    y_all = (P.argmax(1) == 0).astype(int)  # 1 = Qwen says "I want to live close to my family"
    n_layers = X.shape[1]
    tr = [i for i, x in enumerate(idx) if x["kind"] == "probe" and x["split"] == "train"]
    va = [i for i, x in enumerate(idx) if x["kind"] == "probe" and x["split"] == "val"]
    test = [i for i, x in enumerate(idx) if x["kind"] == "test"]
    cell = lambda c, t: [i for i in test if idx[i]["condition"] == c and idx[i]["turn"] == t]

    # 0. self-labels on the training conversations, by cue kind
    print("Qwen's own answer on the training conversations (share 'close to family' / 'far' / 'unclear', by cue kind):")
    for k in ["stay_explicit", "stay_implicit", "move_explicit", "move_implicit", "family_neutral", "filler"]:
        ii = [i for i in tr + va if idx[i]["cue_type"] == k]
        a = P[ii].argmax(1)
        print(f"  {k:<15} n={len(ii):>3}  " + " / ".join(f"{np.mean(a == j):.2f}" for j in range(3)))
    print(f"  train labels: {int(y_all[tr].sum())} stay of {len(tr)}; validation: {int(y_all[va].sum())} of {len(va)}")

    # 1. layer choice
    mk = lambda: make_pipeline(StandardScaler(), PCA(40, random_state=0), LogisticRegression(C=1.0, max_iter=5000))
    val_auc = []
    for l in range(n_layers):
        m = mk().fit(X[tr, l], y_all[tr])
        val_auc.append(roc_auc_score(y_all[va], m.predict_proba(X[va, l])[:, 1]))
    L = int(np.argmax(np.round(val_auc, 6)))
    m = mk().fit(X[tr, L], y_all[tr])
    p = {i: float(v) for i, v in zip(test, m.predict_proba(X[test, L])[:, 1])}
    kw = {i: len(KEYWORDS.findall(idx[i]["user_so_far"])) for i in test}

    # 2. gate, per-version AUROC vs none, keyword baseline, transfer to Qwen's own labels on the test set
    gate = auc([p[i] for i in cell("explicit", 0)], [p[i] for i in cell("none", 0)])
    table = {f"{c}|{t}": {"probe": auc([p[i] for i in cell(c, t)], [p[i] for i in cell("none", t)]),
                          "keyword": auc([kw[i] for i in cell(c, t)], [kw[i] for i in cell("none", t)])}
             for c in CONDS[1:] for t in range(4)}
    yt = y_all[test]
    transfer = auc([p[i] for i, v in zip(test, yt) if v], [p[i] for i, v in zip(test, yt) if not v]) if 0 < yt.sum() < len(yt) else None
    rng = np.random.default_rng(0)
    gate_ci = np.percentile([auc(rng.choice([p[i] for i in cell("explicit", 0)], 30), rng.choice([p[i] for i in cell("none", 0)], 30))
                             for _ in range(2000)], [2.5, 97.5]).tolist()

    # 3. controls: random directions in the PCA space; shuffled-label probes
    pre = make_pipeline(StandardScaler(), PCA(40, random_state=0)).fit(X[tr, L])
    A, B = pre.transform(X[cell("explicit", 0), L]), pre.transform(X[cell("none", 0), L])
    rand = []
    for _ in range(1000):
        v = rng.standard_normal(40); v /= np.linalg.norm(v)
        r = auc(A @ v, B @ v); rand.append(max(r, 1 - r))
    shuf = []
    for s in range(100):
        ys = rng.permutation(y_all[tr])
        ms = mk().fit(X[tr, L], ys)
        shuf.append(auc(ms.predict_proba(X[cell("explicit", 0), L])[:, 1], ms.predict_proba(X[cell("none", 0), L])[:, 1]))
    sc = StandardScaler().fit(X[tr, L])
    mu = sc.transform(X[[i for i in tr if y_all[i]], L]).mean(0) - sc.transform(X[[i for i in tr if not y_all[i]], L]).mean(0)
    dm = {i: float(sc.transform(X[[i], L])[0] @ mu) for i in test}
    dm_tab = {f"{c}|{t}": auc([dm[i] for i in cell(c, t)], [dm[i] for i in cell("none", t)]) for c in CONDS[1:] for t in range(4)}

    # 4. P7: Qwen's own answer on the test conversations, and P6 / registered-but-not-followed with Haiku's answer labels
    self_tab = {f"{c}|{t}": [float(np.mean(P[cell(c, t)].argmax(1) == j)) for j in range(3)] for c in CONDS for t in range(4)}
    ans = judge_answers()
    key = lambda i: (idx[i]["condition"], idx[i]["run"], idx[i]["turn"])
    low = [i for i in test if idx[i]["condition"] == "clear" and (ans.get(key(i), {}).get("score") or 9) <= 2]
    p6 = {"low_answer_turns": len(low), "flagged": int(sum(p[i] > 0.5 for i in low)),
          "passes": bool(low) and sum(p[i] > 0.5 for i in low) >= len(low) / 2}
    rbnf = {}
    for c in ("clear", "explicit"):
        says = [i for i in cell(c, 3) if y_all[i]]
        rbnf[c] = {"says_close_t3": len(says), "of": len(cell(c, 3)),
                   "of_those_reply_leans": {x: sum(ans.get(key(i), {}).get("lean") == x for i in says) for x in ("stay", "move", "neither")}}

    res = {"layer": L, "val_auc": float(val_auc[L]), "val_auc_by_layer": [float(v) for v in val_auc],
           "gate_explicit_vs_none_t0": gate, "gate_ci95": gate_ci, "gate_passes": gate >= 0.8,
           "vs_none": table, "transfer_auc_vs_self_labels_test": transfer,
           "random_dir_95pct": float(np.percentile(rand, 95)), "shuffled_label_95pct": float(np.percentile(shuf, 95)),
           "diff_means_vs_none": dm_tab, "self_report": self_tab, "p6": p6, "registered_not_followed_t3": rbnf,
           "p5": {"clear_vs_none_t0": table["clear|0"]["probe"], "distractor_vs_none_t0": table["distractor|0"]["probe"],
                  "passes": table["clear|0"]["probe"] >= 0.75 and table["distractor|0"]["probe"] <= 0.65}}
    json.dump(res, open(os.path.join(D, "probe_qwen3-8b_v3.json"), "w"), indent=1)

    print(f"\nlayer {L} (validation AUROC {val_auc[L]:.3f} against Qwen's own labels)")
    print(f"GATE explicit vs none t0: {gate:.2f} [95% {gate_ci[0]:.2f}, {gate_ci[1]:.2f}] -> {'passes' if gate >= 0.8 else 'FAILS'}"
          f"   (random directions 95th pct {res['random_dir_95pct']:.2f}; shuffled-label probes 95th pct {res['shuffled_label_95pct']:.2f})")
    print(f"transfer: probe vs Qwen's own label on the job-offer conversations, AUROC {transfer}")
    print("AUROC vs none (probe / keyword), by turn:")
    for c in CONDS[1:]:
        print(f"  {c:<10}" + "".join(f"  t{t}: {table[f'{c}|{t}']['probe']:.2f}/{table[f'{c}|{t}']['keyword']:.2f}" for t in range(4)))
    print("difference of means vs none:")
    for c in CONDS[1:]:
        print(f"  {c:<10}" + "".join(f"  t{t}: {dm_tab[f'{c}|{t}']:.2f}" for t in range(4)))
    print("P7, Qwen's own answer on the test conversations: share saying 'close to family', by turn:")
    for c in CONDS:
        print(f"  {c:<10}" + "".join(f"  t{t}: {self_tab[f'{c}|{t}'][0]:.2f}" for t in range(4)))
    print("P5:", res["p5"]); print("P6:", p6); print("registered but not followed, turn 3:", rbnf)


if __name__ == "__main__":
    main()
