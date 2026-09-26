"""Animation toolkit for the demo video: easing, staggering, and drawing.

Every frame is composed here rather than driven by ffmpeg filters, because the
shots need motion filters cannot express -- a funnel whose bars shrink while
their numbers count, a grid of 1,890 dots that dims down to the 51 that matter,
a table row that stays anonymous until the surround dims around it.

Conventions:
  * a scene renders as f(t, dur, ctx) -> PIL.Image, t in seconds
  * entrances ease OUT (fast start, settle) -- motion arriving should decelerate
  * exits ease IN; anything travelling both ways eases in-out
  * nothing animates for its own sake; every move carries a fact
"""
from __future__ import annotations

import math
import pathlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
BG = (11, 15, 20)
PANEL = (22, 27, 34)
INK = (237, 242, 247)
MUTED = (141, 153, 166)
FAINT = (98, 108, 120)
ACCENT = (110, 155, 242)
TEAL = (45, 190, 140)
PURPLE = (163, 113, 247)
AMBER = (232, 181, 63)
RED = (242, 95, 92)
GREEN = (95, 208, 130)

FD = pathlib.Path("/usr/share/fonts/truetype/dejavu")
_FC: dict = {}


def font(kind: str, size: int):
    key = (kind, size)
    if key not in _FC:
        f = {"b": "DejaVuSans-Bold.ttf", "r": "DejaVuSans.ttf",
             "m": "DejaVuSansMono.ttf", "mb": "DejaVuSansMono-Bold.ttf"}[kind]
        _FC[key] = ImageFont.truetype(str(FD / f), size)
    return _FC[key]


# ------------------------------------------------------------------- easing
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def out_cubic(t):     return 1 - (1 - clamp(t)) ** 3
def out_quint(t):     return 1 - (1 - clamp(t)) ** 5
def in_out_cubic(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
def out_back(t, s=1.70158):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def stagger(i: int, t: float, each: float = 0.5, gap: float = 0.08,
            delay: float = 0.0) -> float:
    """Progress of item i, given a per-item duration and inter-item gap."""
    return clamp((t - delay - i * gap) / each)


def window(t: float, start: float, dur: float) -> float:
    """Progress through a sub-window of the scene."""
    return clamp((t - start) / max(1e-6, dur))


# ------------------------------------------------------------------ drawing
def canvas(colour=BG) -> Image.Image:
    return Image.new("RGB", (W, H), colour)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def fade(colour, alpha, bg=BG):
    """Composite a colour onto the background at `alpha` -- cheaper and
    sharper than an RGBA overlay for text that only fades."""
    return mix(bg, colour, alpha)


def text(d, xy, s, kind="r", size=32, colour=INK, anchor="la", alpha=1.0,
         bg=BG, spacing=None):
    if alpha <= 0.01:
        return
    d.text(xy, s, font=font(kind, size), fill=fade(colour, alpha, bg),
           anchor=anchor, **({"spacing": spacing} if spacing else {}))


def rise(t: float, dist: float = 34.0) -> tuple[float, float]:
    """Standard entrance: fade in while sliding up. Returns (alpha, dy)."""
    e = out_cubic(t)
    return e, (1 - e) * dist


def rrect(d, box, r, fill=None, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def wrap(d, s, f, max_w):
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) <= max_w:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines


def counter(value: float, t: float, decimals: int = 0, comma: bool = True,
            ease=out_quint) -> str:
    """A number counting up. Eased so it decelerates into its final value
    rather than stopping dead, which reads as a glitch."""
    v = value * ease(t)
    if decimals:
        return f"{v:,.{decimals}f}" if comma else f"{v:.{decimals}f}"
    return f"{round(v):,}" if comma else f"{round(v)}"


def bar(d, x, y, w, h, frac, colour, track=(38, 45, 54), r=None):
    r = h // 2 if r is None else r
    rrect(d, [x, y, x + w, y + h], r, fill=track)
    fw = max(0, int(w * clamp(frac)))
    if fw > 2 * r:
        rrect(d, [x, y, x + fw, y + h], r, fill=colour)


def spotlight(im: Image.Image, box, alpha: float, dim=0.80, ring=None,
              ring_w=4, pad=0):
    """Dim everything outside `box`. The single most useful gesture in the
    film: it turns a wall of data into one row without moving the camera."""
    if alpha <= 0.01:
        return im
    x0, y0, x1, y1 = [int(v) for v in box]
    x0 -= pad; y0 -= pad; x1 += pad; y1 += pad
    arr = np.asarray(im).astype(np.float32)
    mask = np.full((H, W, 1), dim * alpha, np.float32)
    mask[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] = 0.0
    out = arr * (1 - mask) + np.array(BG, np.float32) * mask
    im = Image.fromarray(out.astype(np.uint8))
    if ring:
        d = ImageDraw.Draw(im)
        rrect(d, [x0, y0, x1, y1], 10, outline=fade(ring, alpha), width=ring_w)
    return im


def dot_grid(n: int, cols: int, cell: int, radius: int,
             colours: np.ndarray, origin) -> Image.Image:
    """`n` dots drawn with numpy rather than per-dot ImageDraw calls -- at
    1,890 dots a frame the draw loop dominates the render otherwise."""
    rows = math.ceil(n / cols)
    gw, gh = cols * cell, rows * cell
    arr = np.zeros((gh, gw, 3), np.uint8)
    arr[:, :] = BG
    yy, xx = np.mgrid[0:cell, 0:cell]
    c = cell / 2
    disc = ((xx - c) ** 2 + (yy - c) ** 2) <= radius ** 2
    for i in range(n):
        r_, c_ = divmod(i, cols)
        y0, x0 = r_ * cell, c_ * cell
        tile = arr[y0:y0 + cell, x0:x0 + cell]
        tile[disc] = colours[i]
    im = canvas()
    im.paste(Image.fromarray(arr), (int(origin[0]), int(origin[1])))
    return im
