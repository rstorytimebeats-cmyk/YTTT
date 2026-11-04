"""Storyboard -> finished 1080x1920 MP4 (video + synthesized audio), via PIL frames piped into ffmpeg."""
import math, os, random, subprocess, tempfile
import numpy as np
from PIL import Image, ImageChops, ImageDraw
from . import audio
from .gfx import *
from .scenes import KINDS

HOOK, BEAT, OUTRO = 3.0, 4.2, 3.6
_yy, _xx = np.mgrid[0:H, 0:W]
VIG = (1 - .4 * (((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2) / 2).clip(.45, 1).astype("float32")[..., None]

def total_duration(sb): return HOOK + len(sb["beats"]) * BEAT + OUTRO

def render(sb, out_path, workdir=None):
    random.seed(sum(map(ord, sb.get("title", "x"))))
    workdir = workdir or tempfile.mkdtemp(prefix="wif_"); beats = sb["beats"]; dur = total_duration(sb)
    top, bot, acc, deco_kind = THEMES.get(sb.get("theme", "night"), THEMES["night"]); bg = grad(top, bot); deco = Deco(deco_kind)
    # ---- audio timeline
    ev = [(.12, "whoosh"), (HOOK - .12, "hit")]
    for i, b in enumerate(beats):
        t0 = HOOK + i * BEAT; ev += [(t0 + .02, "whoosh"), (t0 + 1.0, b.get("sfx") if b.get("sfx") in audio.SFX_NAMES else "pop")]
    t_out = HOOK + len(beats) * BEAT; ev += [(t_out + .1, "ding")]
    wav = audio.build(ev, dur, sb.get("mood", "bouncy"), HOOK, t_out, os.path.join(workdir, "a.wav"))
    fps = int(os.getenv("RENDER_FPS", FPS))  # set RENDER_FPS=10 for fast test renders
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                           "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", out_path], stdin=subprocess.PIPE)
    hook = sb["hook"]
    for i in range(int(dur * fps)):
        t = i / fps; img = bg.copy(); deco.draw(img, t); fx = {}; zoom = 1.0; flash = 0.0
        if t < HOOK:
            pop(img, hook.get("line1", "WHAT IF"), CX, 560, 200, acc + (255,), t - .1, stroke=11, maxlines=1)
            pop(img, hook.get("line2", ""), CX, 880, 92, (255, 255, 255, 255), t - .9, stroke=8, maxlines=3, tilt=-2)
            paste_mascot(img, "shrug", t, CX, 1450, 1.2)
            zoom = 1 + .06 * t / HOOK
            if t > HOOK - .2: fx["shake"] = 10
        elif t < t_out:
            k = min(int((t - HOOK) / BEAT), len(beats) - 1); u = t - HOOK - k * BEAT; b = beats[k]
            r = KINDS[b["kind"]](img, b, u, acc) or {}; fx.update(r)
            if u < .25: flash = .45 * (1 - u / .25); zoom = 1 + .05 * math.exp(-u * 10)
        else:
            u = t - t_out
            pop(img, sb["outro"].get("line1", "Follow for more WHAT IFs"), CX, 700, 80, acc + (255,), u, stroke=9, maxlines=2)
            pop(img, sb["outro"].get("line2", ""), CX, 900, 48, (255, 255, 255, 255), u - .5, stroke=6, maxlines=2)
            paste_mascot(img, "wave", u, CX, 1500, 1.3)
        if fx.get("shake"):
            a = fx["shake"]; img = ImageChops.offset(img, int(random.uniform(-a, a)), int(random.uniform(-a, a)))
        if zoom > 1.002:
            cw, ch = W / zoom, H / zoom; x0, y0 = (W - cw) / 2, (H - ch) / 2; img = img.resize((W, H), Image.BILINEAR, box=(x0, y0, x0 + cw, y0 + ch))
        if flash > 0: img = Image.blend(img, Image.new("RGB", (W, H), (255, 255, 255)), flash)
        arr = np.asarray(img.convert("RGB"), dtype=np.float32) * VIG; img = Image.fromarray(arr.clip(0, 255).astype("uint8"))
        if t > dur - .5: img = Image.blend(img, Image.new("RGB", (W, H), (0, 0, 0)), smooth((t - (dur - .5)) / .5))
        ff.stdin.write(img.tobytes())
    ff.stdin.close(); rc = ff.wait()
    if rc != 0: raise RuntimeError("ffmpeg failed")
    return {"path": out_path, "duration": dur}

def contact_sheet(video_path, n=8, cols=4):
    """Evenly spaced frames in one PNG grid (for the AI judge and for humans)."""
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video_path]).decode().strip())
    tw, th = 270, 480; rows = math.ceil(n / cols); sheet = Image.new("RGB", (tw * cols, th * rows)); tmp = tempfile.mkdtemp(prefix="cs_")
    for i in range(n):
        p = os.path.join(tmp, f"{i}.png"); ts = (i + .5) * d / n
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ts:.2f}", "-i", video_path, "-frames:v", "1", p], check=True)
        sheet.paste(Image.open(p).convert("RGB").resize((tw, th)), ((i % cols) * tw, (i // cols) * th))
    out = os.path.join(tmp, "sheet.png"); sheet.save(out); return out
