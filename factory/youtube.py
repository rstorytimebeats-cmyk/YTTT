"""Uploading and monitoring. Three modes (config.UPLOADER): none (hand-off), direct (your own Google project), composio."""
import datetime as dt, os
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics.readonly", "https://www.googleapis.com/auth/yt-analytics-monetary.readonly"]

def _creds():
    from google.oauth2.credentials import Credentials
    return Credentials(None, refresh_token=os.environ["YT_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token",
                       client_id=os.environ["YT_CLIENT_ID"], client_secret=os.environ["YT_CLIENT_SECRET"], scopes=SCOPES)

def _svc(name="youtube", ver="v3"):
    from googleapiclient.discovery import build
    return build(name, ver, credentials=_creds(), cache_discovery=False)

def upload_direct(path, title, description, tags, privacy, category="27"):
    """videos.insert costs 1,600 quota units (default 10,000/day -> ~6 uploads/day).
    NOTE: API projects created after 2020-07-28 that have not passed YouTube's compliance audit get every upload LOCKED to private."""
    from googleapiclient.http import MediaFileUpload
    body = {"snippet": {"title": title[:100], "description": description[:4900], "tags": tags[:15], "categoryId": category},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    req = _svc().videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(path, mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True))
    resp = None
    while resp is None: _, resp = req.next_chunk()
    return {"id": resp["id"], "url": f"https://youtube.com/shorts/{resp['id']}"}

def upload_composio(path, title, description, tags, privacy, category="27"):
    """UNTESTED against a live account. Uses Composio's YouTube connection (needs COMPOSIO_API_KEY and a connected YouTube account).
    Argument names must match the tool schema; run scripts/composio_schema.py to print the current schema and adjust below if needed."""
    from composio import Composio
    c = Composio(api_key=os.environ["COMPOSIO_API_KEY"])
    r = c.tools.execute("YOUTUBE_UPLOAD_VIDEO", {"title": title[:100], "description": description, "tags": tags[:15], "categoryId": category,
                        "privacyStatus": privacy, "videoFilePath": path}, user_id=os.getenv("COMPOSIO_USER_ID", "default"), dangerously_skip_version_check=True)
    if not r.get("successful", True): raise RuntimeError(str(r.get("error")))
    data = r.get("data", {}); vid = data.get("id") or data.get("response_data", {}).get("id") or ""
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}" if vid else ""}

def upload(mode, **kw):
    if mode == "direct": return upload_direct(**kw)
    if mode == "composio": return upload_composio(**kw)
    return None

def channel_stats():
    r = _svc().channels().list(part="snippet,statistics", mine=True).execute()["items"][0]
    return {"title": r["snippet"]["title"], "subscribers": int(r["statistics"].get("subscriberCount", 0)), "views": int(r["statistics"].get("viewCount", 0)),
            "videos": int(r["statistics"].get("videoCount", 0))}

def video_stats(ids):
    out = {}
    for i in range(0, len(ids), 50):
        for it in _svc().videos().list(part="statistics", id=",".join(ids[i:i + 50])).execute().get("items", []):
            out[it["id"]] = int(it["statistics"].get("viewCount", 0))
    return out

def revenue(days=30):
    """Returns estimatedRevenue for the last N days, or None if the channel is not monetized / scope missing."""
    try:
        end = dt.date.today(); start = end - dt.timedelta(days=days)
        r = _svc("youtubeAnalytics", "v2").reports().query(ids="channel==MINE", startDate=str(start), endDate=str(end), metrics="estimatedRevenue").execute()
        return float(r["rows"][0][0]) if r.get("rows") else 0.0
    except Exception:
        return None
