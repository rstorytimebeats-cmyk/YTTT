"""All state lives in one JSON file (committed back to the repo by the workflow) so nothing needs a database."""
import datetime as dt, html, json, os

SEED = ["you never slept again", "all the bees disappeared", "you stopped blinking", "dinosaurs came back", "humans could fly like birds",
        "the internet went down for a day", "you were shrunk to ant size", "you stood at the bottom of the Mariana Trench", "money disappeared overnight",
        "you ate only pizza for a month", "you held a lightning bolt", "you woke up in the year 1850", "you swam with a megalodon",
        "every car was electric tomorrow", "you lived on a boat for a year", "everyone spoke the same language", "you could breathe underwater",
        "cats ruled the world", "trees stopped growing", "you spent a week with no phone", "the oceans dried up",
        "you stepped on a Lego every hour for a day", "you could talk to animals", "you had a pet T. rex", "you ate a ghost pepper",
        "every road turned to ice", "you were the fastest runner alive", "you got stuck in an elevator for a week", "your whole city jumped in the pool at once"]

def now(): return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

def default():
    return {"queue": [{"topic": t, "category": "", "fact_hook": "", "status": "planned"} for t in SEED], "videos": [], "stats": {}, "stats_history": [],
            "earnings": [], "log": []}

def load(path):
    if not os.path.exists(path): return default()
    return json.load(open(path))

def save(ledger, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True); ledger["log"] = ledger["log"][-200:]
    json.dump(ledger, open(path, "w"), indent=2)

def log(ledger, msg):
    ledger["log"].append(f"{now()}  {msg}"); print(msg)

def ypp_progress(ledger):
    s = ledger.get("stats", {}); subs = s.get("subscribers", 0)
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=90)).strftime("%Y-%m-%d")
    views90 = sum(v.get("views", 0) for v in ledger["videos"] if v.get("date", "") >= cutoff)  # approximation of Shorts views in 90 days
    tiers = [("Expanded tier: 500 subs + 3M Shorts views (90d)", 500, 3e6), ("Full ad revenue (current): 1,000 subs + 10M Shorts views (90d)", 1000, 1e7),
             ("Full ad revenue, new applicants from Feb 1, 2027: 1,000 subs + 20M views", 1000, 2e7)]
    return [(n, min(100, subs / a * 100), min(100, views90 / b * 100)) for n, a, b in tiers], subs, views90

def dashboard(ledger, path="docs/index.html"):
    e = html.escape; s = ledger.get("stats", {}); tiers, subs, views90 = ypp_progress(ledger)
    rows = "".join(f"<tr><td>{e(v.get('date',''))}</td><td><a href='{e(v.get('url','#'))}'>{e(v['title'])}</a></td><td>{e(v.get('privacy',''))}</td><td>{v.get('score','')}</td><td>{v.get('views','-')}</td></tr>" for v in reversed(ledger["videos"]))
    nxt = "".join(f"<li>{e(q['topic'])}</li>" for q in [q for q in ledger["queue"] if q["status"] == "planned"][:14])
    earn = sum(x.get("amount", 0) for x in ledger.get("earnings", []))
    prog = "".join(f"<p><b>{e(n)}</b><br>subs {ps:.1f}%<div class=b><i style='width:{ps}%'></i></div>views {pv:.1f}%<div class=b><i style='width:{pv}%'></i></div></p>" for n, ps, pv in tiers)
    logs = e("\n".join(ledger["log"][-25:]))
    page = f"""<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>What-If Factory</title>
<style>body{{font:16px system-ui;max-width:820px;margin:auto;padding:16px;background:#0b1530;color:#eae7dc}}a{{color:#9fd3ff}}table{{width:100%;border-collapse:collapse}}td,th{{border-bottom:1px solid #2a3766;padding:6px;text-align:left}}
.b{{height:10px;background:#2a3766;border-radius:6px}}.b i{{display:block;height:100%;background:#ffd166;border-radius:6px}}pre{{white-space:pre-wrap;font-size:12px;color:#9aa3c7}}.k{{font-size:28px;font-weight:800}}</style>
<h1>What-If Factory</h1><p>Updated {e(now())}</p>
<h2>Channel</h2><p class=k>{e(str(s.get('title','(not connected yet)')))}</p><p>{subs:,} subscribers &middot; {s.get('views',0):,} total views &middot; {len(ledger['videos'])} videos made</p>
<h2>Earnings (from YouTube Analytics when available)</h2><p class=k>${earn:,.2f}</p>
<h2>Partner Program progress</h2>{prog}<p style="font-size:13px;color:#9aa3c7">Views are summed from videos in the last 90 days (approximation). Check YouTube Studio for official numbers.</p>
<h2>Next ideas</h2><ol>{nxt}</ol><h2>Videos</h2><table><tr><th>Date<th>Title<th>Privacy<th>AI score<th>Views</tr>{rows}</table><h2>Log</h2><pre>{logs}</pre>"""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True); open(path, "w").write(page); return path
