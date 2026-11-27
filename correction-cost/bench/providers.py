"""Model callers shared by the runner and the judge.
Keys come from environment variables (or a local .env file at the repo root). Never commit keys."""
import http.client, json, os, re, ssl, time, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))

def _ctx():
    try:
        import certifi; return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        for p in ("/etc/ssl/cert.pem", "/opt/homebrew/etc/openssl@3/cert.pem"):
            if os.path.exists(p): return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()
CTX = _ctx()

ROOT = os.path.dirname(os.path.dirname(HERE))  # repo root, where README says .env lives

def keys():
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"'))
    return {"openai": os.environ.get("OPENAI_API_KEY", ""), "anthropic": os.environ.get("ANTHROPIC_API_KEY", ""),
            "google": os.environ.get("GOOGLE_API_KEY", ""), "deepseek": os.environ.get("DEEPSEEK_API_KEY", ""),
            "openrouter": os.environ.get("OPENROUTER_API_KEY", ""),
            "local": os.environ.get("LOCAL_API_KEY", "local"),  # a local server (LM Studio, Ollama) needs no real key
            "groq": os.environ.get("GROQ_API_KEY", ""),
            "nim": os.environ.get("NVIDIA_NIM_API_KEY", ""),
            "aihubmix": os.environ.get("AIHUB_MIX_API_KEY", ""),
            "cloudflare": os.environ.get("CLOUDFLARE_API_TOKEN", "")}
KEYS = keys()

def _post(url, headers, body, tries=8, timeout=300):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code in (408, 429, 500, 502, 503, 529) and i < tries - 1:
                # Free tiers rate-limit per minute: wait as long as the provider asks (Retry-After), else back off.
                try: wait = float(e.headers.get("retry-after") or 0)
                except ValueError: wait = 0
                time.sleep(min(max(wait, 6 * (i + 1)), 90)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, ConnectionError, http.client.HTTPException) as e:  # incl. RemoteDisconnected
            if i < tries - 1: time.sleep(6 * (i + 1)); continue
            raise RuntimeError(str(e))

LAST = {}  # stop_reason and token usage of the last call, where the provider reports them

PROVIDER = {"gpt": "openai", "claude": "anthropic", "gemini": "google", "deepseek": "deepseek"}

def split_think(text):
    """Some open models write their reasoning inline as <think>...</think> before the answer. Returns (answer, thinking)."""
    m = re.match(r"\s*<think>(.*?)</think>\s*(.*)", text or "", re.S)
    return (m.group(2), m.group(1).strip()) if m else (text, None)

def chat(provider, model, messages, system=None, temperature=None, max_tokens=8000, json_mode=False, thinking=False):
    """messages: [{'role':'user'|'assistant','content':str}]. Returns (text, model_used).
    The model's reasoning, when the provider returns it, goes to LAST["thinking"] (never into the returned text).
    thinking=True turns on Claude's adaptive thinking with summarized display: Claude's API returns a summary
    of its reasoning, not the raw text. OpenAI-compatible reasoning models return theirs without a flag."""
    if provider == "anthropic":
        body = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system: body["system"] = system
        if temperature is not None: body["temperature"] = temperature
        if thinking: body["thinking"] = {"type": "adaptive", "display": "summarized"}
        h = {"x-api-key": KEYS["anthropic"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
        try: r = _post("https://api.anthropic.com/v1/messages", h, body)
        except RuntimeError as e:
            if "temperature" not in str(e): raise
            body.pop("temperature"); r = _post("https://api.anthropic.com/v1/messages", h, body)
        think = "\n\n".join(b.get("thinking", "") for b in r["content"] if b.get("type") == "thinking") or None
        LAST.clear(); LAST.update(stop_reason=r.get("stop_reason"), usage=r.get("usage"), thinking=think)
        return "".join(b.get("text", "") for b in r["content"]), r.get("model")
    if provider in ("openai", "deepseek", "openrouter", "local", "groq", "nim", "aihubmix", "cloudflare"):
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        body = {"model": model, "messages": msgs}
        if provider in ("openrouter", "local", "nim", "aihubmix", "cloudflare"): body["max_tokens"] = max_tokens  # same cap as the anthropic path
        # Groq's free tier allows ~8k tokens a minute, so its reply cap is lower (set GROQ_MAX_TOKENS to change it).
        if provider == "groq": body["max_tokens"] = min(max_tokens, int(os.environ.get("GROQ_MAX_TOKENS", "4000")))
        if temperature is not None: body["temperature"] = temperature
        if json_mode: body["response_format"] = {"type": "json_object"}
        url = {"openai": "https://api.openai.com/v1/chat/completions",
               "deepseek": "https://api.deepseek.com/chat/completions",
               "openrouter": "https://openrouter.ai/api/v1/chat/completions",
               # OpenAI-compatible local server: LM Studio by default, or set LOCAL_BASE_URL (Ollama: http://localhost:11434/v1)
               "local": os.environ.get("LOCAL_BASE_URL", "http://localhost:1234/v1") + "/chat/completions",
               "groq": "https://api.groq.com/openai/v1/chat/completions",
               "nim": "https://integrate.api.nvidia.com/v1/chat/completions",  # NVIDIA NIM (build.nvidia.com)
               "aihubmix": "https://aihubmix.com/v1/chat/completions",  # AIHubMix (has free GLM models)
               # Cloudflare Workers AI, OpenAI-compatible endpoint (free plan: 10,000 neurons a day)
               "cloudflare": f"https://api.cloudflare.com/client/v4/accounts/{os.environ.get('CLOUDFLARE_ACCOUNT_ID', '')}/ai/v1/chat/completions"}[provider]
        h = {"Authorization": "Bearer " + KEYS[provider], "content-type": "application/json", "User-Agent": "sai-bench"}
        # A local model thinking at length can take many minutes per reply; giving up cancels the generation.
        to = 1800 if provider == "local" else 300
        try: r = _post(url, h, body, timeout=to)
        except RuntimeError as e:
            if "temperature" not in str(e): raise
            body.pop("temperature"); r = _post(url, h, body, timeout=to)
        if "choices" not in r:  # OpenRouter can report upstream errors in a 200 response
            raise RuntimeError(f"{provider}: {json.dumps(r.get('error', r))[:400]}")
        c = r["choices"][0]
        # AIHubMix answers an exhausted free quota with a normal-looking reply; treat it as an error, never as model output.
        if provider == "aihubmix" and (c["message"].get("content") or "").startswith("Sorry, to prevent abuse of free resources"):
            raise RuntimeError("aihubmix: free quota exhausted: " + c["message"]["content"][:200])
        text, inline = split_think(c["message"].get("content") or "")
        think = c["message"].get("reasoning") or c["message"].get("reasoning_content") or inline
        LAST.clear(); LAST.update(stop_reason="max_tokens" if c.get("finish_reason") == "length" else c.get("finish_reason"),
                                  usage=r.get("usage"), thinking=think)
        return text, r.get("model")
    if provider == "google":
        contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]} for m in messages]
        body = {"contents": contents}
        if system: body["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={KEYS['google']}"
        r = _post(url, {"content-type": "application/json"}, body)
        c = (r.get("candidates") or [{}])[0]
        return "".join(p.get("text", "") for p in c.get("content", {}).get("parts", [])), model
    if provider == "mock":
        # No key, no network. Lets anyone check the pipeline end to end.
        if system and "JSON only" in system:
            return '{"score": 3, "handling": "silent", "reason": "mock judge"}', "mock"
        return "Mock reply to: " + messages[-1]["content"][:80], "mock"
    raise ValueError(provider)
