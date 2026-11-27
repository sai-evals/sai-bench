"""Q1 (#9), Phase B on Modal (amendment A4): Qwen3-8B transcripts with raw thinking, then residual-stream activations.

Two steps, both on one L40S at a time:
  generate  plays the 4 scripted turns of every job-offer-family version (10 runs each) with thinking on, and writes
            results/job-offer-family-<c>/convos__modal_qwen3-8b.jsonl in runner.py's format, so q1_judge.py can judge it.
  acts      runs forward passes and saves, for every layer, the residual stream at the last prompt token (end of each
            user turn) and the mean over the hint sentence's tokens, for the conversations above and for the explicit-
            statement training set (q1_probe_data.py). Writes results/q1_probe/acts_qwen3-8b.npz (+ .json index).

Usage (Modal credentials from the environment, MODAL_TOKEN_ID / MODAL_TOKEN_SECRET):
  modal run correction-cost/bench/q1_modal.py --step generate
  modal run correction-cost/bench/q1_modal.py --step acts
  add --version v3 for amendment A6 (training conversations labelled by Qwen3-8B's own answer; 30 matched test runs)
  add --version v2 for amendment A5 (varied hint/question wording, v2 training set; files under results/q1_probe/)
"""
import json, os
import modal

MODEL = "Qwen/Qwen3-8B"
CONDITIONS = ["none", "subtle", "clear", "explicit", "distractor"]
TARGET = "modal:qwen3-8b"

app = modal.App("sai-bench-q1-probe")
cache = modal.Volume.from_name("sai-bench-hf-cache", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.11.0", "huggingface_hub[hf_transfer]==0.35.3", "numpy<2.3")
         .env({"HF_HOME": "/cache", "HF_HUB_ENABLE_HF_TRANSFER": "1"}))


def split_think(text):
    """Qwen3 writes '<think>…</think>' before the answer. Returns (answer, thinking); thinking is None if absent."""
    if "</think>" in text:
        think, ans = text.split("</think>", 1)
        return ans.strip(), think.replace("<think>", "").strip()
    if text.lstrip().startswith("<think>"):  # cut off inside the thinking
        return "", text.replace("<think>", "").strip()
    return text.strip(), None


@app.function(gpu="L40S", image=image, volumes={"/cache": cache}, timeout=3 * 3600)
def generate(user_turns: dict, n_runs: int, max_tokens: int, per_run: dict = None) -> list:
    """user_turns: condition -> turns (same for every run); per_run (A5): condition -> one turn list per run."""
    from vllm import LLM, SamplingParams
    llm = LLM(MODEL, dtype="bfloat16", max_model_len=40960, gpu_memory_utilization=0.92)
    sp = SamplingParams(temperature=0.6, top_p=0.95, top_k=20, max_tokens=max_tokens)
    text = (lambda c, r, t: per_run[c][r][t]) if per_run else (lambda c, r, t: user_turns[c][t])
    convs = [{"condition": c, "run": r, "messages": [], "turns": []} for c in user_turns for r in range(n_runs)]
    for t in range(len(next(iter(user_turns.values())))):
        for cv in convs:
            cv["messages"].append({"role": "user", "content": text(cv["condition"], cv["run"], t)})
        outs = llm.chat([cv["messages"] for cv in convs], sp, chat_template_kwargs={"enable_thinking": True}, use_tqdm=False)
        for cv, o in zip(convs, outs):
            out = o.outputs[0]
            ans, think = split_think(out.text)
            cv["messages"].append({"role": "assistant", "content": ans})
            cv["turns"].append({"turn": t, "user": text(cv["condition"], cv["run"], t), "assistant": ans, "corrects": None,
                                "stop_reason": "max_tokens" if out.finish_reason == "length" else out.finish_reason,
                                "usage": {"input_tokens": len(o.prompt_token_ids), "output_tokens": len(out.token_ids)},
                                "thinking": think})
        print(f"turn {t} done")
    return [{k: cv[k] for k in ("condition", "run", "turns")} for cv in convs]


@app.cls(gpu="L40S", image=image, volumes={"/cache": cache}, timeout=3600, max_containers=2)
class Acts:
  @modal.enter()
  def load(self):
    """Load the model once per container (loading it per call kept old copies alive and ran out of GPU memory)."""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    self.tok = AutoTokenizer.from_pretrained(MODEL)
    self.model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16).to("cuda").eval()

  @modal.method()
  def run(self, items: list) -> list:
    """items: {"id", "messages", "hint" (or None)}. Returns {"id", "last": [L+1, d] f16, "hint": [L+1, d] f16 | None}."""
    import numpy as np, torch
    tok, model = self.tok, self.model
    out = []
    for it in items:
        prompt = tok.apply_chat_template(it["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=True)
        enc = tok(prompt, return_offsets_mapping=True, return_tensors="pt", add_special_tokens=False)
        with torch.no_grad():
            hs = model(enc["input_ids"].cuda(), output_hidden_states=True).hidden_states  # L+1 x [1, T, d]
        H = torch.stack([h[0] for h in hs])  # [L+1, T, d]
        rec = {"id": it["id"], "last": H[:, -1].float().cpu().numpy().astype(np.float16), "hint": None,
               "n_tokens": int(H.shape[1])}
        if it.get("hint"):
            a = prompt.find(it["hint"])
            b = a + len(it["hint"])
            idx = [i for i, (s, e) in enumerate(enc["offset_mapping"][0].tolist()) if s < b and e > a]
            if a >= 0 and idx:
                rec["hint"] = H[:, idx].float().mean(1).cpu().numpy().astype(np.float16)
        out.append(rec)
    return out


# A6: Qwen3-8B's own read of the user, used as the probe label (self-distillation, as in arXiv 2609.31603).
SELF_Q = ("Pause the advice for a moment. Based only on what I've told you so far, which is most likely true about me? "
          "Reply with just the letter.\n{opts}")
SELF_OPTS = ["I want to live close to my family.", "I'm fine living far from my family.", "Nothing I've said shows either way."]


@app.cls(gpu="L40S", image=image, volumes={"/cache": cache}, timeout=3600, max_containers=2)
class Acts3:
  @modal.enter()
  def load(self):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    self.tok = AutoTokenizer.from_pretrained(MODEL)
    self.model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16).to("cuda").eval()
    self.letters = [self.tok.encode(x, add_special_tokens=False)[0] for x in "ABC"]

  @modal.method()
  def run(self, items: list) -> list:
    """items: {"id", "messages"}. Returns {"id", "last": [L+1, d] f16 at the end of the conversation (generation prompt,
    thinking on), "self": [p_stay, p_away, p_unclear] averaged over the 3 cyclic option orders (thinking off)}."""
    import numpy as np, torch
    tok, model = self.tok, self.model
    out = []
    for it in items:
        prompt = tok.apply_chat_template(it["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=True)
        ids = tok(prompt, return_tensors="pt", add_special_tokens=False)["input_ids"].cuda()
        with torch.no_grad():
            hs = model(ids, output_hidden_states=True).hidden_states
        last = torch.stack([h[0, -1] for h in hs]).float().cpu().numpy().astype(np.float16)
        probs = np.zeros(3)
        for k in range(3):
            order = [(k + j) % 3 for j in range(3)]  # position j shows canonical option order[j]
            opts = "\n".join(f"{'ABC'[j]}. {SELF_OPTS[order[j]]}" for j in range(3))
            msgs = it["messages"] + [{"role": "user", "content": SELF_Q.format(opts=opts)}]
            q = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            qi = tok(q, return_tensors="pt", add_special_tokens=False)["input_ids"].cuda()
            with torch.no_grad():
                logits = model(qi).logits[0, -1].float()
            p = torch.softmax(logits[self.letters], 0).cpu().numpy()
            for j in range(3):
                probs[order[j]] += p[j] / 3
        out.append({"id": it["id"], "last": last, "self": probs.tolist(), "n_tokens": int(ids.shape[1])})
    return out


@app.local_entrypoint()
def main(step: str = "generate", n_runs: int = 10, max_tokens: int = 6000, version: str = "v1"):
    import numpy as np
    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(here))
    scen = {c: json.load(open(f"{repo}/correction-cost/scenarios/job-offer-family-{c}/scenario.json")) for c in CONDITIONS}
    safe = TARGET.replace(":", "_").replace("/", "_")
    if version == "v3":
        return main_v3(step, repo, scen, safe)
    v2 = version == "v2"  # A5: per-run hint and question wording, separate files
    spec = json.load(open(f"{repo}/correction-cost/probes/q1_test_prompts_v2.json")) if v2 else None
    convo_path = (lambda c: f"{repo}/results/q1_probe/v2/convos__{safe}__{c}.jsonl") if v2 else \
                 (lambda c: f"{repo}/results/job-offer-family-{c}/convos__{safe}.jsonl")

    if step == "generate":
        user_turns = {c: [t["user"] for t in scen[c]["turns"]] for c in CONDITIONS}
        if v2:
            n_runs = len(spec["none"])
            convs = generate.remote(user_turns, n_runs, max_tokens, {c: [r["turns"] for r in spec[c]] for c in CONDITIONS})
        else:
            convs = generate.remote(user_turns, n_runs, max_tokens)
        for c in CONDITIONS:
            path = convo_path(c)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                for cv in (x for x in convs if x["condition"] == c):
                    f.write(json.dumps({"scenario": scen[c]["id"], "scenario_version": scen[c].get("version"), "target": TARGET,
                                        "model_used": MODEL, "time": "", "run": cv["run"], "turns": cv["turns"],
                                        **({k: spec[c][cv["run"]][k] for k in ("hint", "hint_phrasing", "question_wording")} if v2 else {})},
                                       ensure_ascii=False) + "\n")
            print("saved", os.path.relpath(path, repo))
        cut = sum(t["stop_reason"] == "max_tokens" for cv in convs for t in cv["turns"])
        print(f"{len(convs)} conversations; {cut} turns hit max_tokens")

    elif step == "acts":
        items, index = [], []
        for c in CONDITIONS:
            for line in open(convo_path(c)):
                cv = json.loads(line)
                hint_text = cv.get("hint") if v2 else scen[c].get("hint")
                msgs = []
                for t in cv["turns"]:
                    msgs = msgs + [{"role": "user", "content": t["user"]}]
                    iid = f"test|{c}|{cv['run']}|{t['turn']}"
                    items.append({"id": iid, "messages": msgs, "hint": hint_text if t["turn"] == 0 else None})
                    index.append({"id": iid, "kind": "test", "condition": c, "run": cv["run"], "turn": t["turn"],
                                  "hint_phrasing": cv.get("hint_phrasing"), "question_wording": cv.get("question_wording"),
                                  "user_so_far": " ".join(m["content"] for m in msgs if m["role"] == "user")})
                    msgs = msgs + [{"role": "assistant", "content": t["assistant"]}]
        for k, r in enumerate(json.load(open(f"{repo}/correction-cost/probes/q1_explicit_statements{'_v2' if v2 else ''}.json"))):
            iid = f"probe|{k}"
            items.append({"id": iid, "messages": [{"role": "user", "content": r["user"]}], "hint": r["statement"]})
            index.append({"id": iid, "kind": "probe", "split": r["split"], "label": r["label"], "phrasing": r["phrasing"],
                          "context": r["context"]})
        batches = [items[i:i + 50] for i in range(0, len(items), 50)]
        recs = {r["id"]: r for batch in Acts().run.map(batches) for r in batch}
        last = np.stack([recs[x["id"]]["last"] for x in index])
        has_hint = np.array([recs[x["id"]]["hint"] is not None for x in index])
        hint = np.stack([recs[x["id"]]["hint"] if recs[x["id"]]["hint"] is not None else np.zeros_like(last[0]) for x in index])
        for x in index:
            x["n_tokens"] = recs[x["id"]]["n_tokens"]
        out = f"{repo}/results/q1_probe"
        os.makedirs(out, exist_ok=True)
        tag = "acts_qwen3-8b_v2" if v2 else "acts_qwen3-8b"
        np.savez_compressed(f"{out}/{tag}.npz", last=last, hint=hint, has_hint=has_hint)
        json.dump(index, open(f"{out}/{tag}.json", "w"))
        print(f"saved {len(index)} items, last {last.shape}, hints {int(has_hint.sum())}")


def main_v3(step, repo, scen, safe):
    """A6: training conversations (other moving decisions) and matched job-offer test conversations, 30 runs per version."""
    import numpy as np
    train = json.load(open(f"{repo}/correction-cost/probes/q1_train_convs_v3.json"))
    spec = json.load(open(f"{repo}/correction-cost/probes/q1_test_prompts_v3.json"))
    d = f"{repo}/results/q1_probe/v3"
    os.makedirs(d, exist_ok=True)
    if step == "generate":
        h_tr = generate.spawn({"train": [0, 0]}, len(train), 4000, {"train": [r["turns"] for r in train]})
        h_te = generate.spawn({c: [0] * 4 for c in CONDITIONS}, len(spec["none"]), 6000,
                              {c: [r["turns"] for r in spec[c]] for c in CONDITIONS})
        tr, te = h_tr.get(), h_te.get()
        with open(f"{d}/train_convos.jsonl", "w") as f:
            for cv in tr:
                f.write(json.dumps({**{k: train[cv["run"]][k] for k in ("split", "cue_type", "phrasing", "decision", "cue")},
                                    "run": cv["run"], "turns": cv["turns"]}, ensure_ascii=False) + "\n")
        for c in CONDITIONS:
            with open(f"{d}/convos__{safe}__{c}.jsonl", "w") as f:
                for cv in (x for x in te if x["condition"] == c):
                    f.write(json.dumps({"scenario": scen[c]["id"], "scenario_version": scen[c].get("version"), "target": TARGET,
                                        "model_used": MODEL, "time": "", "run": cv["run"], "turns": cv["turns"],
                                        **{k: spec[c][cv["run"]][k] for k in ("hint", "hint_phrasing", "question_wording")}},
                                       ensure_ascii=False) + "\n")
        cut = sum(t["stop_reason"] == "max_tokens" for cv in tr + te for t in cv["turns"])
        print(f"{len(tr)} training and {len(te)} test conversations; {cut} turns hit max_tokens")
    elif step == "acts":
        items, index = [], []
        def add(convo, base):
            msgs = []
            for t in convo["turns"]:
                msgs = msgs + [{"role": "user", "content": t["user"]}]
                iid = f"{base['kind']}|{base.get('condition', base.get('cue_type'))}|{convo['run']}|{t['turn']}"
                items.append({"id": iid, "messages": msgs})
                index.append({**base, "id": iid, "run": convo["run"], "turn": t["turn"],
                              "user_so_far": " ".join(m["content"] for m in msgs if m["role"] == "user")})
                msgs = msgs + [{"role": "assistant", "content": t["assistant"]}]
        for line in open(f"{d}/train_convos.jsonl"):
            cv = json.loads(line)
            add(cv, {"kind": "probe", **{k: cv[k] for k in ("split", "cue_type", "phrasing", "decision")}})
        for c in CONDITIONS:
            for line in open(f"{d}/convos__{safe}__{c}.jsonl"):
                cv = json.loads(line)
                add(cv, {"kind": "test", "condition": c, "hint_phrasing": cv["hint_phrasing"], "question_wording": cv["question_wording"]})
        batches = [items[i:i + 40] for i in range(0, len(items), 40)]
        recs = {r["id"]: r for batch in Acts3().run.map(batches) for r in batch}
        last = np.stack([recs[x["id"]]["last"] for x in index])
        selfp = np.array([recs[x["id"]]["self"] for x in index], dtype=np.float32)
        for x in index:
            x["n_tokens"] = recs[x["id"]]["n_tokens"]
        np.savez_compressed(f"{repo}/results/q1_probe/acts_qwen3-8b_v3.npz", last=last, self=selfp)
        json.dump(index, open(f"{repo}/results/q1_probe/acts_qwen3-8b_v3.json", "w"))
        print(f"saved {len(index)} items, last {last.shape}")
