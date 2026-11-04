"""Orchestrator ("the manager"). Commands:
   python -m factory.pipeline post   [--dry-run] [--topic "..."]   idea -> storyboard -> render -> AI judge (retry loop) -> upload
   python -m factory.pipeline stats                                  refresh channel/video stats and earnings
   python -m factory.pipeline dashboard                              rebuild docs/index.html
"""
import argparse, json, os, re, shutil, subprocess, sys, traceback
from . import config, ideas, judge, ledger, render, storyboard, youtube

def slug(s): return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:50]

def qc(path, dur_expected):
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path]).decode())
    return [] if abs(d - dur_expected) < 1.5 and 15 <= d <= 59 else [f"bad duration {d:.1f}s"]

def make_video(L, idea):
    """The quality loop: write -> validate -> render -> independent AI review -> rewrite with feedback, up to MAX_ATTEMPTS."""
    feedback, prev = None, None
    for attempt in range(1, config.MAX_ATTEMPTS + 1):
        ledger.log(L, f"[{idea['topic']}] attempt {attempt}: writing storyboard")
        try: sb = storyboard.generate(idea, feedback, prev)
        except Exception as ex: ledger.log(L, f"writer error: {ex}"); feedback = ["Return valid JSON matching the schema."]; continue
        problems = storyboard.validate(sb)
        if problems: ledger.log(L, f"validation: {problems}"); feedback, prev = problems, sb; continue
        os.makedirs(config.OUT_DIR, exist_ok=True); path = os.path.join(config.OUT_DIR, f"{ledger.now()[:10]}_{slug(sb['title'])}_a{attempt}.mp4")
        info = render.render(sb, path); bad = qc(path, info["duration"]) if not os.getenv("RENDER_FPS") else []
        if bad: ledger.log(L, f"QC failed: {bad}"); feedback, prev = bad, sb; continue
        j = judge.judge(sb, path); ledger.log(L, f"judge: overall {j['overall']} {j['scores']} safety={j['safety']} approved={j['approved']}")
        if j["approved"]: return sb, path, j, attempt
        feedback = j["fixes"] + j["issues"] + [f"Unverified claim, remove or fix: {c}" for c in j["unverified_claims"]] + ([] if j["safety"] else ["Make it safer and less imitable."])
        prev = sb
    return None, None, None, config.MAX_ATTEMPTS

def cmd_post(a):
    L = ledger.load(config.STATE_PATH)
    idea = {"topic": a.topic, "category": "", "fact_hook": "", "status": "planned"} if a.topic else ideas.pick(L)
    sb, path, j, attempts = make_video(L, idea)
    if not sb:
        for q in L["queue"]:
            if q["topic"] == idea["topic"]: q["status"] = "rejected"
        ledger.log(L, f"REJECTED after {attempts} attempts, nothing posted: {idea['topic']}"); ledger.save(L, config.STATE_PATH); return 0
    rec = {"topic": idea["topic"], "title": sb["title"], "date": ledger.now()[:10], "score": j["overall"], "attempts": attempts, "privacy": config.PRIVACY,
           "file": path, "views": 0, "url": ""}
    desc = sb["description"] + ("\n\n#shorts #whatif" if "#shorts" not in sb["description"].lower() else "")
    if a.dry_run or config.UPLOADER == "none":
        ledger.log(L, f"READY (not uploaded; mode={'dry-run' if a.dry_run else 'hand-off'}): {path}")
        json.dump({"title": sb["title"], "description": desc, "tags": sb.get("tags", [])}, open(path + ".json", "w"), indent=2)
    else:
        try:
            r = youtube.upload(config.UPLOADER, path=path, title=sb["title"], description=desc, tags=sb.get("tags", []), privacy=config.PRIVACY, category=config.CATEGORY_ID)
            rec.update(id=r["id"], url=r["url"]); ledger.log(L, f"UPLOADED {r['url']} as {config.PRIVACY}")
        except Exception as ex:
            ledger.log(L, f"UPLOAD FAILED: {ex}"); json.dump({"title": sb["title"], "description": desc, "tags": sb.get("tags", [])}, open(path + ".json", "w"), indent=2)
            traceback.print_exc()
    L["videos"].append(rec)
    for q in L["queue"]:
        if q["topic"] == idea["topic"]: q["status"] = "done"
    ledger.save(L, config.STATE_PATH); ledger.dashboard(L); return 0

def cmd_stats(a):
    L = ledger.load(config.STATE_PATH)
    try:
        L["stats"] = youtube.channel_stats(); ids = [v["id"] for v in L["videos"] if v.get("id")]
        vs = youtube.video_stats(ids) if ids else {}
        for v in L["videos"]:
            if v.get("id") in vs: v["views"] = vs[v["id"]]
        rev = youtube.revenue(30)
        if rev is not None: L["earnings"] = [x for x in L["earnings"] if x.get("source") != "analytics-30d"] + [{"date": ledger.now()[:10], "source": "analytics-30d", "amount": rev}]
        L["stats_history"].append({"ts": ledger.now(), "subs": L["stats"]["subscribers"], "views": L["stats"]["views"]})
        ledger.log(L, f"stats: {L['stats']}")
    except Exception as ex: ledger.log(L, f"stats skipped: {ex}")
    ledger.save(L, config.STATE_PATH); ledger.dashboard(L); return 0

def main(argv=None):
    p = argparse.ArgumentParser(); sp = p.add_subparsers(dest="cmd", required=True)
    pp = sp.add_parser("post"); pp.add_argument("--dry-run", action="store_true"); pp.add_argument("--topic")
    sp.add_parser("stats"); sp.add_parser("dashboard")
    a = p.parse_args(argv)
    if a.cmd == "post": return cmd_post(a)
    if a.cmd == "stats": return cmd_stats(a)
    L = ledger.load(config.STATE_PATH); ledger.dashboard(L); return 0

if __name__ == "__main__": sys.exit(main())
