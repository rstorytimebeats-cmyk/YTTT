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
    if getattr(r, "stop_reason", "") == "max_tokens": print("note: model hit the length limit", flush=True)
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text")

def _extent(t, i):
    """Index just past the bracket group starting at t[i], or -1 if it is never closed (cut-off answer)."""
    depth, in_str, esc = 0, False, False
    for j in range(i, len(t)):
        c = t[j]
        if in_str:
            if esc: esc = False
            elif c == "\\": esc = True
            elif c == '"': in_str = False
        elif c == '"': in_str = True
        elif c in "{[": depth += 1
        elif c in "}]":
            depth -= 1
            if depth == 0: return j + 1
    return -1

def parse_json(text):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    i = 0
    while i < len(t):
        if t[i] in "{[":
            end = _extent(t, i)
            if end == -1: raise ValueError("JSON was cut off")
            try: return json.loads(t[i:end])
            except json.JSONDecodeError: i = end; continue
        i += 1
    raise ValueError("no JSON found")

def ask_json(role, model, system, user, image_paths=None, max_tokens=4000):
    """role in {'ideas','story','judge'} (used only by the offline fake)."""
    if os.getenv("FAKE_LLM"):
        from . import fake
        return fake.answer(role, user)
    if role == "judge": max_tokens = max(max_tokens, 4000)
    for attempt in range(2):
        txt = ask(model, system, user + ("" if attempt == 0 else "\n\nReturn ONLY valid JSON, nothing else."), image_paths, max_tokens)
        try: return parse_json(txt)
        except Exception:
            print(f"{role}: unreadable answer ({len(txt)} chars): {clean(txt[:300])!r}", flush=True)
    if role == "judge":  # an unreadable review counts as a failed review, not a crash
        return {"scores": {}, "safety": False, "unverified_claims": [], "issues": ["reviewer answer was unreadable"], "fixes": ["keep the storyboard simple and factual"]}
    raise ValueError(f"{role}: model did not return valid JSON")
