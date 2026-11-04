"""Thin wrapper around the Anthropic API. Set FAKE_LLM=1 to run the whole pipeline offline with canned answers."""
import base64, json, os, re, sys

def clean(s):
    """Never let a key reach logs or files."""
    return re.sub(r"sk-[A-Za-z0-9_\-]{8,}", "[redacted-key]", str(s))[:300]

def fatal(msg):
    print("FATAL:", clean(msg), flush=True)
    sys.exit(1)  # stops the run with a red X; later steps (including saving state) are skipped

def get_key():
    raw = os.environ.get("ANTHROPIC_API_KEY", "")
    m = re.search(r"sk-ant-[A-Za-z0-9_\-]+", raw)  # pulls the key out even if extra text was pasted around it
    key = m.group(0) if m else raw.strip().strip('"').strip("'")
    if not key or "\n" in key or " " in key:
        fatal("ANTHROPIC_API_KEY secret is empty or is not a single key starting with sk-ant-. Re-create the secret with ONLY the key.")
    return key

def ask(model, system, user, image_paths=None, max_tokens=4000):
    import anthropic
    content = []
    for p in image_paths or []:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(open(p, "rb").read()).decode()}})
    content.append({"type": "text", "text": user})
    try:
        r = anthropic.Anthropic(api_key=get_key()).messages.create(model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": content}])
    except SystemExit:
        raise
    except Exception as ex:
        fatal(f"{type(ex).__name__}: {ex}")
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")

def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    try: return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", t, flags=re.S)
        if not m: raise
        return json.loads(m.group(1))

def ask_json(role, model, system, user, image_paths=None, max_tokens=4000):
    """role in {'ideas','story','judge'} (used only by the offline fake)."""
    if os.getenv("FAKE_LLM"):
        from . import fake
        return fake.answer(role, user)
    for attempt in range(2):
        txt = ask(model, system, user + ("" if attempt == 0 else "\n\nReturn ONLY valid JSON, nothing else."), image_paths, max_tokens)
        try: return parse_json(txt)
        except Exception: continue
    raise ValueError(f"{role}: model did not return valid JSON")
