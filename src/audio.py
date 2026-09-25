"""Synthesised orchestral soundtrack, locked to the timeline's bar grid."""
import os
import numpy as np
from scipy.signal import butter, lfilter, fftconvolve
from scipy.io import wavfile

from timeline import SEGMENTS, TOTAL, BEAT, BAR, CHORDS

SR = 44100
rng = np.random.default_rng(7)
N = int((TOTAL + 5) * SR)
dry = np.zeros((2, N))
wet = np.zeros((2, N))  # reverb send


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def lp(x, fc, order=2):
    b, a = butter(order, min(fc, SR * 0.45) / (SR / 2))
    return lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = butter(order, fc / (SR / 2), btype="high")
    return lfilter(b, a, x)


def bp(x, lo, hi):
    b, a = butter(2, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return lfilter(b, a, x)


def saw(f, n, phase=None, vib=0.0):
    t = np.arange(n) / SR
    ph = rng.random() if phase is None else phase
    if vib:
        depth = vib * np.clip((t - 0.25) / 0.4, 0, 1)
        inst = f * (1 + depth * np.sin(2 * np.pi * 5.2 * t))
        p = np.cumsum(inst) / SR + ph
    else:
        p = f * t + ph
    return 2 * (p % 1.0) - 1


def env(n, a, r, sustain_end=None):
    e = np.ones(n)
    na = max(1, int(a * SR))
    e[:na] = np.linspace(0, 1, na)
    nr = max(1, int(r * SR))
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def put(sig, t, pan=0.0, gain=1.0, send=0.3):
    i = int(t * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    lg, rg = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    dry[0, i:i + len(sig)] += sig * lg
    dry[1, i:i + len(sig)] += sig * rg
    if send:
        wet[0, i:i + len(sig)] += sig * lg * send
        wet[1, i:i + len(sig)] += sig * rg * send


# ---------------------------------------------------------------- instruments

def pad(t, dur, chord, bright=1500, gain=0.05):
    bass, notes = CHORDS[chord]
    n = int((dur + 0.8) * SR)
    e = env(n, 0.35, 0.9)
    for m in notes + [bass + 12]:
        for det, pan in ((-0.08, -0.6), (0.0, 0.0), (0.08, 0.6)):
            s = lp(saw(mtof(m + det), n), bright) * e
            put(s, t, pan, gain, send=0.7)
    s = lp(saw(mtof(bass), n) + 0.5 * saw(mtof(bass - 12), n), 400) * e
    put(s, t, 0, gain * 1.6, send=0.2)


def spiccato(t, chord, gain=0.07):
    bass, _ = CHORDS[chord]
    root = bass + 12
    pattern = [0, 12, 7, 12, 0, 12, 7, 15 if chord.endswith("m") else 16]
    for k, off in enumerate(pattern):
        n = int(0.28 * SR)
        tt = np.arange(n) / SR
        e = np.exp(-tt / 0.07) * np.minimum(1, tt / 0.004)
        s = lp(saw(mtof(root + off), n) + saw(mtof(root + off + 0.1), n), 2600) * e
        put(s, t + k * BEAT / 2, 0.35 if k % 2 else -0.35, gain * (1.2 if k % 4 == 0 else 1), send=0.35)


def brass(t, midi, dur, gain=0.12, pan=0.0):
    n = int((dur + 0.35) * SR)
    tt = np.arange(n) / SR
    s = saw(mtof(midi), n, vib=0.006) + 0.8 * saw(mtof(midi + 0.07), n, vib=0.006) \
        + 0.5 * saw(mtof(midi - 12), n)
    # filter opens on attack: crude two-band blend
    a = np.clip(tt / 0.12, 0, 1)
    s = lp(s, 700) * (1 - a * 0.6) + lp(s, 2600) * a * 0.6
    e = env(n, 0.04, 0.3)
    put(s * e, t, pan, gain, send=0.6)


def kick(t, gain=0.9):
    n = int(0.9 * SR)
    tt = np.arange(n) / SR
    f = 42 + 110 * np.exp(-tt * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 5.5)
    s += lp(rng.standard_normal(n), 3000) * np.exp(-tt * 120) * 0.3
    put(np.tanh(s * 1.5), t, 0, gain, send=0.08)


def taiko(t, gain=0.6, pan=0.0):
    n = int(1.2 * SR)
    tt = np.arange(n) / SR
    f = 70 + 60 * np.exp(-tt * 18)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 4)
    s += lp(rng.standard_normal(n), 900) * np.exp(-tt * 25) * 0.6
    put(s, t, pan, gain, send=0.35)


def snare(t, gain=0.25, pan=0.1):
    n = int(0.35 * SR)
    tt = np.arange(n) / SR
    s = bp(rng.standard_normal(n), 1200, 7000) * np.exp(-tt * 22)
    s += np.sin(2 * np.pi * 190 * tt) * np.exp(-tt * 35) * 0.6
    put(s, t, pan, gain, send=0.25)


def hat(t, gain=0.05):
    n = int(0.08 * SR)
    tt = np.arange(n) / SR
    s = hp(rng.standard_normal(n), 8000) * np.exp(-tt * 70)
    put(s, t, 0.4, gain, send=0.05)


def crash(t, gain=0.22):
    n = int(3.0 * SR)
    tt = np.arange(n) / SR
    s = hp(rng.standard_normal(n), 4500) * np.exp(-tt * 1.6)
    put(s, t, -0.2, gain, send=0.5)


def timpani(t, midi=38, gain=0.5):
    n = int(1.8 * SR)
    tt = np.arange(n) / SR
    f = mtof(midi)
    s = (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 1.5 * tt)
         + 0.25 * np.sin(2 * np.pi * f * 2 * tt)) * np.exp(-tt * 2.2)
    s += lp(rng.standard_normal(n), 600) * np.exp(-tt * 30) * 0.5
    put(s, t, 0, gain, send=0.4)


def impact(t, gain=1.0):
    n = int(3.5 * SR)
    tt = np.arange(n) / SR
    f = 28 + 70 * np.exp(-tt * 4)
    s = np.tanh(2.2 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-tt * 1.3)
    s += lp(rng.standard_normal(n), 1500) * np.exp(-tt * 6) * 0.5
    put(s, t, 0, gain * 0.9, send=0.5)
    crash(t, 0.28)


def whoosh(t_end, dur=0.9, gain=0.18):
    n = int(dur * SR)
    tt = np.arange(n) / SR
    x = rng.standard_normal(n)
    ramp = (tt / dur) ** 3
    s = lp(x, 1200) * (1 - ramp) + hp(x, 1500) * ramp
    put(s * ramp, t_end - dur, 0, gain, send=0.6)


def riser(t, dur, gain=0.25):
    n = int(dur * SR)
    chunk = n // 24
    out = np.zeros(n)
    x = rng.standard_normal(n)
    for k in range(24):
        seg = x[k * chunk:(k + 1) * chunk + 512]
        f = 300 * (40 ** (k / 23))
        y = lp(seg, f)[: chunk if k < 23 else n - k * chunk]
        out[k * chunk:k * chunk + len(y)] = y
    out *= np.linspace(0, 1, n) ** 2
    put(out, t, 0, gain, send=0.6)


# ---------------------------------------------------------------- arrangement

def drums(t, level, bar_idx):
    s16 = BEAT / 4
    if level == 1:
        kick(t)
        timpani(t)
    elif level == 2:  # marching
        for k in (0, 8):
            kick(t + k * s16, 0.8)
        for k, acc in ((0, 1), (3, .5), (4, .8), (6, .5), (8, 1), (11, .5), (12, .8),
                       (13, .4), (14, .6), (15, .8)):
            snare(t + k * s16, 0.18 * acc)
        timpani(t, gain=0.35)
    elif level >= 3:
        for k in (0, 6, 8, 10):
            kick(t + k * s16, 0.85)
        for k in (4, 12):
            snare(t + k * s16, 0.3)
        for k in range(0, 16, 2):
            hat(t + k * s16, 0.05 if k % 4 else 0.08)
        taiko(t + 14 * s16, 0.45, -0.3)
        taiko(t + 15 * s16, 0.45, 0.3)
        if level >= 4:
            if bar_idx % 2 == 0:
                crash(t, 0.14)
            for k in (2, 3, 10, 11):
                taiko(t + k * s16, 0.3, 0.5 if k % 2 else -0.5)


def horn_line(t, chord):
    bass, _ = CHORDS[chord]
    r = bass + 24
    brass(t, r, BEAT * 2 * 0.95, 0.07, -0.2)
    brass(t + BEAT * 2, r + 7, BEAT * 0.95, 0.07, -0.2)
    brass(t + BEAT * 3, r + 12, BEAT * 0.95, 0.07, -0.2)


# Marseillaise, first phrase ("Allons enfants ... est arrivé"), G major, in beats
MARSEILLAISE = [
    (62, .75), (62, .25), (67, 1), (67, 1), (69, 1),
    (69, 1), (74, 1.5), (71, .5), (67, .75), (67, .25),
    (71, .75), (67, .25), (64, 1), (72, 2),
    (69, .75), (66, .25), (67, 3),
]
OUTRO_HALF = ["G", "G", "D", "G", "Em", "C", "D", "G"]

for seg in SEGMENTS:
    t0, kind, level = seg["start"], seg["kind"], seg["level"]
    if kind == "outro":
        # pickup "Al-" on the last sixteenth before the outro
        brass(t0 - BEAT / 4, 62, BEAT / 4, 0.16)
        bt = t0
        for m, d in MARSEILLAISE:
            brass(bt, m, d * BEAT * 0.97, 0.16)
            brass(bt, m - 12, d * BEAT * 0.97, 0.07, 0.3)
            bt += d * BEAT
        for h, c in enumerate(OUTRO_HALF):
            pad(t0 + h * BAR / 2, BAR / 2, c, bright=2200, gain=0.05)
            timpani(t0 + h * BAR / 2, CHORDS[c][0], 0.35)
            kick(t0 + h * BAR / 2, 0.6)
        crash(t0, 0.25)
        for b, c in enumerate(["C", "D"]):
            tb = t0 + (4 + b) * BAR
            pad(tb, BAR, c, bright=2600, gain=0.06)
            drums(tb, 3, b)
            spiccato(tb, c, 0.06)
        tf = t0 + 6 * BAR
        impact(tf, 1.0)
        pad(tf, BAR * 2.2, "G", bright=2600, gain=0.07)
        for m in (55, 59, 62, 67):
            brass(tf, m, BAR * 1.6, 0.08)
        for k in range(12):  # timpani roll dying out
            timpani(tf + k * BEAT / 3, 43, 0.25 * (1 - k / 12))
        continue

    for b in range(seg["bars"]):
        tb = t0 + b * BAR
        chord = seg["chords"][b]
        if kind == "flurry":
            pad(tb, BAR, chord, bright=1800 + 500 * b, gain=0.055)
            spiccato(tb, chord, 0.07)
            for k in range(16):
                snare(tb + k * BEAT / 4, 0.05 + 0.25 * (b * 16 + k) / 64)
            for k in range(0, 16, 4 if b < 2 else 2):
                kick(tb + k * BEAT / 4, 0.75)
            horn_line(tb, chord)
            continue
        pad(tb, BAR, chord, bright=900 + 350 * max(level, 0), gain=0.05)
        if kind == "chapter":
            impact(tb)
            timpani(tb + BEAT * 2, 38, 0.3)
            continue
        if kind == "title":
            if b == 0:
                impact(tb)
            timpani(tb, CHORDS[chord][0], 0.45)
            timpani(tb + BEAT * 2.5, CHORDS[chord][0], 0.25)
            if b == 2:
                for k in range(8):
                    timpani(tb + BEAT * 2 + k * BEAT / 4, 38, 0.1 + 0.05 * k)
            continue
        if kind == "line":
            timpani(tb, 38, 0.3)
            continue
        drums(tb, level, seg.get("index", 0))
        if level >= 3:
            spiccato(tb, chord, 0.06)
        if level >= 4 or (level == 3 and seg["chapter"]["key"] in ("soc",)):
            horn_line(tb, chord)
        if level == 2 and seg.get("index", 0) % 2 == 1:
            horn_line(tb, chord)

    # swell into each chapter card and the flurry
    if kind in ("chapter",):
        whoosh(t0)

flurry = next(s for s in SEGMENTS if s["kind"] == "flurry")
riser(flurry["start"], flurry["dur"] - BEAT / 2, 0.22)
whoosh(flurry["start"], 1.2, 0.2)

# ---------------------------------------------------------------- reverb + master
ir_len = int(2.6 * SR)
tt = np.arange(ir_len) / SR
irs = []
for c in range(2):
    ir = rng.standard_normal(ir_len) * np.exp(-tt * 2.6)
    ir = lp(ir, 5000)
    ir[: int(0.012 * SR)] = 0
    irs.append(ir / np.sqrt(np.sum(ir ** 2)))
rev = np.stack([fftconvolve(wet[c], irs[c])[:N] for c in range(2)])
mix = dry + rev * 0.55
mix = hp(mix, 28)
end = int((TOTAL + 3.5) * SR)
mix = mix[:, :end]
fade = int(3.0 * SR)
mix[:, -fade:] *= np.linspace(1, 0, fade)
mix /= np.max(np.abs(mix)) + 1e-9
mix = np.tanh(mix * 1.6) / np.tanh(1.6) * 0.93
os.makedirs(os.path.join(os.path.dirname(__file__), "..", "build"), exist_ok=True)
wavfile.write(os.path.join(os.path.dirname(__file__), "..", "build", "soundtrack.wav"), SR, (mix.T * 32767).astype(np.int16))
print("audio", mix.shape[1] / SR, "s")
