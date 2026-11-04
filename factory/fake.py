"""Offline stand-in for the AI calls so the whole pipeline can be tested with no network or API key."""
import json, os
_n = {"judge": 0}
def answer(role, user):
    here = os.path.dirname(__file__)
    if role == "ideas": return {"ideas": [{"topic": f"test idea {i}", "category": "test", "fact_hook": "x"} for i in range(3)]}
    if role == "story":
        sb = json.load(open(os.path.join(here, "..", "samples", "sample_storyboard.json"))); return sb
    _n["judge"] += 1
    good = _n["judge"] >= 2
    sc = {k: (8.5 if good else 5.0) for k in ("hook", "humor", "clarity", "visuals", "pacing", "accuracy")}
    return {"scores": sc, "safety": True, "unverified_claims": [], "issues": [] if good else ["hook is weak"], "fixes": [] if good else ["make the hook a sharper question"]}
