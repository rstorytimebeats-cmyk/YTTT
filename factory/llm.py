"""Thin wrapper around the Anthropic API. Set FAKE_LLM=1 to run the whole pipeline offline with canned answers."""
import base64, json, os, re

def _client():
    import anthropic
    return anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

def ask(model, system, user, image_paths=None, max_tokens=4000):
    content = []
    for p in image_paths or []:
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(open(p, "rb").read()).decode()}})
    content.append({"type": "text", "text": user})
    r = _client().messages.create(model=model, max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": content}])
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
