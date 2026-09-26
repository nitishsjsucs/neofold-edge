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


def _bgdraw():
    im = canvas()
    return im, ImageDraw.Draw(im)


def eyebrow(d, y, s, alpha=1.0):
    text(d, (W / 2, y), s.upper(), "b", 22, FAINT, "ma", alpha)


# --------------------------------------------------------------------- meta
def meta(t, dur):
    im, d = _bgdraw()
    a, dy = rise(window(t, 0.1, 0.7))
    text(d, (W / 2, 168 + dy), "we thought it'd be funny", "b", 58, INK, "ma", a)
    a2, dy2 = rise(window(t, 0.3, 0.7))
    text(d, (W / 2, 240 + dy2), "to make this video on the Nano too", "b", 58,
         INK, "ma", a2)

    rows = [("voice", "piper neural TTS"), ("music", "synthesised, numpy"),
            ("diagrams", "cairosvg"), ("frames", "pillow"), ("encode", "ffmpeg")]
    y0 = 430
    lw = max(d.textlength(a_, font=font("r", 30)) for a_, _ in rows)
    x0 = W / 2 - (lw + 40 + 420) / 2
    la = window(t, 0.75, 0.4)
    if la > 0:
        d.line([(x0 - 24, y0 - 34), (x0 - 24 + (lw + 40 + 460) * out_cubic(la),
                                     y0 - 34)], fill=fade((48, 56, 66), la), width=2)
    for i, (label, val) in enumerate(rows):
        p = stagger(i, t, each=0.45, gap=0.12, delay=0.9)
        if p <= 0:
            continue
        a_, dy_ = rise(p, 20)
        text(d, (x0 + lw, y0 + i * 58 + dy_), label, "r", 30, MUTED, "ra", a_)
        text(d, (x0 + lw + 40, y0 + i * 58 + dy_), val, "m", 29, INK, "la", a_)
    p = window(t, 1.7, 0.6)
    if p > 0:
        a_, dy_ = rise(p, 18)
        text(d, (W / 2, y0 + len(rows) * 58 + 48 + dy_),
             "nothing left the Nano, including this sentence", "r", 31, GREEN,
             "ma", a_)
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
    eyebrow(d, 92, "to run this on a patient, the genome has to move", window(t, 0.0, 0.5))

    cloud = ["tumour + normal sequencing data", "Data Use Certification",
             "Data Access Committee review", "institutional signing official",
             "Business Associate Agreement", "transfer", "inference",
             "an outside party now holds a genome"]
    edge = ["tumour + normal sequencing data", "inference, on the Nano", "shortlist"]

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
def build(t, dur):
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
        if i:
            pa = window(t, at - 0.25, 0.4)
            if pa > 0:
                yy = y - 58
                d.line([(x + 26, yy - 26), (x + 26, yy)], fill=fade(FAINT, pa), width=3)
                d.polygon([(x + 26, yy + 9), (x + 18, yy - 2), (x + 34, yy - 2)],
                          fill=fade(FAINT, pa))
    p = window(t, 5.6, 0.7)
    if p > 0:
        text(d, (W / 2, 920), "then it explains every one in plain English", "r", 34,
             INK, "ma", p)
    return im


# ---------------------------------------------------------------------- wow
def wow(t, dur):
    """The reveal. Rows arrive anonymous; only later does one of them dim the
    rest of the screen away."""
    im, d = _bgdraw()
    eyebrow(d, 80, "ranked by predicted binding — the strongest candidates",
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
             "an exact match to a healthy human protein", "b", 46,
             RED, "ma", a)
    p = window(t, 5.3, 0.7)
    if p > 0:
        a, dy = rise(p, 16)
        text(d, (W / 2, fy + rh + 136 + dy),
             "ERK2 — the DFG motif is in almost every human kinase", "r", 31,
             MUTED, "ma", a)
        text(d, (W / 2, fy + rh + 182 + dy),
             "a therapy aimed at it would attack the patient", "r", 31, MUTED, "ma", a)
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
    im, d = _bgdraw()
    a, dy = rise(window(t, 0.05, 0.7))
    text(d, (W / 2, 390 + dy), "A cancer research lab", "b", 76, INK, "ma", a)
    a2, dy2 = rise(window(t, 0.25, 0.7))
    text(d, (W / 2, 480 + dy2), "that fits on a desk.", "b", 76, INK, "ma", a2)
    a3, dy3 = rise(window(t, 0.6, 0.7))
    text(d, (W / 2, 590 + dy3), "And never phones home.", "b", 60, TEAL, "ma", a3)
    p = window(t, 1.2, 0.6)
    if p > 0:
        text(d, (W / 2, 730), "github.com/nitishsjsucs/neofold-edge", "m", 32,
             ACCENT, "ma", p)
    p = window(t, 1.6, 0.6)
    if p > 0:
        text(d, (W / 2, 820), "HP ZGX Nano · NVIDIA GB10 · fully offline", "r", 27,
             FAINT, "ma", p)
        text(d, (W / 2, 900),
             "Research prioritisation only. Every value is a prediction, not a measurement.",
             "r", 24, AMBER, "ma", p)
    return im


SCENES = {"meta": meta, "hook": hook, "question": question, "problem": problem,
          "build": build, "wow": wow, "nano": nano, "proof": proof, "close": close}


# How long each scene's authored animation runs. make_video stretches the
# timeline toward the narration length (capped), then holds the remainder.
NOMINAL = {"meta": 2.6, "hook": 7.4, "question": 6.0, "problem": 6.0,
           "build": 6.5, "wow": 7.3, "nano": 5.6, "proof": 4.9, "close": 2.3}
