from . import config, llm, prompts
from .scenes import KINDS
from .audio import SFX_NAMES

def validate(sb):
    """Return a list of human-readable problems (empty = valid). These are fed back to the writer."""
    e = []; need = lambda c, m: (None if c else e.append(m))
    for k in ("title", "description", "hook", "beats", "outro"): need(k in sb, f"missing '{k}'")
    if e: return e
    need(len(sb["title"]) <= 100, "title too long"); need(4 <= len(sb["beats"]) <= 7, "need 4-7 beats")
    kinds = [b.get("kind") for b in sb["beats"]]; need(len(set(kinds)) >= 4, "use at least 4 different beat kinds"); need(kinds.count("reaction") == 1, "exactly one reaction beat")
    for i, b in enumerate(sb["beats"]):
        k = b.get("kind"); d = b.get("data", {}) or {}; p = f"beat {i+1} ({k})"
        if k not in KINDS: e.append(f"{p}: unknown kind"); continue
        need(len(b.get("headline", "")) <= 48, f"{p}: headline too long"); need(len(b.get("sub", "")) <= 80, f"{p}: sub too long")
        if b.get("sfx") and b["sfx"] not in SFX_NAMES: e.append(f"{p}: bad sfx")
        if k == "stat": need("value" in d, f"{p}: needs value")
        if k == "compare": need(all(x in d for x in ("a_value", "b_value", "a_label", "b_label")), f"{p}: needs a/b labels and values")
        if k == "meter": need(len(d.get("levels", [])) >= 3, f"{p}: needs 3-4 levels")
        if k == "timeline": need(3 <= len(d.get("points", [])) <= 5, f"{p}: needs 3-5 points")
        if k == "reaction": need(bool(d.get("bubble")), f"{p}: needs bubble")
        if k == "list": need(len(d.get("items", [])) == 3, f"{p}: needs exactly 3 items")
    need(bool(sb.get("facts")), "list your factual claims in 'facts'")
    blob = (sb["title"] + " " + str(sb["beats"])).lower()
    for w in config.BANNED:
        if w in blob: e.append(f"banned topic word: {w}")
    return e

def generate(idea, feedback=None, previous=None):
    user = f"Topic: What if {idea['topic']}?\nCategory: {idea.get('category', 'general')}\nFact hook: {idea.get('fact_hook', '')}"
    if previous and feedback:
        import json
        user += f"\n\nYour previous storyboard:\n{json.dumps(previous)}\n\nIt was rejected. Fix ALL of these:\n- " + "\n- ".join(feedback) + "\nReturn the full corrected storyboard."
    return llm.ask_json("story", config.GEN_MODEL, prompts.STORY_SYSTEM, user, max_tokens=5000)
