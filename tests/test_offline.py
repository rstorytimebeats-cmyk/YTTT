"""Offline end-to-end test (no network, no API keys). Expects ffmpeg installed. Run: python tests/test_offline.py"""
import os, subprocess, sys, tempfile
d = tempfile.mkdtemp()
env = dict(os.environ, FAKE_LLM="1", RENDER_FPS="10", STATE_PATH=f"{d}/ledger.json", OUT_DIR=f"{d}/out")
r = subprocess.run([sys.executable, "-m", "factory.pipeline", "post", "--dry-run"], env=env, capture_output=True, text=True)
print(r.stdout[-800:]); assert "approved=True" in r.stdout and "READY" in r.stdout, r.stderr
print("OK")
