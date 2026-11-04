"""Procedural audio. No samples, no licensing issues: every sound is synthesized with numpy."""
import wave
import numpy as np

SR = 44100
SFX_NAMES = ["ding", "boing", "bonk", "sad", "whoosh", "hit", "riser", "cheer", "crickets", "pop", "buzz"]

def _T(d): return np.arange(int(d * SR)) / SR
def _noise(rng, d): return rng.standard_normal(int(d * SR))
def _lp(x, fc, o=4):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); return np.fft.irfft(X / (1 + (f / fc) ** o), len(x))
def _hp(x, fc, o=4):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); r = (f / fc) ** o; return np.fft.irfft(X * r / (1 + r), len(x))
def _glide(f0, f1, d, vib=0.0):
    t = _T(d); f = f0 * (f1 / f0) ** (t / d) * (1 + vib * np.sin(2 * np.pi * 6 * t)); return np.sin(2 * np.pi * np.cumsum(f) / SR)
def _kick(g=1.0):
    t = _T(.4); return np.sin(2 * np.pi * np.cumsum(45 + 130 * np.exp(-t * 32)) / SR) * np.exp(-t * 9) * g
def _tri(f, t): return 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * t))

def sfx(name, rng):
    if name == "ding":
        t = _T(1.0); return (np.sin(2 * np.pi * 1046.5 * t) + .4 * np.sin(2 * np.pi * 2093 * t)) * np.exp(-t * 5) * .35
    if name == "boing": return _glide(200, 700, .3, .03) * np.exp(-_T(.3) * 6) * .5
    if name == "bonk":
        t = _T(.6); return (_lp(_noise(rng, .6), 900) * np.exp(-t * 30) + np.sin(2 * np.pi * np.cumsum(180 * np.exp(-t * 20) + 60) / SR) * np.exp(-t * 12)) * .9
    if name == "sad":
        out = np.zeros(int(2.2 * SR)); i = 0
        for f, d in ((233, .5), (220, .5), (207, .5), (196, 1.1)):
            t = _T(d); w = _lp(2 * ((np.cumsum(f * (1 + .02 * np.sin(2 * np.pi * 5 * t))) / SR) % 1) - 1, 1200)
            seg = w * np.minimum(1, t * 40) * np.exp(-t * 1.2) * .35; out[i:i + len(seg)] += seg[:len(out) - i]; i += int(d * SR)
        return out
    if name == "whoosh":
        n = _noise(rng, .7); return _hp(_lp(n, 3500), 350) * np.sin(np.pi * np.arange(len(n)) / len(n)) ** 2 * .35
    if name == "hit":
        t = _T(.7); out = np.zeros(len(t)); k = _kick(1.0); out[:len(k)] += k
        return out + _hp(_noise(rng, .7), 1500) * np.exp(-t * 25) * .4
    if name == "riser":
        t = _T(1.2); return (np.sin(2 * np.pi * np.cumsum(200 * 8 ** (t / 1.2)) / SR) * (t / 1.2) ** 2 * .25 + _hp(_noise(rng, 1.2), 1500) * (t / 1.2) ** 2 * .2)
    if name == "cheer":
        n = _noise(rng, .8); return _hp(_lp(n, 3000), 500) * np.minimum(1, _T(.8) / .06) * np.exp(-_T(.8) * 3) * .6
    if name == "crickets":
        out = np.zeros(int(1.6 * SR))
        for k in range(3):
            for q in (0, .1):
                i = int((k * .5 + q) * SR); seg = np.sin(2 * np.pi * 4200 * _T(.05)) * np.exp(-_T(.05) * 40) * .12; out[i:i + len(seg)] += seg
        return out
    if name == "pop": return _glide(600, 1400, .1) * np.exp(-_T(.1) * 25) * .4
    if name == "buzz":
        t = _T(.5); return np.sign(np.sin(2 * np.pi * 120 * t)) * np.exp(-t * 4) * .25
    return np.zeros(10)

MOODS = {  # bpm, bass roots per chord, melody notes, pad chords
    "bouncy":  dict(bpm=120, roots=[65.41, 98.0, 110.0, 87.31], mel=[523.25, 587.33, 659.25, 783.99, 880.0],
                    pads=[[110, 164.81, 220, 261.63], [87.31, 130.81, 174.61, 261.63], [130.81, 196, 261.63, 329.63], [98, 146.83, 196, 246.94]]),
    "mystery": dict(bpm=92, roots=[55.0, 43.65, 65.41, 49.0], mel=[440.0, 523.25, 587.33, 659.25, 783.99],
                    pads=[[110, 130.81, 164.81, 220], [87.31, 130.81, 174.61, 207.65], [130.81, 155.56, 196, 261.63], [98, 123.47, 146.83, 196]]),
    "hype":    dict(bpm=130, roots=[73.42, 110.0, 98.0, 82.41], mel=[587.33, 659.25, 783.99, 880.0, 987.77],
                    pads=[[146.83, 220, 293.66, 369.99], [110, 164.81, 220, 277.18], [98, 146.83, 196, 246.94], [123.47, 185, 246.94, 311.13]]),
}

def build(events, dur, mood, music_from, music_to, out_path, seed=7):
    """events: list of (time_seconds, sfx_name). Writes a stereo 16-bit wav."""
    rng = np.random.default_rng(seed); N = int(dur * SR); L = np.zeros(N); R = np.zeros(N); ta = np.arange(N) / SR
    def add(sig, t0, g=1.0, pan=0.0):
        i = int(t0 * SR); n = min(len(sig), N - i)
        if n <= 0 or i < 0: return
        s = sig[:n] * g; L[i:i + n] += s * min(1, 1 - pan); R[i:i + n] += s * min(1, 1 + pan)
    m = MOODS.get(mood, MOODS["bouncy"]); step = 60.0 / m["bpm"] / 2
    j = 0
    while True:
        tb = music_from + step * j
        if tb >= music_to: break
        beat = int((tb - music_from) / (step * 2)); ci = (beat // 4) % 4
        if j % 2 == 0:
            tt = _T(.4); r = m["roots"][ci]; add((np.sin(2 * np.pi * r * tt) + .3 * np.sin(2 * np.pi * 2 * r * tt)) * np.exp(-tt * 5) * .3, tb)
            if j % 4 == 0: add(_kick(.55), tb)
        else:
            tt = _T(.15); add(_tri(m["mel"][(j * 3 + ci) % 5], tt) * np.exp(-tt * 20) * .12, tb, 1, .3 if j % 4 == 1 else -.3)
            add(np.diff(rng.standard_normal(int(.05 * SR)), prepend=0) * np.exp(-_T(.05) * 70) * .06, tb)
        j += 1
    P = np.zeros(N); seg = 4 * step * 2; k = 0
    while music_from + seg * k < music_to:
        s = music_from + seg * k; tt = _T(seg + .4); e = np.minimum(1, tt / .35) * np.minimum(1, (seg + .4 - tt) / .35)
        w = sum(np.sin(2 * np.pi * f * tt) + .4 * np.sin(2 * np.pi * f * 1.004 * tt) for f in m["pads"][k % 4]) * e * .06
        i = int(s * SR); n = min(len(w), N - i)
        if n > 0: P[i:i + n] += w[:n]
        k += 1
    L += P; R += np.roll(P, int(.012 * SR))
    for tev, name in events: add(sfx(name, rng), tev, 1.0, 0.0)
    L = np.tanh(L * 1.3); R = np.tanh(R * 1.3); pk = max(abs(L).max(), abs(R).max(), 1e-9); L *= .89 / pk; R *= .89 / pk
    fo = np.clip((dur - ta) / .6, 0, 1); L *= fo; R *= fo
    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((np.stack([L, R], 1) * 32767).astype("<i2").tobytes())
    return out_path
