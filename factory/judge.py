import json
from . import config, llm, prompts
from .render import contact_sheet

CRITERIA = ("hook", "humor", "clarity", "visuals", "pacing", "accuracy")

def judge(sb, video_path):
    sheet = contact_sheet(video_path, 8, 4)
    r = llm.ask_json("judge", config.JUDGE_MODEL, prompts.JUDGE_SYSTEM, "Storyboard:\n" + json.dumps(sb), image_paths=[sheet], max_tokens=1500)
    s = {k: float(r.get("scores", {}).get(k, 0)) for k in CRITERIA}
    overall = round(sum(s.values()) / len(s), 2)
    unverified = r.get("unverified_claims", []) or []
    approved = (overall >= config.PASS_SCORE and min(s.values()) >= config.MIN_EACH and bool(r.get("safety", False)) and not unverified)
    return {"approved": approved, "overall": overall, "scores": s, "safety": bool(r.get("safety", False)),
            "unverified_claims": unverified, "issues": r.get("issues", []), "fixes": r.get("fixes", []), "sheet": sheet}
