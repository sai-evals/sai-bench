"""Q1 (#9), amendment A8: ask other open models the direct question that worked for Qwen3-8B (A6, P7).

Each model plays its own job-offer conversations (the A6 test prompts, first 10 runs of each of the 5 versions, 4 turns,
no thinking), then after every turn is asked, in 3 cyclic option orders, "which is most likely true about me?":
  live close to my family / fine living far from my family / nothing I've said shows either way.
The letter probabilities (first token of "A"/" A" etc.) are averaged over the orders, as for Qwen.

Writes results/q1_probe/selfreport/<model>.jsonl: one line per conversation with the turns and, per turn, the
probabilities [close, far, unclear]. q1_selfreport.py reads these, adds Haiku's stay/move/neither lean, and reports.

Usage (Modal credentials from the environment):
  modal run correction-cost/bench/q1_selfreport_modal.py --model allenai/Olmo-3-7B-Instruct
"""
import json, os
import modal

CONDITIONS = ["none", "subtle", "clear", "explicit", "distractor"]
N_RUNS = 10
SELF_Q = ("Pause the advice for a moment. Based only on what I've told you so far, which is most likely true about me? "
          "Reply with just the letter.\n{opts}")  # identical to q1_modal.SELF_Q
SELF_OPTS = ["I want to live close to my family.", "I'm fine living far from my family.", "Nothing I've said shows either way."]

app = modal.App("sai-bench-q1-selfreport")
cache = modal.Volume.from_name("sai-bench-hf-cache", create_if_missing=True)
image = (modal.Image.debian_slim(python_version="3.12")
         .pip_install("vllm==0.11.0", "huggingface_hub[hf_transfer]==0.35.3", "numpy<2.3")
         .env({"HF_HOME": "/cache", "HF_HUB_ENABLE_HF_TRANSFER": "1"}))


@app.function(gpu="L40S", image=image, volumes={"/cache": cache}, timeout=2 * 3600)
def play(model: str, convs: list) -> list:
    """convs: {"condition", "run", "turns": [user texts]}. Plays them, then asks the self-report question after each turn."""
    from vllm import LLM, SamplingParams
    # processed_logprobs: the letter logprobs come after allowed_token_ids is applied, so all three letters are returned
    llm = LLM(model, dtype="bfloat16", max_model_len=16384, gpu_memory_utilization=0.9, logprobs_mode="processed_logprobs")
    tok = llm.get_tokenizer()
    sp = SamplingParams(temperature=0.7, top_p=0.95, max_tokens=1500)
    for cv in convs:
        cv["messages"], cv["out"] = [], []
    for t in range(4):
        for cv in convs:
            cv["messages"].append({"role": "user", "content": cv["turns"][t]})
        outs = llm.chat([cv["messages"] for cv in convs], sp, use_tqdm=False)
        for cv, o in zip(convs, outs):
            text = o.outputs[0].text.strip()
            cv["messages"].append({"role": "assistant", "content": text})
            cv["out"].append({"turn": t, "user": cv["turns"][t], "assistant": text,
                              "stop_reason": "max_tokens" if o.outputs[0].finish_reason == "length" else o.outputs[0].finish_reason})
        print(f"turn {t} done", flush=True)
    # The self-report question: one token, logprobs over the letters (both "A" and " A" spellings).
    letter_ids = []
    for x in "ABC":
        ids = {tok.encode(x, add_special_tokens=False)[0], tok.encode(" " + x, add_special_tokens=False)[-1]}
        letter_ids.append(sorted(ids))
    allowed = sorted({i for ids in letter_ids for i in ids})
    sq = SamplingParams(temperature=0, max_tokens=1, logprobs=len(allowed), allowed_token_ids=allowed)
    import math
    qs, where = [], []
    for ci, cv in enumerate(convs):
        for t in range(4):
            hist = cv["messages"][:2 * t + 2]
            for k in range(3):
                order = [(k + j) % 3 for j in range(3)]
                opts = "\n".join(f"{'ABC'[j]}. {SELF_OPTS[order[j]]}" for j in range(3))
                qs.append(hist + [{"role": "user", "content": SELF_Q.format(opts=opts)}])
                where.append((ci, t, order))
    outs = llm.chat(qs, sq, use_tqdm=False)
    probs = {}
    for (ci, t, order), o in zip(where, outs):
        lp = o.outputs[0].logprobs[0]  # token id -> Logprob
        mass = [sum(math.exp(lp[i].logprob) for i in ids if i in lp) for ids in letter_ids]
        z = sum(mass) or 1.0
        p = probs.setdefault((ci, t), [0.0, 0.0, 0.0])
        for j in range(3):
            p[order[j]] += mass[j] / z / 3
    return [{"condition": cv["condition"], "run": cv["run"], "model": model, "turns": cv["out"],
             "self": [probs[(ci, t)] for t in range(4)]} for ci, cv in enumerate(convs)]


@app.local_entrypoint()
def main(model: str):
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    spec = json.load(open(f"{repo}/correction-cost/probes/q1_test_prompts_v3.json"))
    convs = [{"condition": c, "run": r["run"], "turns": r["turns"]} for c in CONDITIONS for r in spec[c][:N_RUNS]]
    res = play.remote(model, convs)
    d = f"{repo}/results/q1_probe/selfreport"
    os.makedirs(d, exist_ok=True)
    out = f"{d}/{model.replace('/', '_')}.jsonl"
    with open(out, "w") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    cut = sum(t["stop_reason"] == "max_tokens" for r in res for t in r["turns"])
    print(f"saved {out}: {len(res)} conversations, {cut} turns cut off")
