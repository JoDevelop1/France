"""Frame renderer: pipes 1920x1080 frames straight into ffmpeg with the soundtrack."""
import math
import os
import subprocess
import sys
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from timeline import SEGMENTS, TOTAL, FPS, W, H, BEAT, BAR

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
FONTS = "/usr/share/fonts/truetype"
SERIF_B = f"{FONTS}/liberation/LiberationSerif-Bold.ttf"
SERIF_I = f"{FONTS}/liberation/LiberationSerif-Italic.ttf"
SANS_B = f"{FONTS}/dejavu/DejaVuSans-Bold.ttf"

BLEU = (0, 85, 214)
BLEU_CLAIR = (110, 150, 255)
ROUGE = (237, 41, 57)
BLANC = (245, 245, 240)
OR = (222, 184, 92)

THEMES = {  # top colour, bottom colour, motif colour
    "mil": ((16, 24, 52), (3, 5, 16), (70, 90, 140)),
    "sci": ((6, 30, 58), (1, 8, 20), (80, 150, 210)),
    "eng": ((8, 36, 82), (2, 10, 30), (70, 120, 190)),
    "soc": ((70, 10, 20), (16, 2, 6), (150, 40, 55)),
    "cul": ((40, 24, 10), (8, 4, 2), (170, 130, 60)),
}


def font(path, size):
    return _font(path, int(size))


@lru_cache(maxsize=64)
def _font(path, size):
    return ImageFont.truetype(path, size)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 3 * x * x - 2 * x * x * x


# ---------------------------------------------------------------- text layers

@lru_cache(maxsize=512)
def text_layer(text, path, size, fill, tracking=0, shadow=True, glow=0):
    f = font(path, size)
    if tracking:
        w = sum(f.getlength(c) for c in text) + tracking * (len(text) - 1)
    else:
        w = f.getlength(text)
    asc, desc = f.getmetrics()
    pad = max(30, glow * 3)
    img = Image.new("RGBA", (int(w) + 2 * pad, asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if tracking:
        x = pad
        for c in text:
            d.text((x, pad), c, font=f, fill=fill)
            x += f.getlength(c) + tracking
    else:
        d.text((pad, pad), text, font=f, fill=fill)
    if shadow or glow:
        a = img.getchannel("A")
        base = Image.new("RGBA", img.size, (0, 0, 0, 0))
        if shadow:
            sh = Image.new("RGBA", img.size, (0, 0, 0, 255))
            sh.putalpha(a.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.7)))
            base.alpha_composite(sh, (0, 6))
        if glow:
            gl = Image.new("RGBA", img.size, fill[:3] + (255,))
            gl.putalpha(a.filter(ImageFilter.GaussianBlur(glow)).point(lambda v: min(255, int(v * 1.3))))
            base.alpha_composite(gl)
        base.alpha_composite(img)
        img = base
    return img, pad


def wrap(text, path, size, maxw):
    f = font(path, size)
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if f.getlength(test) > maxw and cur:
            lines.append(cur)
            cur = w
        else:
            cur = test
    lines.append(cur)
    return lines


def paste(base, layer, x, y, alpha=1.0, scale=1.0):
    if alpha <= 0.003:
        return
    if scale != 1.0:
        nw, nh = max(1, int(layer.width * scale)), max(1, int(layer.height * scale))
        x += (layer.width - nw) / 2
        y += (layer.height - nh) / 2
        layer = layer.resize((nw, nh), Image.BILINEAR)
    if alpha < 0.997:
        layer = layer.copy()
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * alpha)))
    x, y = int(round(x)), int(round(y))
    # clip to canvas
    l, t = max(0, -x), max(0, -y)
    r, b = min(layer.width, base.width - x), min(layer.height, base.height - y)
    if r <= l or b <= t:
        return
    if (l, t, r, b) != (0, 0, layer.width, layer.height):
        layer = layer.crop((l, t, r, b))
    base.alpha_composite(layer, (x + l, y + t))


def place(base, text, path, size, fill, cx=None, x=None, y=0, alpha=1.0, scale=1.0,
          tracking=0, shadow=True, glow=0):
    """Draw text with its visual top-left (or centre if cx) at the given position."""
    img, pad = text_layer(text, path, size, fill, tracking, shadow, glow)
    if cx is not None:
        px = cx - img.width / 2
    else:
        px = x - pad
    paste(base, img, px, y - pad, alpha, scale)
    return img.width - 2 * pad


# ---------------------------------------------------------------- backgrounds

BW, BH = W + 160, H + 90


def gradient(top, bottom, w=BW, h=BH):
    t = np.linspace(0, 1, h)[:, None, None]
    arr = np.array(top)[None, None] * (1 - t) + np.array(bottom)[None, None] * t
    return np.broadcast_to(arr, (h, w, 3)).astype(np.float32)


@lru_cache(maxsize=8)
def theme_bg(key):
    top, bottom, mc = THEMES[key]
    arr = gradient(top, bottom)
    img = Image.fromarray(arr.astype(np.uint8)).convert("RGBA")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    r = np.random.default_rng(hash(key) % 1000)
    if key == "mil":
        for x in range(-BH, BW, 70):
            d.line([(x, BH), (x + BH, 0)], fill=mc + (26,), width=18)
        for _ in range(40):
            cx, cy, s = r.uniform(0, BW), r.uniform(0, BH), r.uniform(4, 12)
            pts = [(cx + s * math.cos(a) * (1 if k % 2 == 0 else .42),
                    cy + s * math.sin(a) * (1 if k % 2 == 0 else .42))
                   for k, a in enumerate(np.linspace(-math.pi / 2, 1.5 * math.pi, 11)[:-1])]
            d.polygon(pts, fill=mc + (60,))
    elif key == "sci":
        cx, cy = BW * 0.78, BH * 0.45
        for k in range(1, 12):
            rx, ry = 90 * k, 38 * k
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=mc + (34,), width=2)
        for _ in range(160):
            x, y, s = r.uniform(0, BW), r.uniform(0, BH), r.uniform(1, 3.5)
            d.ellipse([x - s, y - s, x + s, y + s], fill=mc + (int(r.uniform(30, 110)),))
    elif key == "eng":
        for x in range(0, BW, 40):
            d.line([(x, 0), (x, BH)], fill=mc + (40 if x % 200 == 0 else 16,), width=1)
        for y in range(0, BH, 40):
            d.line([(0, y), (BW, y)], fill=mc + (40 if y % 200 == 0 else 16,), width=1)
        cx, cy = BW * 0.8, BH * 0.5
        for k in range(3):
            d.ellipse([cx - 160 - 90 * k, cy - 160 - 90 * k, cx + 160 + 90 * k, cy + 160 + 90 * k],
                      outline=mc + (50,), width=2)
        d.line([(cx - 500, cy), (cx + 500, cy)], fill=mc + (50,), width=2)
        d.line([(cx, cy - 500), (cx, cy + 500)], fill=mc + (50,), width=2)
    elif key == "soc":
        cx, cy = BW * 0.5, BH * 1.15
        for k in range(36):
            a0 = math.pi + k * math.pi / 36
            a1 = a0 + math.pi / 72
            d.polygon([(cx, cy), (cx + 3000 * math.cos(a0), cy + 3000 * math.sin(a0)),
                       (cx + 3000 * math.cos(a1), cy + 3000 * math.sin(a1))], fill=mc + (30,))
    elif key == "cul":
        m = 70
        for (x0, y0, sx, sy) in ((m, m, 1, 1), (BW - m, m, -1, 1), (m, BH - m, 1, -1), (BW - m, BH - m, -1, -1)):
            for k in range(3):
                o = k * 16
                d.line([(x0 + sx * o, y0 + sy * o), (x0 + sx * (260 - o), y0 + sy * o)], fill=mc + (90,), width=3)
                d.line([(x0 + sx * o, y0 + sy * o), (x0 + sx * o, y0 + sy * (260 - o))], fill=mc + (90,), width=3)
            d.ellipse([x0 + sx * 40 - 8, y0 + sy * 40 - 8, x0 + sx * 40 + 8, y0 + sy * 40 + 8], fill=mc + (120,))
        for _ in range(120):
            x, y, s = r.uniform(0, BW), r.uniform(0, BH), r.uniform(1, 3)
            d.ellipse([x - s, y - s, x + s, y + s], fill=mc + (int(r.uniform(30, 120)),))
    img.alpha_composite(ov)
    return img


def bg_crop(img, p, zoom=1.0):
    """Slow camera drift across an oversized background (p in 0..1)."""
    ox = (BW - W) * p
    oy = (BH - H) * (0.5 + 0.3 * math.sin(p * math.pi))
    if zoom == 1.0:
        return img.crop((int(ox), int(oy), int(ox) + W, int(oy) + H))
    cw, ch = W / zoom, H / zoom
    ox += (W - cw) / 2
    oy += (H - ch) / 2
    return img.crop((int(ox), int(oy), int(ox + cw), int(oy + ch))).resize((W, H), Image.BILINEAR)


@lru_cache(maxsize=4)
def plain_bg(top, bottom):
    return Image.fromarray(gradient(top, bottom, W, H).astype(np.uint8)).convert("RGBA")


# ---------------------------------------------------------------- post effects

_rng = np.random.default_rng(3)
GRAIN = [(_rng.standard_normal((H // 2, W // 2, 1)) * 3.5).astype(np.float32) for _ in range(6)]
yy, xx = np.mgrid[0:H, 0:W]
_d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = (1 - 0.42 * np.clip(_d - 0.35, 0, 1) ** 1.6)[..., None].astype(np.float32)
del yy, xx, _d


def finish(img, fi, flash=0.0, fade=1.0):
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    arr *= VIGNETTE
    if flash > 0:
        arr += (255 - arr) * flash
    g = GRAIN[fi % len(GRAIN)]
    arr += np.repeat(np.repeat(g, 2, axis=0), 2, axis=1)
    if fade < 1:
        arr *= fade
    return np.clip(arr, 0, 255).astype(np.uint8)


def tricolore(d, x, y, w, h, alpha=255):
    s = w / 3
    d.rectangle([x, y, x + s, y + h], fill=BLEU + (alpha,))
    d.rectangle([x + s, y, x + 2 * s, y + h], fill=BLANC + (alpha,))
    d.rectangle([x + 2 * s, y, x + w, y + h], fill=ROUGE + (alpha,))


# ---------------------------------------------------------------- scenes

PARTICLES = np.random.default_rng(11).random((140, 4))


def dust(img, t, color=OR, strength=1.0):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for px, py, sp, sz in PARTICLES:
        x = (px * W + math.sin(t * 0.4 + py * 9) * 30) % W
        y = (py * H - t * (10 + sp * 25)) % H
        s = 1 + sz * 2.4
        a = int((40 + 120 * sz) * strength * (0.6 + 0.4 * math.sin(t * 2 + px * 20)))
        d.ellipse([x - s, y - s, x + s, y + s], fill=color + (max(0, a),))
    img.alpha_composite(ov)


def scene_line(seg, lt, fi, gt):
    img = plain_bg((10, 12, 22), (0, 0, 0)).copy()
    dust(img, gt, strength=0.8)
    a = ease_out(lt / 0.6) * (1 - ease_in_out((lt - (seg["dur"] - 0.35)) / 0.35))
    place(img, seg["text"], SERIF_I, 76, BLANC, cx=W / 2, y=H / 2 - 50, alpha=a,
          scale=1.0 + 0.04 * lt / seg["dur"])
    return finish(img, fi)


def scene_title(seg, lt, fi, gt):
    img = plain_bg((6, 14, 44), (0, 0, 8)).copy()
    dust(img, gt, color=BLANC, strength=0.7)
    d = ImageDraw.Draw(img)
    # stripes sweep in, then retract into a thin band under the title
    p_in = ease_out(lt / 0.5)
    p_out = ease_in_out((lt - 0.9) / 0.7)
    band_h = 8
    cols = (BLEU, BLANC, ROUGE)
    final_w = 540
    for k, c in enumerate(cols):
        full_x0 = k * W / 3
        fin_x0 = W / 2 - final_w / 2 + k * final_w / 3
        x0 = full_x0 + (fin_x0 - full_x0) * p_out
        w = W / 3 + (final_w / 3 - W / 3) * p_out
        top_full = 0 if k != 1 else H * (1 - p_in)
        h_full = H * p_in
        y_fin = H / 2 + 150
        y0 = (top_full if k == 1 else 0) * (1 - p_out) + y_fin * p_out
        h = h_full * (1 - p_out) + band_h * p_out
        if k != 1:
            h = h_full * (1 - p_out) + band_h * p_out
        d.rectangle([x0, y0, x0 + w, y0 + h], fill=c + (255,))
    a = ease_out((lt - 1.2) / 0.8)
    place(img, "FRANCE", SERIF_B, 250, BLANC, cx=W / 2, y=H / 2 - 190, alpha=a,
          scale=1.08 - 0.08 * ease_out((lt - 1.2) / 2.5) + 0.015 * lt / seg["dur"],
          tracking=48, glow=26)
    a2 = ease_out((lt - 2.0) / 0.8)
    place(img, "QUINZE SIÈCLES D'HISTOIRE", SANS_B, 34, OR, cx=W / 2, y=H / 2 + 200,
          alpha=a2, tracking=14, shadow=False)
    flash = 0.0
    return finish(img, fi, flash)


def scene_chapter(seg, lt, fi, gt):
    ch = seg["chapter"]
    img = bg_crop(theme_bg(ch["key"]), lt / seg["dur"] * 0.3, zoom=1.12 - 0.1 * ease_out(lt / 1.2))
    img = img.copy()
    d = ImageDraw.Draw(img)
    a = ease_out(lt / 0.35)
    place(img, ch["num"], SERIF_B, 150, OR, cx=W / 2, y=H / 2 - 250, alpha=a, glow=18)
    wname = place(img, ch["name"], SERIF_B, 104, BLANC, cx=W / 2, y=H / 2 - 40,
                  alpha=ease_out((lt - 0.12) / 0.4), scale=1.1 - 0.1 * ease_out(lt / 0.8), tracking=10)
    lw = (wname / 2 + 40) * ease_out((lt - 0.25) / 0.6)
    tricolore(d, W / 2 - lw, H / 2 + 110, 2 * lw, 6)
    flash = 0.55 * max(0, 1 - lt / 0.25)
    return finish(img, fi, flash)


def scene_fact(seg, lt, fi, gt):
    ch = seg["chapter"]
    p = (seg["index"] % 4) / 4 + lt / seg["dur"] / 4
    zoom = 1.035 - 0.035 * ease_out(lt / 0.6)
    img = bg_crop(theme_bg(ch["key"]), p, zoom).copy()
    d = ImageDraw.Draw(img)
    dur = seg["dur"]
    # ghost year drifting in the background
    ghost, gpad = text_layer(seg["year"], SERIF_B, 620, (255, 255, 255), 0, False, 0)
    paste(img, ghost, W - ghost.width + 120 - 140 * lt / dur, H / 2 - ghost.height / 2 + 40, alpha=0.07)

    x0 = 150
    tag = f"{ch['num']}  ·  {ch['name']}"
    d.rectangle([x0, 228, x0 + 34, 232], fill=OR + (255,))
    place(img, tag, SANS_B, 26, (200, 200, 210), x=x0 + 52, y=216, tracking=6, shadow=False,
          alpha=0.85 * ease_out(lt / 0.3))

    e1 = ease_out(lt / 0.45)
    place(img, seg["year"], SERIF_B, 230, OR, x=x0, y=295 + 50 * (1 - e1), alpha=e1, glow=14)

    e2 = ease_out((lt - 0.12) / 0.45)
    size = 118 if font(SERIF_B, 118).getlength(seg["title"]) < 1600 else 96
    place(img, seg["title"], SERIF_B, size, BLANC, x=x0 + 60 * (1 - e2), y=580, alpha=e2)

    bw = 330 * ease_out((lt - 0.2) / 0.6)
    tricolore(d, x0, 730, bw, 7)

    e3 = ease_out((lt - 0.3) / 0.5)
    for k, line in enumerate(wrap(seg["sub"], SERIF_I, 54, 1550)):
        place(img, line, SERIF_I, 54, (225, 225, 232), x=x0, y=780 + k * 68 + 20 * (1 - e3), alpha=e3)

    # global progress bar
    prog = gt / TOTAL
    tricolore(d, 0, H - 6, W * prog, 6, 200)

    flash = 0.28 * max(0, 1 - lt / 0.18)
    out_fade = 1 - 0.25 * ease_in_out((lt - (dur - 0.12)) / 0.12)
    return finish(img, fi, flash, out_fade)


def scene_flurry(seg, lt, fi, gt):
    step = BEAT / 2
    k = min(int(lt / step), len(seg["picks"]) - 1)
    st = lt - k * step
    year, title, _ = seg["picks"][k]
    img = plain_bg((12, 14, 30), (2, 2, 8)).copy()
    dust(img, gt * 3, color=BLANC, strength=0.5 + 0.5 * lt / seg["dur"])
    d = ImageDraw.Draw(img)
    color = (BLEU_CLAIR, BLANC, ROUGE)[k % 3]
    place(img, year, SERIF_B, 330, color, cx=W / 2, y=H / 2 - 260, scale=1.18 - 0.18 * ease_out(st / 0.2),
          glow=20)
    place(img, title.upper(), SANS_B, 44, (230, 230, 235), cx=W / 2, y=H / 2 + 150, tracking=12,
          alpha=ease_out(st / 0.1))
    # tricolore grows as the years accumulate
    tw = 60 + (W - 400) * (k + 1) / len(seg["picks"])
    tricolore(d, W / 2 - tw / 2, H / 2 + 240, tw, 6)
    end_flash = ease_in_out((lt - (seg["dur"] - 0.5)) / 0.5) * 0.9
    return finish(img, fi, flash=max(0.12 * max(0, 1 - st / 0.08), end_flash))


def scene_outro(seg, lt, fi, gt):
    img = plain_bg((6, 14, 44), (0, 0, 8)).copy()
    dust(img, gt, color=OR, strength=0.9)
    d = ImageDraw.Draw(img)
    words = [("LIBERTÉ", BLEU_CLAIR), ("ÉGALITÉ", BLANC), ("FRATERNITÉ", ROUGE)]
    bar = lt / BAR
    if bar < 3:
        k = int(bar)
        bt = lt - k * BAR
        w, c = words[k]
        a = ease_out(bt / 0.4) * (1 - ease_in_out((bt - BAR + 0.3) / 0.3))
        place(img, w, SERIF_B, 190, c, cx=W / 2, y=H / 2 - 140, alpha=a,
              scale=1.0 + 0.05 * bt / BAR, tracking=24, glow=22)
        flash = 0.3 * max(0, 1 - bt / 0.2) if k == 0 else 0
        return finish(img, fi, flash)
    vt = lt - 3 * BAR
    a = ease_out(vt / 0.6)
    place(img, "VIVE LA FRANCE", SERIF_B, 170, BLANC, cx=W / 2, y=H / 2 - 180, alpha=a,
          scale=1.1 - 0.1 * ease_out(vt / 3) + 0.02 * vt / (5 * BAR), tracking=20, glow=30)
    tw = 900 * ease_out((vt - 0.3) / 1.2)
    tricolore(d, W / 2 - tw / 2, H / 2 + 50, tw, 10)
    place(img, "LIBERTÉ  ·  ÉGALITÉ  ·  FRATERNITÉ", SANS_B, 32, OR, cx=W / 2, y=H / 2 + 110,
          alpha=ease_out((vt - 1.2) / 1.0), tracking=12, shadow=False)
    flash = 0.45 * max(0, 1 - vt / 0.3)
    # "VIVE LA FRANCE" holds, then fades to black over the last bar and a half
    fade = 1 - ease_in_out((lt - (seg["dur"] - 1.6 * BAR)) / (1.6 * BAR))
    return finish(img, fi, flash, fade)


SCENES = dict(line=scene_line, title=scene_title, chapter=scene_chapter, fact=scene_fact,
              flurry=scene_flurry, outro=scene_outro)
STARTS = [s["start"] for s in SEGMENTS]
TAIL = 3.5  # soundtrack reverb tail rendered as black


def render(fi):
    gt = fi / FPS
    if gt >= TOTAL:
        return np.zeros((H, W, 3), np.uint8).tobytes()
    idx = max(i for i, s in enumerate(STARTS) if s <= gt + 1e-6)
    seg = SEGMENTS[idx]
    return SCENES[seg["kind"]](seg, gt - seg["start"], fi, gt).tobytes()


def main():
    out = os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "france_gloire.mp4")
    frames = int((TOTAL + TAIL) * FPS)
    only = os.environ.get("PREVIEW")  # comma-separated seconds -> PNG stills
    if only:
        for s in only.split(","):
            fi = int(float(s) * FPS)
            Image.frombytes("RGB", (W, H), render(fi)).save(os.path.join(ROOT, "build", f"still_{s}.png"))
        return
    ff = __import__("imageio_ffmpeg").get_ffmpeg_exe()
    cmd = [ff, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", os.path.join(ROOT, "build", "soundtrack.wav"),
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        # bounded batches: never let rendered frames pile up faster than x264 encodes them
        batch = 48
        for b0 in range(0, frames, batch):
            for buf in pool.map(render, range(b0, min(frames, b0 + batch)), chunksize=12):
                proc.stdin.write(buf)
            if b0 % 960 == 0:
                print(f"{b0}/{frames}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("wrote", out)


if __name__ == "__main__":
    main()
