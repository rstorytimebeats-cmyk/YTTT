"""Drawing helpers: fonts, text pop-ins, gradients, background decoration, and the stick-figure mascot (Bob)."""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1080, 1920, 30
CX = W // 2
clamp = lambda v, a=0.0, b=1.0: max(a, min(b, v))
lerp = lambda a, b, t: a + (b - a) * t
def smooth(t): t = clamp(t); return t * t * (3 - 2 * t)
def ease_out(t): t = clamp(t); return 1 - (1 - t) ** 3
def back(x):
    x = clamp(x); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

_FB = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
       "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"]
_FM = ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSansMono-Bold.ttf",
       "/Library/Fonts/Courier New Bold.ttf", "C:/Windows/Fonts/courbd.ttf"]
_fc = {}
def font(size, mono=False):
    k = (int(size), mono)
    if k not in _fc:
        for p in (_FM if mono else _FB):
            if os.path.exists(p):
                _fc[k] = ImageFont.truetype(p, int(size)); break
        else:
            try: _fc[k] = ImageFont.load_default(int(size))
            except TypeError: _fc[k] = ImageFont.load_default()
    return _fc[k]

_meas = ImageDraw.Draw(Image.new("L", (1, 1)))
def text_w(txt, f, stroke=0):
    l, t, r, b = _meas.textbbox((0, 0), txt, font=f, stroke_width=stroke); return r - l

def wrap(txt, size, maxw, mono=False, stroke=0):
    f = font(size, mono); lines, cur = [], ""
    for w in str(txt).split():
        t = (cur + " " + w).strip()
        if text_w(t, f, stroke) <= maxw or not cur: cur = t
        else: lines.append(cur); cur = w
    if cur: lines.append(cur)
    return lines

def fit(txt, size, maxw, mono=False, stroke=0, maxlines=2, minsize=32):
    """Shrink text until it fits in maxlines lines of width maxw (prevents text running off-screen)."""
    s = size
    while s >= minsize:
        ls = wrap(txt, s, maxw, mono, stroke)
        if len(ls) <= maxlines and all(text_w(l, font(s, mono), stroke) <= maxw for l in ls): return s, ls
        s -= 4
    return minsize, wrap(txt, minsize, maxw, mono, stroke)[:maxlines]

def pop(img, txt, x, y, size, fill, ts, dur=99.0, stroke=8, mono=False, out=.25, tilt=0, maxw=960, maxlines=2,
        color_stroke=(8, 10, 28, 255)):
    """Pop-in text with overshoot. ts = seconds since it should appear."""
    if ts < 0 or ts > dur or not txt: return
    s, lines = fit(txt, size, maxw, mono, stroke, maxlines)
    f = font(s, mono); lh = int(s * 1.18)
    lay = Image.new("RGBA", (maxw + 60, lh * len(lines) + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for i, ln in enumerate(lines):
        d.text((lay.width / 2, 20 + i * lh + lh / 2), ln, font=f, fill=fill, stroke_width=stroke,
               stroke_fill=color_stroke, anchor="mm")
    if tilt: lay = lay.rotate(tilt, expand=True, resample=Image.BICUBIC)
    sc = max(back(ts / .3), .01); a = clamp((dur - ts) / out) if ts > dur - out else 1.0
    lay = lay.resize((max(1, int(lay.width * sc)), max(1, int(lay.height * sc))), Image.BILINEAR)
    if a < 1: lay.putalpha(lay.split()[3].point(lambda v: int(v * a)))
    img.paste(lay, (int(x - lay.width / 2), int(y - lay.height / 2)), lay)

def grad(top, bot):
    g = np.linspace(0, 1, H)[:, None]
    col = (np.array(top)[None, :] * (1 - g) + np.array(bot)[None, :] * g).clip(0, 255).astype("uint8")
    return Image.fromarray(col[:, None, :]).resize((W, H))

# theme -> (top, bottom, accent, decoration)
THEMES = {
    "night":  ((6, 8, 26), (34, 22, 70), (255, 209, 102), "stars"),
    "ocean":  ((8, 40, 90), (10, 120, 170), (255, 220, 120), "bubbles"),
    "forest": ((10, 52, 36), (66, 132, 80), (255, 236, 130), "leaves"),
    "sunset": ((70, 20, 90), (236, 116, 84), (255, 255, 255), "embers"),
    "lab":    ((12, 28, 46), (28, 92, 120), (120, 255, 200), "grid"),
    "city":   ((18, 22, 40), (80, 90, 132), (255, 168, 90), "rain"),
}

class Deco:
    """Cheap animated background decoration, deterministic per time."""
    def __init__(self, kind, seed=3):
        r = np.random.default_rng(seed); self.kind = kind; n = 36
        self.x = r.random(n) * W; self.y = r.random(n); self.s = .4 + r.random(n); self.r = 6 + r.random(n) * 22
    def draw(self, img, t):
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov); k = self.kind
        for i in range(len(self.x)):
            if k == "stars":
                a = int(120 + 120 * math.sin(t * 2 + i)); d.rectangle([self.x[i], self.y[i] * H, self.x[i] + 3, self.y[i] * H + 3], fill=(255, 255, 255, a))
            elif k == "bubbles":
                y = H - ((self.y[i] * H + t * 90 * self.s[i]) % (H + 80)); d.ellipse([self.x[i] - self.r[i], y - self.r[i], self.x[i] + self.r[i], y + self.r[i]], outline=(255, 255, 255, 110), width=3)
            elif k in ("leaves", "embers"):
                up = k == "embers"; yy = (self.y[i] * H + t * 70 * self.s[i] * (-1 if up else 1)) % H
                xx = self.x[i] + 30 * math.sin(t + i); c = (255, 170, 80, 150) if up else (200, 255, 160, 120)
                d.ellipse([xx - self.r[i] / 3, yy - self.r[i] / 3, xx + self.r[i] / 3, yy + self.r[i] / 3], fill=c)
            elif k == "rain":
                y = (self.y[i] * H + t * 900 * self.s[i]) % H; d.line([(self.x[i], y), (self.x[i] - 14, y + 60)], fill=(200, 220, 255, 90), width=2)
            elif k == "grid" and i < 14:
                p = (t * 40 + i * 80) % H; d.line([(0, p), (W, p)], fill=(120, 255, 200, 40), width=2); d.line([(i * 80, 0), (i * 80, H)], fill=(120, 255, 200, 40), width=2)
        img.paste(ov, (0, 0), ov)

# ---------- mascot "Bob"
def _P(**k):
    P = dict(t1l=0, t2l=0, t1r=0, t2r=0, a1l=-8, a2l=-8, a1r=8, a2r=8, lean=0, hy=None); P.update(k); return P
def pose_for(name, t):
    s = math.sin
    if name == "shrug":  return _P(a1l=-75, a2l=-45, a1r=75, a2r=45, lean=2 * s(t * 3)), "o", 0.0
    if name == "dizzy":  return _P(lean=9 * s(t * 3), a1l=-30, a2l=-30, a1r=30, a2r=30), "o", 0.0
    if name == "dance":
        x = s(t * 8); return _P(a1l=90 + 80 * x, a2l=90 + 80 * x, a1r=90 - 80 * x, a2r=90 - 80 * x, t1l=12 * x, t1r=-12 * x), "smile", 0.0
    if name == "faint":  return _P(a1l=100, a2l=100, a1r=80, a2r=80), "x", -math.radians(90)
    if name == "run":
        x = s(t * 20); return _P(t1l=45 * x, t2l=45 * x - 55, t1r=-45 * x, t2r=-45 * x - 55, a1l=-45 * x, a2l=-45 * x - 30, a1r=45 * x, a2r=45 * x - 30, lean=14), "grit", 0.0
    if name == "panic":  return _P(a1l=150 + 10 * s(t * 25), a2l=150, a1r=-150 + 10 * s(t * 25), a2r=-150, lean=3 * s(t * 20)), "o", 0.0
    if name == "wave":   return _P(a1r=160 + 15 * s(t * 8), a2r=160 + 25 * s(t * 8 + 1), a1l=-8), "smile", 0.0
    return _P(lean=2 * s(t * 3)), "smile", 0.0

def _seg(d, items, wd):
    o = (18, 18, 30)
    for p0, p1, c in items:
        d.line([p0, p1], fill=o, width=wd + 8)
        for p in (p0, p1): d.ellipse([p[0] - (wd + 8) / 2, p[1] - (wd + 8) / 2, p[0] + (wd + 8) / 2, p[1] + (wd + 8) / 2], fill=o)
    for p0, p1, c in items:
        d.line([p0, p1], fill=c, width=wd)
        for p in (p0, p1): d.ellipse([p[0] - wd / 2, p[1] - wd / 2, p[0] + wd / 2, p[1] + wd / 2], fill=c)

def mascot(name, t, scale=1.0, shades=False):
    """Returns (RGBA layer, feet origin inside layer)."""
    P, face, rot = pose_for(name, t)
    lay = Image.new("RGBA", (700, 700), (0, 0, 0, 0)); d = ImageDraw.Draw(lay); ox, oy = 350, 640
    v = lambda a: (math.sin(math.radians(a)), math.cos(math.radians(a)))
    hy = P["hy"] or max(75 * math.cos(math.radians(P["t1" + s])) + 75 * math.cos(math.radians(P["t2" + s])) for s in "lr")
    cr, sr = math.cos(rot), math.sin(rot)
    T = lambda p: (ox + p[0] * cr - p[1] * sr, oy + p[0] * sr + p[1] * cr)
    hip = (0, -hy); ln = math.radians(P["lean"]); tx, ty = math.sin(ln), -math.cos(ln)
    sho = (hip[0] + 120 * tx, hip[1] + 120 * ty); head = (sho[0] + 46 * tx, sho[1] + 46 * ty)
    legs, arms = [], []
    for s, dk in (("l", -25), ("r", 0)):
        k1 = (hip[0] + 75 * v(P["t1" + s])[0], hip[1] + 75 * v(P["t1" + s])[1]); ft = (k1[0] + 75 * v(P["t2" + s])[0], k1[1] + 75 * v(P["t2" + s])[1])
        c = tuple(max(0, q + dk) for q in (48, 70, 150)); legs += [(T(hip), T(k1), c), (T(k1), T(ft), c)]
        e = (sho[0] + 80 * v(P["a1" + s])[0], sho[1] + 80 * v(P["a1" + s])[1]); h = (e[0] + 80 * v(P["a2" + s])[0], e[1] + 80 * v(P["a2" + s])[1])
        c = tuple(max(0, q + dk) for q in (255, 214, 170)); arms += [(T(sho), T(e), c), (T(e), T(h), c)]
    _seg(d, legs, 20); _seg(d, [(T(hip), T(sho), (255, 120, 40))], 34); _seg(d, arms, 16)
    hc = T(head); r = 36
    d.ellipse([hc[0] - r - 4, hc[1] - r - 4, hc[0] + r + 4, hc[1] + r + 4], fill=(18, 18, 30)); d.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], fill=(255, 214, 170))
    Pt = lambda dx, dy: T((head[0] + dx, head[1] + dy)); e1, e2 = Pt(8, -8), Pt(24, -8)
    for e in (e1, e2):
        if face == "x":
            d.line([(e[0] - 6, e[1] - 6), (e[0] + 6, e[1] + 6)], fill=(18, 18, 30), width=4); d.line([(e[0] - 6, e[1] + 6), (e[0] + 6, e[1] - 6)], fill=(18, 18, 30), width=4)
        else: d.ellipse([e[0] - 5, e[1] - 5, e[0] + 5, e[1] + 5], fill=(18, 18, 30))
    m = Pt(16, 14)
    if face == "smile": d.arc([m[0] - 12, m[1] - 12, m[0] + 12, m[1] + 8], 20, 160, fill=(18, 18, 30), width=4)
    elif face == "o": d.ellipse([m[0] - 8, m[1] - 8, m[0] + 8, m[1] + 8], outline=(18, 18, 30), width=4)
    elif face == "grit": d.line([(m[0] - 12, m[1]), (m[0] + 12, m[1])], fill=(18, 18, 30), width=5)
    else: d.arc([m[0] - 12, m[1] - 2, m[0] + 12, m[1] + 18], 200, 340, fill=(18, 18, 30), width=4)
    if shades:
        a, b = Pt(-2, -14), Pt(34, -2); d.rectangle([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])], fill=(10, 10, 14))
    d.line([Pt(-36, -16), Pt(36, -16)], fill=(230, 50, 50), width=8)
    if name == "dizzy":
        for k in range(3):
            a = t * 6 + k * 2.09; x, y = hc[0] + 70 * math.cos(a), hc[1] - 70 + 18 * math.sin(a)
            d.polygon([(x, y - 16), (x + 5, y - 5), (x + 16, y), (x + 5, y + 5), (x, y + 16), (x - 5, y + 5), (x - 16, y), (x - 5, y - 5)], fill=(255, 230, 80))
    if name in ("shrug", "panic"):
        yy = (t * 60) % 40; d.ellipse([hc[0] + 44, hc[1] - 30 + yy, hc[0] + 58, hc[1] - 8 + yy], fill=(120, 200, 255))
    if scale != 1.0: lay = lay.resize((int(700 * scale), int(700 * scale)), Image.BILINEAR)
    return lay, (int(ox * scale), int(oy * scale))

def paste_mascot(img, name, t, x, y, scale=1.0, **kw):
    lay, (fx, fy) = mascot(name, t, scale, **kw); img.paste(lay, (int(x - fx), int(y - fy)), lay)
