"""Model callers shared by the runner and the judge.
Keys come from environment variables (or a local .env file at the repo root). Never commit keys."""
import json, os, re, ssl, time, urllib.request, urllib.error
HERE = os.path.dirname(os.path.abspath(__file__))

def _ctx():
    try:
        import certifi; return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        for p in ("/etc/ssl/cert.pem", "/opt/homebrew/etc/openssl@3/cert.pem"):
            if os.path.exists(p): return ssl.create_default_context(cafile=p)
    return ssl.create_default_context()
CTX = _ctx()

ROOT = os.path.dirname(HERE)

def keys():
    env = os.path.join(ROOT, ".env")
    if os.path.exists(env):
        for line in open(env):
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.strip().split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"'))
    return {"openai": os.environ.get("OPENAI_API_KEY", ""), "anthropic": os.environ.get("ANTHROPIC_API_KEY", ""),
            "google": os.environ.get("GOOGLE_API_KEY", ""), "deepseek": os.environ.get("DEEPSEEK_API_KEY", "")}
KEYS = keys()

def _post(url, headers, body, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=300, context=CTX) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code in (408, 429, 500, 502, 503, 529) and i < tries - 1:
                time.sleep(6 * (i + 1)); continue
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError) as e:
            if i < tries - 1: time.sleep(6 * (i + 1)); continue
            raise RuntimeError(str(e))

PROVIDER = {"gpt": "openai", "claude": "anthropic", "gemini": "google", "deepseek": "deepseek"}

def chat(provider, model, messages, system=None, temperature=None, max_tokens=3000, json_mode=False):
    """messages: [{'role':'user'|'assistant','content':str}]. Returns (text, model_used)."""
    if provider == "anthropic":
        body = {"model": model, "max_tokens": max_tokens, "messages": messages}
        if system: body["system"] = system
        if temperature is not None: body["temperature"] = temperature
        h = {"x-api-key": KEYS["anthropic"], "anthropic-version": "2023-06-01", "content-type": "application/json"}
        try: r = _post("https://api.anthropic.com/v1/messages", h, body)
        except RuntimeError as e:
            if "temperature" not in str(e): raise
            body.pop("temperature"); r = _post("https://api.anthropic.com/v1/messages", h, body)
        return "".join(b.get("text", "") for b in r["content"]), r.get("model")
    if provider in ("openai", "deepseek"):
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        body = {"model": model, "messages": msgs}
        if temperature is not None: body["temperature"] = temperature
        if json_mode: body["response_format"] = {"type": "json_object"}
        url = "https://api.openai.com/v1/chat/completions" if provider == "openai" else "https://api.deepseek.com/chat/completions"
        h = {"Authorization": "Bearer " + KEYS[provider], "content-type": "application/json"}
        try: r = _post(url, h, body)
        except RuntimeError as e:
            if "temperature" not in str(e): raise
            body.pop("temperature"); r = _post(url, h, body)
        return r["choices"][0]["message"]["content"] or "", r.get("model")
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
