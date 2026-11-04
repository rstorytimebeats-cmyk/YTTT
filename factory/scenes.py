"""Reusable animated scenes. Each draws onto `img` given local time `u` (seconds into the beat).
Every scene returns an optional dict of effects: {"shake": px}."""
import math
from PIL import Image, ImageDraw
from .gfx import *

WHITE = (255, 255, 255, 255); SOFT = (234, 231, 220, 255)

def _num(v):
    try: return float(str(v).replace(",", "").strip())
    except Exception: return None

def _fmt(x, ref):
    r = _num(ref)
    if r is not None and float(r).is_integer(): return f"{int(round(x)):,}"
    return f"{x:,.1f}"

def _frame(img, b, u, acc):
    pop(img, b.get("headline", ""), CX, 380, 74, WHITE, u, stroke=8, maxlines=2)
    if b.get("sub"): pop(img, b["sub"], CX, 1500, 46, SOFT, u - .7, stroke=6, maxlines=2)

def stat(img, b, u, acc):
    _frame(img, b, u, acc); d = b.get("data", {}); v = d.get("value", "?"); n = _num(v); fx = {}
    if n is not None:
        k = ease_out(u / 1.6); shown = _fmt(n * k, v)
    else: shown = str(v)
    land = u >= 1.6; z = 1 + (.12 * math.exp(-(u - 1.6) * 9) if land else 0)
    pop(img, shown, CX, int(900 * 1), int(200 * z), acc + (255,), u - .1, stroke=10, mono=True, maxw=980, maxlines=1)
    pop(img, d.get("unit", ""), CX, 1060, 78, WHITE, u - .5, stroke=8)
    pop(img, d.get("label", ""), CX, 1250, 52, SOFT, u - 1.0, stroke=6, maxlines=2)
    if land and u < 1.9: fx["shake"] = 12 * math.exp(-(u - 1.6) * 12)
    return fx

def compare(img, b, u, acc):
    _frame(img, b, u, acc); d = b.get("data", {}); av, bv = _num(d.get("a_value")) or 0, _num(d.get("b_value")) or 0
    mx = max(av, bv, 1e-9); dr = ImageDraw.Draw(img); base, maxh = 1260, 600
    for i, (lab, val, col, x) in enumerate((("a_label", av, (159, 211, 255), 300), ("b_label", bv, acc, 780))):
        k = ease_out((u - .3 - i * .35) / 1.2); h = max(6, int(maxh * (val / mx) * k))
        dr.rounded_rectangle([x - 130, base - h, x + 130, base], 22, fill=col, outline=(18, 18, 30), width=5)
        shown = _fmt(val * k, d.get("a_value" if i == 0 else "b_value"))
        pop(img, f"{shown} {d.get('unit', '')}".strip(), x, base - h - 60, 54, WHITE, u - .5 - i * .35, stroke=7, maxw=420, mono=True)
        pop(img, str(d.get(lab, "")), x, base + 70, 44, SOFT, u - .3 - i * .35, stroke=6, maxw=420, maxlines=2)
    return {}

def meter(img, b, u, acc):
    _frame(img, b, u, acc); d = b.get("data", {}); levels = d.get("levels") or ["Fine", "Weird", "Yikes", "Run"]
    tgt = clamp(_num(d.get("target")) if _num(d.get("target")) is not None else .8); k = ease_out(u / 2.4) * tgt
    dr = ImageDraw.Draw(img); x0, x1, y0, y1 = 90, 990, 860, 950
    dr.rounded_rectangle([x0, y0, x1, y1], 30, fill=(20, 24, 50), outline=(255, 255, 255), width=5)
    w = int((x1 - x0) * k)
    for i in range(0, max(w, 1), 6):
        t = i / (x1 - x0); c = (int(lerp(60, 255, clamp(t * 1.6))), int(lerp(220, 40, clamp(t * 1.4))), 70)
        dr.rectangle([x0 + i, y0 + 6, min(x0 + i + 6, x0 + w), y1 - 6], fill=c)
    px = x0 + w; dr.polygon([(px, y0 - 14), (px - 26, y0 - 56), (px + 26, y0 - 56)], fill=(255, 255, 255), outline=(18, 18, 30))
    pop(img, str(d.get("label", "Meter")), CX, 740, 54, acc + (255,), u - .2, stroke=7)
    idx = min(len(levels) - 1, int(k / max(tgt, .01) * (len(levels) - 1) + .001)) if tgt > 0 else 0
    for i, lv in enumerate(levels):
        pos = x0 + (x1 - x0) * (i + .5) / len(levels); cur = (i <= idx)
        pop(img, str(lv), pos, 1040 + (i % 2) * 70, 34 if not cur else 38, WHITE if cur else (150, 150, 170, 255), u - .3, stroke=5, maxw=240, maxlines=1)
    return {"shake": 6 * math.sin(u * 40) * (k > .5)} if k > .5 else {}

def timeline(img, b, u, acc):
    _frame(img, b, u, acc); pts = (b.get("data", {}).get("points") or [])[:5]; dr = ImageDraw.Draw(img)
    top = 560; gap = 190
    if pts: dr.line([(170, top), (170, top + gap * (len(pts) - 1))], fill=(255, 255, 255), width=8)
    for i, p in enumerate(pts):
        ts = u - .3 - i * .75; y = top + i * gap
        if ts < 0: continue
        r = int(26 * back(ts / .3)); dr.ellipse([170 - r, y - r, 170 + r, y + r], fill=acc, outline=(18, 18, 30), width=5)
        pop(img, str(p.get("when", "")), 640, y - 34, 52, acc + (255,), ts, stroke=7, maxw=700, maxlines=1)
        pop(img, str(p.get("what", "")), 640, y + 32, 40, WHITE, ts - .1, stroke=6, maxw=700, maxlines=2)
    return {}

def reaction(img, b, u, acc):
    d = b.get("data", {}); pose = d.get("pose", "shrug")
    pop(img, b.get("headline", ""), CX, 380, 74, WHITE, u, stroke=8, maxlines=2)
    # speech bubble
    bt = d.get("bubble", "")
    if bt:
        ts = u - .5
        if ts >= 0:
            s, lines = fit(bt, 56, 700, stroke=0, maxlines=3); lh = int(s * 1.2); h = lh * len(lines) + 70
            lay = Image.new("RGBA", (800, h + 60), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
            ld.rounded_rectangle([20, 10, 780, 10 + h], 36, fill=(255, 255, 255, 255), outline=(18, 18, 30, 255), width=6)
            ld.polygon([(390, 10 + h - 2), (450, 10 + h - 2), (430, h + 56)], fill=(255, 255, 255, 255), outline=(18, 18, 30, 255))
            for i, ln in enumerate(lines): ld.text((400, 10 + 35 + i * lh + lh / 2), ln, font=font(s), fill=(18, 18, 30, 255), anchor="mm")
            sc = max(back(ts / .3), .01); lay = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BILINEAR)
            img.paste(lay, (int(CX - lay.width / 2), int(700 - lay.height / 2)), lay)
    paste_mascot(img, pose, u, CX, 1400, 1.35)
    if b.get("sub"): pop(img, b["sub"], CX, 1500, 46, SOFT, u - .9, stroke=6, maxlines=2)
    return {"shake": 10 * math.exp(-u * 10)} if u < .4 else {}

def listing(img, b, u, acc):
    _frame(img, b, u, acc); items = (b.get("data", {}).get("items") or [])[:3]; dr = ImageDraw.Draw(img)
    for i, it in enumerate(items):
        ts = u - .3 - i * .6
        if ts < 0: continue
        x = lerp(1100, 0, back(ts / .35)); y = 560 + i * 250
        dr.rounded_rectangle([60 + x, y, 1020 + x, y + 200], 30, fill=(20, 26, 60), outline=acc, width=6)
        dr.ellipse([90 + x, y + 50, 190 + x, y + 150], fill=acc, outline=(18, 18, 30), width=5)
        dr.text((140 + x, y + 100), str(i + 1), font=font(60), fill=(18, 18, 30), anchor="mm")
        s, ls = fit(str(it), 46, 700, maxlines=2)
        for j, ln in enumerate(ls): dr.text((230 + x, y + 100 + (j - (len(ls) - 1) / 2) * int(s * 1.2)), ln, font=font(s), fill=(255, 255, 255), anchor="lm")
    return {}

KINDS = {"stat": stat, "compare": compare, "meter": meter, "timeline": timeline, "reaction": reaction, "list": listing}
