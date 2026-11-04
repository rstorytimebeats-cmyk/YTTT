# What-If Factory

Makes a funny "What if..." Shorts video, has a **second AI rate it** (and sends it back for a rewrite until it's good), uploads it, and keeps a dashboard.
Runs on GitHub Actions twice a day, so it works while you are at school. Cost: GitHub is free for this; the Claude API costs a few cents per video attempt.

```
idea (Claude) -> storyboard JSON (Claude) -> validate -> render MP4 + synthesized audio -> independent judge (different Claude model, sees frames)
   score too low? -> rewrite with the judge's notes (up to MAX_ATTEMPTS) -> still bad? skip, never post it
   approved -> upload -> ledger + dashboard (docs/index.html)
```
Tested offline in this repo (render, validation, retry loop, dashboard). **Not tested live:** the Anthropic calls, YouTube upload, YouTube stats, Composio upload (they need your keys).

## Setup, easiest first

### Level 0: hand-off mode (no YouTube setup, start here)
1. Create a **private** GitHub repo, push this folder.
2. Get an API key at console.anthropic.com (separate from a claude.ai subscription). Add it as repo secret `ANTHROPIC_API_KEY`.
3. Actions tab > post-video > Run workflow. Every run makes a video, rejects weak ones, and attaches finished MP4s + title/description files to the run page (download on your phone, upload in the YouTube app: about 30 seconds).

### Level 1: automatic upload with your own Google project
1. console.cloud.google.com: new project. Enable **YouTube Data API v3** and **YouTube Analytics API**.
2. OAuth consent screen: External. **Publish it to "In production"**. If it stays in "Testing", Google expires your refresh token after 7 days and uploads silently stop.
3. Credentials > OAuth client ID > **Desktop app**. Download as `client_secret.json` into `scripts/`.
4. On your computer: `pip install -r requirements.txt && python scripts/get_refresh_token.py`. Log in with the channel's Google account. Copy the token it prints.
5. Repo secrets: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`. Repo variables: `UPLOADER=direct`, `PRIVACY=private`.
6. **Big catch:** YouTube locks every video uploaded through an *unaudited* API project (created after 2020-07-28) to **private**. Making them public needs YouTube's API compliance audit (a form on the YouTube API Services site; takes time and is not guaranteed). Until then, run with `PRIVACY=private` and either pass the audit, or use Level 0/2 for the public step.
7. Quota: each upload costs 1,600 units of the default 10,000/day, so max ~6 uploads/day. Twice a day is fine.

### Level 2: upload through Composio's YouTube connection
Set `UPLOADER=composio`, secret `COMPOSIO_API_KEY`, and connect YouTube in Composio. `factory/youtube.py: upload_composio` is untested; run `python scripts/composio_schema.py` to confirm argument names. Composio's shared quota can run out (it did during setup of this project).

## Dashboard (your "calendar + wallet")
`docs/index.html` is rebuilt every run. Turn on GitHub Pages (Settings > Pages > main /docs). Pages for private repos needs a paid GitHub plan; or make the repo public (state contains no secrets, only titles/stats).
Earnings come from YouTube Analytics (`estimatedRevenue`) once your channel is in the Partner Program. It is a read-only tracker; the app never touches money. Stats refresh every 3 hours (`stats.yml`). Per-second monitoring is not possible: YouTube's numbers don't update that fast and quota would run out.

## Knobs (repo Variables or env)
`PRIVACY` private|unlisted|public, `UPLOADER` none|direct|composio, `PASS_SCORE` (8.0), `MIN_EACH` (6.5), `MAX_ATTEMPTS` (4), `GEN_MODEL`, `JUDGE_MODEL`.
Edit the schedule in `.github/workflows/post.yml` (UTC; the defaults are 9 AM and 6 PM Pacific standard time; GitHub may start runs several minutes late).

## Know the risks before turning on "public + no review"
* **Monetization:** you need 1,000 subscribers plus 10M Shorts views in 90 days (or 4,000 watch hours). From Feb 1, 2027 new applicants need 20M views or 8,000 hours. YouTube also reduces reach and demonetizes mass-produced, repetitive content. Twice-daily identical-format videos are exactly what that policy targets; vary formats and add real creative input.
* **Accuracy:** an AI judge catches many mistakes, not all. One wrong "fact" posted unreviewed can hurt the channel. Keep `PRIVACY=private` for the first 2 weeks and read what it makes.
* **Safety words** in `factory/config.py: BANNED` block risky topics automatically.
* Never commit `client_secret.json` or tokens; use repo Secrets only.

## Offline test
`python tests/test_offline.py` (needs ffmpeg) runs the full loop with a fake AI.
