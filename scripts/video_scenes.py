"""The scenes. Each is render(t, dur) -> PIL.Image, t in seconds.

Data is DRAWN rather than screenshotted. A downscaled 1600px screenshot of a
dashboard is illegible at 1080p and cannot be animated; redrawing the same real
numbers gives type that holds up full-screen and elements that can arrive one
at a time. Every figure here comes from benchmarks/ or a real triage run.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from video_anim import (ACCENT, AMBER, BG, FAINT, GREEN, INK, MUTED, PANEL,
                        PURPLE, RED, TEAL, H, W, bar, canvas, clamp, counter,
                        dot_grid, fade, font, in_out_cubic, mix, out_back,
                        out_cubic, out_quint, rise, rrect, spotlight, stagger,
                        text, window, wrap)

# The real top of a real run: data/demo/tumor_variants_large.vcf on HLA-C*08:02.
ROWS = [
    ("ITDFGRAKL",  "EGFR L858R",   "36",  "34",    "0.9",  "TCR-facing", 0),
    ("GADGVGKSAL", "KRAS G12D",    "39",  "877",   "17.9", "TCR-facing", 0),
    ("ITDKHELF",   "PIK3CA I45D",  "48",  "11616", "53.6", "TCR-facing", 0),
    ("GADGVGKSA",  "KRAS G12D",    "74",  "3656",  "23.5", "TCR-facing", 0),
    ("AAPGPAAPA",  "TP53 T81G",    "90",  "146",   "1.6",  "TCR-facing", 0),
    ("ITDFGRAKLL", "EGFR L858R",   "95",  "106",   "1.1",  "TCR-facing", 0),
    ("FVPEYDPTI",  "KRAS D30P",    "108", "28",    "0.3",  "TCR-facing", 0),
    ("AAGVGKSAL",  "KRAS G12A",    "117", "1355",  "8.2",  "anchor",     0),
    ("VAPQTSEFI",  "EGFR S1204T",  "175", "167",   "0.9",  "TCR-facing", 0),
    ("ICDFGLARV",  "KIT D816V",    "178", "19899", "16.1", "anchor",     1),
]
FLAG = next(i for i, r in enumerate(ROWS) if r[6])


_SHOT: dict = {}


def real_ui():
    """The actual dashboard, as captured. The drawn scenes are far more legible
    at 1080p, but a demo that never shows the real interface is a presentation,
    not a demo -- and judging guidance is explicit that presentations lose."""
    if "dash" not in _SHOT:
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "docs" / "img" / "dashboard.png"
        im = Image.open(p).convert("RGB")
        sc = min((W - 120) / im.width, (H - 200) / im.height)
        _SHOT["dash"] = im.resize((int(im.width * sc), int(im.height * sc)),
                                  Image.LANCZOS)
    return _SHOT["dash"]


def _bgdraw():
    im = canvas()
    return im, ImageDraw.Draw(im)


def eyebrow(d, y, s, alpha=1.0):
    text(d, (W / 2, y), s.upper(), "b", 22, FAINT, "ma", alpha)


# --------------------------------------------------------------------- meta
def meta(t, dur):
    """Pre-roll joke. Kept short and sparse: it runs before the one-liner, so
    every character it spends is a character the product does not get."""
    im, d = _bgdraw()
    a, dy = rise(window(t, 0.1, 0.6))
    text(d, (W / 2, 400 + dy), "we made this video", "b", 66, INK, "ma", a)
    a2, dy2 = rise(window(t, 0.3, 0.6))
    text(d, (W / 2, 486 + dy2), "on the Nano too", "b", 66, INK, "ma", a2)
    p = window(t, 1.0, 0.7)
    if p > 0:
        aa, ddy = rise(p, 18)
        text(d, (W / 2, 610 + ddy), "voice · music · every frame", "m", 34,
             MUTED, "ma", aa)
    p = window(t, 1.7, 0.6)
    if p > 0:
        text(d, (W / 2, 690), "nothing left the Nano", "r", 32, GREEN, "ma", p)
    return im



# ------------------------------------------------- real screen-capture shots
_CAP: dict = {}


def cap(name: str):
    """Load a captured panel once. These are 2x device-scale grabs of the app
    actually running, so a crop can be blown up to full frame and still hold."""
    if name not in _CAP:
        from pathlib import Path
        p = Path(__file__).resolve().parent.parent / "docs" / "img" / f"{name}.png"
        _CAP[name] = Image.open(p).convert("RGB")
    return _CAP[name]


def screen(name, t_, a, b, caption=None, sub=None, ease=out_cubic,
           hl=None, hl_at=0.6, label=None):
    """A capture pushed slowly from crop `a` to crop `b`, both given as
    (x0,y0,x1,y1) fractions. Motion that travels toward the thing being
    explained is the cue that measures well; a static arrow is not."""
    src = cap(name)
    e = ease(clamp(t_))
    box = [a[i] + (b[i] - a[i]) * e for i in range(4)]
    px = (box[0] * src.width, box[1] * src.height,
          box[2] * src.width, box[3] * src.height)
    crop = src.crop(tuple(int(v) for v in px))

    top = 158 if caption else 56          # headroom so the caption never overlaps
    bw, bh = W - 140, H - top - 84
    sc = min(bw / crop.width, bh / crop.height)
    crop = crop.resize((max(1, int(crop.width * sc)), max(1, int(crop.height * sc))),
                       Image.LANCZOS)
    im = canvas()
    ox, oy = (W - crop.width) // 2, top + (bh - crop.height) // 2
    im.paste(crop, (ox, oy))
    d = ImageDraw.Draw(im)
    rrect(d, [ox - 2, oy - 2, ox + crop.width + 2, oy + crop.height + 2], 6,
          outline=(44, 52, 62), width=2)

    if label:
        text(d, (W / 2, 46), label.upper(), "b", 22, FAINT, "ma", clamp(t_ * 4))
    if caption:
        ca = clamp(t_ * 3)
        text(d, (W / 2, 96), caption, "b", 42, INK, "ma", ca)
    if sub:
        text(d, (W / 2, H - 40), sub, "r", 28, MUTED, "ma", window(t_, 0.35, 0.25))
    if hl:
        p = clamp((t_ - hl_at) / 0.18)
        if p > 0:
            hx = [ox + hl[0] * crop.width, oy + hl[1] * crop.height,
                  ox + hl[2] * crop.width, oy + hl[3] * crop.height]
            im = spotlight(im, hx, out_cubic(p), dim=0.8, ring=RED, ring_w=4)
    return im


# --------------------------------------------------------------- dashboard
def dashboard(t, dur):
    """The real interface. A demo that never shows the product is a
    presentation, and judging guidance is explicit that presentations lose."""
    p = t / max(0.5, dur)
    return screen("vid-dashboard", p,
                  (0.00, 0.00, 1.00, 0.62), (0.01, 0.40, 0.56, 0.90),
                  label="running on the Nano",
                  caption="the actual interface",
                  sub="every row scored, ranked, and explained · no mock-ups")


# --------------------------------------------------------------- structure
def structure(t, dur):
    p = t / max(0.5, dur)
    # The headless captures leave the WebGL viewport black; this earlier grab
    # has the cartoon rendered, so the push travels from the molecule down to
    # the number that makes it checkable.
    return screen("structure", p,
                  (0.02, 0.20, 0.98, 0.50), (0.02, 0.52, 0.98, 0.76),
                  label="predicted peptide–HLA complex",
                  caption="2.5 Å predicted · 2.7 Å in the crystal",
                  sub="the contact was chosen before the prediction was run")


# ---------------------------------------------------------------- evidence
def evidence(t, dur):
    p = t / max(0.5, dur)
    return screen("vid-roc", p,
                  (0.00, 0.00, 1.00, 0.62), (0.02, 0.06, 0.98, 0.46),
                  label="validated against 2,555 lab-tested peptides",
                  caption="AUC 0.777 and 0.759",
                  sub="and the metric that scored below random is still on screen")


# ----------------------------------------------------------------- holdout
def holdout(t, dur):
    p = t / max(0.5, dur)
    return screen("vid-holdout", p,
                  (0.00, 0.00, 1.00, 0.72), (0.02, 0.10, 0.98, 0.58),
                  label="nine crystals the model had never seen",
                  caption="confidence does not predict error",
                  sub="0.011 of ipTM against a full ångström of real error · r = −0.23")


# ----------------------------------------------------------------- summary
def summary(t, dur):
    p = t / max(0.5, dur)
    return screen("vid-summary", p,
                  (0.00, 0.22, 1.00, 0.78), (0.01, 0.28, 0.99, 0.62),
                  label="written on-device by qwen3:8b",
                  caption="it only gets the facts, and every number is checked",
                  sub="invent one and the summary is rejected")


# --------------------------------------------------------------------- what
def what(t, dur):
    """The one-liner. A viewer who stops at 45 seconds should still be able to
    say what this is; leading with Rosie alone leaves them having watched a
    dog-cancer documentary."""
    im, d = _bgdraw()
    a, dy = rise(window(t, 0.05, 0.6))
    text(d, (W / 2, 300 + dy), "NeoFold Edge", "b", 104, INK, "ma", a)
    for i, s in enumerate(["takes a tumour's DNA and picks the targets",
                           "a cancer vaccine should aim at"]):
        p = stagger(i, t, each=0.55, gap=0.18, delay=0.55)
        if p <= 0:
            continue
        aa, ddy = rise(p, 22)
        text(d, (W / 2, 450 + i * 60 + ddy), s, "r", 46, MUTED, "ma", aa)
    p = window(t, 1.5, 0.7)
    if p > 0:
        aa, ddy = rise(p, 18)
        y = 640 + ddy
        for i, (lab, col) in enumerate([("one small computer", ACCENT),
                                        ("completely offline", TEAL)]):
            x = W / 2 + (-1 if i == 0 else 1) * 230
            rrect(d, [x - 210, y, x + 210, y + 72], 12, fill=fade(PANEL, aa),
                  outline=fade(col, aa), width=2)
            text(d, (x, y + 36), lab, "b", 34, col, "mm", aa)
    return im


# --------------------------------------------------------------------- hook
def hook(t, dur):
    im, d = _bgdraw()
    lines = [("Rosie, five years old.", 40, MUTED),
             ("Terminal cancer.", 40, MUTED),
             ("Her owner had never studied biology.", 52, INK)]
    y = 300
    for i, (s, sz, col) in enumerate(lines):
        p = stagger(i, t, each=0.55, gap=0.55, delay=0.2)
        if p <= 0:
            continue
        a, dy = rise(p, 26)
        text(d, (W / 2, y + dy), s, "b" if col is INK else "r", sz, col, "ma", a)
        y += sz + 42

    p = window(t, 2.6, 1.0)
    if p > 0:
        a, dy = rise(p, 24)
        for j, s in enumerate(["He had her tumour sequenced, used AI to pick",
                               "the targets, and designed her a vaccine."]):
            text(d, (W / 2, 560 + j * 46 + dy), s, "r", 34, MUTED, "ma", a)

    # The result, counting up -- the number is the point, so it lands last.
    p = window(t, 4.6, 1.8)
    if p > 0:
        val = counter(75, p, comma=False)
        sc = 1.0 + 0.06 * (1 - out_back(clamp(p * 1.6)))
        text(d, (W / 2, 760), f"{val}%", "b", int(150 * sc), GREEN, "mm",
             clamp(p * 3))
        text(d, (W / 2, 862), "her largest tumour shrank", "r", 34, INK, "ma",
             window(t, 5.2, 0.6))
    p = window(t, 6.4, 0.8)
    if p > 0:
        text(d, (W / 2, 930), "one dog · not a controlled study · given with a checkpoint inhibitor",
             "r", 24, FAINT, "ma", p)
    return im


# ----------------------------------------------------------------- question
def question(t, dur):
    """The asymmetry, built in front of you: eight steps against one."""
    im, d = _bgdraw()
    eyebrow(d, 92, "the genome has to move", window(t, 0.0, 0.5))

    cloud = ["the genome", "Data Use Certification", "Access Committee review",
             "signing official", "vendor agreement", "transfer", "inference",
             "someone else holds it"]
    edge = ["the genome", "inference, on the Nano", "shortlist"]

    cw, bh, gap = 700, 62, 14
    lx, rx = 130, W - 130 - cw
    text(d, (lx + cw / 2, 175), "CLOUD", "b", 30, RED, "ma", window(t, 0.2, 0.4))
    text(d, (rx + cw / 2, 175), "NEOFOLD EDGE", "b", 30, TEAL, "ma", window(t, 0.2, 0.4))

    for i, s in enumerate(cloud):
        p = stagger(i, t, each=0.32, gap=0.30, delay=0.6)
        if p <= 0:
            continue
        a, dy = rise(p, 16)
        y = 225 + i * (bh + gap) + dy
        hot = 1 <= i <= 4
        rrect(d, [lx, y, lx + cw, y + bh], 9,
              fill=fade((58, 26, 30) if hot else PANEL, a),
              outline=fade(RED if hot else (48, 56, 66), a), width=2)
        text(d, (lx + cw / 2, y + bh / 2), s, "r", 27,
             INK if hot else MUTED, "mm", a)

    for i, s in enumerate(edge):
        p = stagger(i, t, each=0.3, gap=0.12, delay=3.4)
        if p <= 0:
            continue
        a, dy = rise(p, 16)
        y = 225 + i * (bh + gap) + dy
        rrect(d, [rx, y, rx + cw, y + bh], 9, fill=fade(PANEL, a),
              outline=fade(TEAL if i == 1 else (48, 56, 66), a), width=2)
        text(d, (rx + cw / 2, y + bh / 2), s, "r", 27,
             INK if i == 1 else MUTED, "mm", a)

    p = window(t, 5.0, 0.8)
    if p > 0:
        a, _ = rise(p, 0)
        text(d, (lx + cw / 2, 225 + 8 * (bh + gap) + 42), "weeks", "b", 62, RED, "ma", a)
        text(d, (rx + cw / 2, 225 + 3 * (bh + gap) + 42), "minutes", "b", 62, TEAL, "ma", a)
    return im


# ------------------------------------------------------------------ problem
def problem(t, dur):
    """1,890 candidates as 1,890 dots, dimming to the ~51 that are real."""
    N, COLS, CELL, RAD = 1890, 70, 21, 7
    rng = np.random.default_rng(11)
    real = set(rng.choice(N, 51, replace=False).tolist())

    dim = window(t, 2.2, 2.0)
    base = np.array(mix(BG, MUTED, 0.55), np.uint8)
    lit = np.array(GREEN, np.uint8)
    off = np.array(mix(BG, MUTED, 0.55 * (1 - 0.88 * out_cubic(dim))), np.uint8)
    cols = np.zeros((N, 3), np.uint8)
    appear = out_cubic(window(t, 0.0, 1.2))
    for i in range(N):
        if i / N > appear:
            cols[i] = np.array(BG, np.uint8)
        elif i in real:
            cols[i] = mix(tuple(base.tolist()), tuple(lit.tolist()), out_cubic(dim))
        else:
            cols[i] = off
    gw = COLS * CELL
    im = dot_grid(N, COLS, CELL, RAD, cols, ((W - gw) / 2, 200))
    d = ImageDraw.Draw(im)

    text(d, (W / 2, 128), "one tumour · 1,890 candidate fragments", "r", 34,
         MUTED, "ma", window(t, 0.1, 0.5))
    p = window(t, 3.4, 0.8)
    if p > 0:
        a, dy = rise(p, 20)
        text(d, (W / 2, 800 + dy), "about fifty are real", "b", 60, GREEN, "ma", a)
    p = window(t, 4.4, 1.4)
    if p > 0:
        text(d, (W / 2, 892), f"{counter(6, p, comma=False)}% of the best candidates "
             f"ever lab-tested actually worked", "r", 32, RED, "ma", clamp(p * 3))
        text(d, (W / 2, 950), "608 nominated by 25 expert pipelines · 37 worked · TESLA, Cell 2020",
             "r", 23, FAINT, "ma", window(t, 5.2, 0.6))
    return im


# -------------------------------------------------------------------- build
def funnel(t, dur):
    """The funnel, actually funnelling."""
    im, d = _bgdraw()
    eyebrow(d, 96, "NeoFold Edge · entirely offline on one HP ZGX Nano",
            window(t, 0.0, 0.5))
    steps = [(1890, "candidate fragments", "", MUTED, 0.0),
             (1890, "screened against the patient's HLA", "9 seconds · CPU", ACCENT, 0.9),
             (22,   "survive the screen", "", TEAL, 2.4),
             (5,    "folded in 3D and stress-tested", "64 s each · GPU", PURPLE, 3.9)]
    x, w, bh = 300, W - 600, 74
    for i, (n, label, note, col, at) in enumerate(steps):
        p = window(t, at, 1.1)
        if p <= 0:
            continue
        y = 235 + i * 150
        frac = (n / 1890) ** 0.42 * out_cubic(p)
        bar(d, x, y, w, bh, frac, fade(col, min(1, p * 2)))
        text(d, (x, y - 34), counter(n, p), "mb", 46, fade(col, min(1, p * 2)), "la")
        text(d, (x + w, y - 30), label, "r", 30, MUTED, "ra", min(1, p * 2))
        if note:
            text(d, (x, y + bh + 16), note, "m", 25, FAINT, "la", window(t, at + 0.5, 0.5))
    return im


# ---------------------------------------------------------------------- wow
def wow(t, dur):
    """The reveal. Rows arrive anonymous; only later does one of them dim the
    rest of the screen away."""
    im, d = _bgdraw()
    eyebrow(d, 80, "real output from a real run · redrawn to be legible",
            window(t, 0.0, 0.4))
    x0, y0, rw, rh = 250, 108, W - 500, 58
    cols = [0, 330, 620, 810, 980, 1130]

    hp = window(t, 0.3, 0.4)
    for j, hd in enumerate(["peptide", "variant", "nM", "WT nM", "DAI", "site"]):
        text(d, (x0 + cols[j], y0 + 4), hd, "r", 26, FAINT, "la", hp)

    for i, (pep, var, nm, wt, dai, site, flag) in enumerate(ROWS):
        p = stagger(i, t, each=0.4, gap=0.11, delay=0.6)
        if p <= 0:
            continue
        a, dx = rise(p, 0)
        y = y0 + 48 + i * rh
        if i % 2 == 0:
            rrect(d, [x0 - 20, y, x0 + rw + 20, y + rh - 6], 8, fill=fade(PANEL, a * .7))
        text(d, (x0 + cols[0], y + rh / 2 - 3), pep, "mb", 29, INK, "lm", a)
        text(d, (x0 + cols[1], y + rh / 2 - 3), var, "r", 27, MUTED, "lm", a)
        for j, v in enumerate([nm, wt, dai]):
            text(d, (x0 + cols[2 + j] + 120, y + rh / 2 - 3), v, "m", 27, MUTED, "rm", a)
        text(d, (x0 + cols[5], y + rh / 2 - 3), site, "r", 24,
             AMBER if site == "anchor" else MUTED, "lm", a)

    fy = y0 + 48 + FLAG * rh
    sp = window(t, 3.1, 0.9)
    if sp > 0:
        im = spotlight(im, [x0 - 40, fy - 6, x0 + rw + 40, fy + rh - 2],
                       out_cubic(sp), dim=0.86, ring=RED, ring_w=4)
        d = ImageDraw.Draw(im)
    p = window(t, 4.2, 0.7)
    if p > 0:
        a, dy = rise(p, 20)
        text(d, (W / 2, fy + rh + 68 + dy),
             "= ERK2, a healthy human protein", "b", 50, RED, "ma", a)
    p = window(t, 5.3, 0.7)
    if p > 0:
        a, dy = rise(p, 16)
        text(d, (W / 2, fy + rh + 136 + dy),
             "the DFG motif is in almost every human kinase", "r", 31,
             MUTED, "ma", a)
    p = window(t, 6.5, 0.6)
    if p > 0:
        a, dy = rise(p, 14)
        text(d, (W / 2, fy + rh + 252 + dy), "our filter caught it", "b", 40,
             GREEN, "ma", a)
    return im


# --------------------------------------------------------------------- nano
def nano(t, dur):
    im, d = _bgdraw()
    eyebrow(d, 110, "four models resident at the same time", window(t, 0.0, 0.4))
    chips = [("MHCflurry", "binding screen", TEAL),
             ("Boltz-2", "structure prediction", PURPLE),
             ("qwen3:8b", "plain-English summary", ACCENT),
             ("OpenMM", "molecular dynamics", AMBER)]
    cw, ch, g = 380, 150, 34
    total = len(chips) * cw + (len(chips) - 1) * g
    sx = (W - total) / 2
    for i, (name, role, col) in enumerate(chips):
        p = stagger(i, t, each=0.5, gap=0.22, delay=0.35)
        if p <= 0:
            continue
        a, dy = rise(p, 26)
        x = sx + i * (cw + g)
        rrect(d, [x, 215 + dy, x + cw, 215 + ch + dy], 14, fill=fade(PANEL, a),
              outline=fade(col, a), width=2)
        text(d, (x + cw / 2, 268 + dy), name, "b", 38, INK, "mm", a)
        text(d, (x + cw / 2, 318 + dy), role, "r", 26, MUTED, "mm", a)
    p = window(t, 1.9, 0.5)
    if p > 0:
        text(d, (W / 2, 420), "three neural networks and a physics engine", "r", 30,
             FAINT, "ma", p)

    p = window(t, 2.6, 1.5)
    if p > 0:
        text(d, (300, 520), "unified memory", "r", 30, MUTED, "la", min(1, p * 3))
        bar(d, 300, 566, W - 600, 44, 0.9 * out_cubic(p), fade(ACCENT, 1))
        text(d, (W - 300, 520), f"{counter(128, p, comma=False)} GB", "mb", 34,
             INK, "ra", min(1, p * 3))
        text(d, (300, 628), "one coherent pool — every model resident at once",
             "r", 26, FAINT, "la", window(t, 3.4, 0.5))
    p = window(t, 4.3, 1.2)
    if p > 0:
        text(d, (W / 2, 790), f"{counter(38, p, comma=False)} W", "b", 132, GREEN,
             "mm", min(1, p * 3))
        text(d, (W / 2, 890), "peak draw, measured · about what a laptop uses",
             "r", 30, MUTED, "ma", window(t, 5.0, 0.5))
    return im


# -------------------------------------------------------------------- proof
def proof(t, dur):
    im, d = _bgdraw()
    eyebrow(d, 120, "is it actually right?", window(t, 0.0, 0.4))
    pairs = [("2.5 Å", "we predict this atomic contact", ACCENT, 0.4),
             ("2.7 Å", "the crystal structure measures", GREEN, 1.3)]
    for i, (val, label, col, at) in enumerate(pairs):
        p = window(t, at, 0.8)
        if p <= 0:
            continue
        a, dy = rise(p, 28)
        x = W / 2 + (-1 if i == 0 else 1) * 330
        text(d, (x, 330 + dy), val, "b", 128, col, "mm", a)
        text(d, (x, 430 + dy), label, "r", 29, MUTED, "ma", a)
    p = window(t, 2.4, 0.6)
    if p > 0:
        text(d, (W / 2, 330), "vs", "r", 44, FAINT, "mm", p)
        text(d, (W / 2, 520), "a prediction we made before looking", "r", 30,
             FAINT, "ma", p)

    p = window(t, 3.3, 1.4)
    if p > 0:
        text(d, (300, 660), "one tumour, end to end", "r", 32, MUTED, "la", min(1, p * 3))
        bar(d, 300, 712, W - 600, 46, out_cubic(p), fade(PURPLE, 1))
        text(d, (W - 300, 660), f"{counter(13, p, comma=False)} minutes", "mb", 36,
             INK, "ra", min(1, p * 3))
        text(d, (300, 782), "on one Nano · nothing leaves the room", "r", 27,
             FAINT, "la", window(t, 4.2, 0.5))
    return im


# -------------------------------------------------------------------- close
def close(t, dur):
    """The last frame a judge sees. Measured at 8x over the readable-character
    budget before this cut, so it is now the tagline, the URL, and nothing."""
    im, d = _bgdraw()
    a, dy = rise(window(t, 0.05, 0.6))
    text(d, (W / 2, 420 + dy), "A cancer research lab", "b", 78, INK, "ma", a)
    a2, dy2 = rise(window(t, 0.25, 0.6))
    text(d, (W / 2, 512 + dy2), "that fits on a desk.", "b", 78, INK, "ma", a2)
    p = window(t, 0.9, 0.6)
    if p > 0:
        aa, ddy = rise(p, 18)
        text(d, (W / 2, 640 + ddy), "github.com/nitishsjsucs/neofold-edge", "m",
             34, ACCENT, "ma", aa)
    p = window(t, 1.4, 0.5)
    if p > 0:
        text(d, (W / 2, 730), "research prioritisation only", "r", 26, AMBER,
             "ma", p)
    return im


SCENES = {"meta": meta, "what": what, "hook": hook,
          "dashboard": dashboard, "structure": structure,
          "evidence": evidence, "holdout": holdout, "summary": summary, "question": question, "problem": problem,
          "funnel": funnel, "wow": wow, "nano": nano, "proof": proof, "close": close}


# How long each scene's authored animation runs. make_video stretches the
# timeline toward the narration length (capped), then holds the remainder.
NOMINAL = {"meta": 2.4, "what": 2.4, "hook": 7.4, "question": 6.0, "problem": 6.0,
           "funnel": 6.6, "dashboard": 8.0, "structure": 8.0,
           "evidence": 8.0, "holdout": 8.0, "summary": 8.0, "wow": 7.3, "nano": 5.6, "proof": 4.9, "close": 2.3}
