"""The scenes, rebuilt on the archetypes in research/research-video-visual.md.

Two rules run through all of it:

  * EVERYTHING LEFT-ALIGNS TO COL(0) = 192. There is no centred stack anywhere.
    Centred-everything on a flat ground is the single strongest "amateur deck"
    signal, and it was on every slide of the previous cut.

  * ONE CHROMATIC HUE PER FRAME. Semantic colours carry meaning; they never
    decorate. The old funnel put four hues on one slide.

Product scenes are annotated captures (video_plates): a static, never-resampled
screenshot with a ring, a numbered badge and a short caption that land on the
word the narration is saying.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

import video_anim as A
import video_plates as P
from video_theme import (AC, AC_TEXT, CARD, COL, DANGER, HAIRLINE, H, INFO,
                         LINE_CARD, LINE_PAGE, MARK, PAGE, PANEL, RAISED,
                         R_CTRL, SUCCESS, TX_1, TX_2, TX_3, TX_4, W, WARNING,
                         Y_EYEBROW, Y_HEADLINE, Y_RULE)


# ============================================================== archetypes
def a1_title(lines, eyebrow=None, meta=None, t=0.0, accent_idx=None):
    """Bottom-left anchored. The top 60% stays empty -- that emptiness is the
    composition, and it is what most changes how a title card reads."""
    im = A.canvas(); d = ImageDraw.Draw(im)
    # The archetype is specced for two display lines; a third pushes the block
    # up into the eyebrow, so the eyebrow follows the block rather than sitting
    # at a fixed y and colliding.
    base = 892 - (len(lines) - 1) * 126
    if eyebrow:
        a = A.out_cubic(A.window(t, 0.0, 0.5))
        A.role(d, (COL(0), base - 94), eyebrow, "eyebrow", alpha=a)
        A.kicker(d, y=base - 62, alpha=A.window(t, 0.15, 0.4))
    for i, ln in enumerate(lines):
        p = A.stagger(i, t, each=0.55, gap=0.14, delay=0.25)
        if p <= 0:
            continue
        a = A.out_cubic(p)
        A.role(d, (COL(0), base + i * 126 + (1 - a) * 18), ln, "display", alpha=a)
    if meta:
        p = A.window(t, 0.9, 0.5)
        if p > 0:
            x = COL(0)
            for j, seg in enumerate(meta):
                if j:
                    x += A.role(d, (x, 956), "  ·  ", "mono_label", colour=TX_4,
                                alpha=p)
                col = AC_TEXT if j == accent_idx else TX_3
                x += A.role(d, (x, 956), seg, "mono_label", colour=col, alpha=p)
    return im


def a2_head(d, eyebrow, headline, t, lead=None, delay=0.0):
    """Shared header: eyebrow, kicker rule, headline as a full sentence."""
    A.role(d, (COL(0), Y_EYEBROW), eyebrow, "eyebrow",
           alpha=A.window(t, delay, 0.45))
    A.kicker(d, alpha=A.window(t, delay + 0.12, 0.4))
    lines = A.wrap_role(headline, "headline", COL(12) - COL(0))[:3]
    last = Y_HEADLINE
    for i, ln in enumerate(lines):
        p = A.stagger(i, t, each=0.5, gap=0.1, delay=delay + 0.2)
        if p <= 0:
            continue
        a = A.out_cubic(p)
        last = Y_HEADLINE + i * 80
        A.role(d, (COL(0), last + (1 - a) * 16), ln, "headline", alpha=a)
    if lead:
        p = A.window(t, delay + 0.7, 0.5)
        if p > 0:
            for j, ln in enumerate(A.wrap_role(lead, "lead", COL(11) - COL(0))[:2]):
                A.role(d, (COL(0), last + 112 + j * 58), ln, "lead",
                       alpha=A.out_cubic(p))
    return last


def a3_stat(d, value, unit, label, caption, t, colour=TX_1, source=None,
            delay=0.0, decimals=0, baseline=560):
    """Label above, value left-aligned, unit on the same baseline. Never centre
    a number that has a caption."""
    A.role(d, (COL(0), Y_EYEBROW), label, "eyebrow", alpha=A.window(t, delay, 0.4))
    A.kicker(d, alpha=A.window(t, delay + 0.1, 0.4))
    p = A.window(t, delay + 0.25, 1.1)
    if p <= 0:
        return
    s = A.counter(value, p, decimals=decimals, comma=False)
    w = A.role(d, (COL(0), baseline), s, "stat", colour=colour,
               alpha=min(1.0, p * 4))
    if unit:
        A.role(d, (COL(0) + w + 24, baseline), unit, "stat_unit",
               alpha=min(1.0, p * 4))
    if caption:
        q = A.window(t, delay + 0.8, 0.5)
        if q > 0:
            for j, ln in enumerate(A.wrap_role(caption, "lead", COL(12) - COL(0))[:2]):
                A.role(d, (COL(0), 660 + j * 58), ln, "lead", alpha=A.out_cubic(q))
    if source:
        A.role(d, (COL(0), 968), source, "caption",
               alpha=A.window(t, delay + 1.2, 0.5))


def a4_ladder(d, title_l, title_r, rows_l, rows_r, verdict_l, verdict_r, t,
              hot_l=(), delay=0.0):
    """Two columns built one row at a time. The asymmetry is the argument, so
    it gets built in front of the viewer rather than asserted."""
    for x, title, rows, col, hot, verdict in (
            (COL(0), title_l, rows_l, DANGER, hot_l, verdict_l),
            (COL(9), title_r, rows_r, SUCCESS, (), verdict_r)):
        A.role(d, (x, 372), title, "mono_label", colour=col,
               alpha=A.window(t, delay, 0.4))
        d.rectangle([x, 392, x + 672, 392 + HAIRLINE], fill=LINE_PAGE)
        for i, s in enumerate(rows):
            p = A.stagger(i, t, each=0.3, gap=0.26,
                          delay=delay + (0.5 if col is DANGER else 3.1))
            if p <= 0:
                continue
            a = A.out_cubic(p)
            top = 404 + 62 * i
            is_hot = i in hot
            A.rrect(d, [x, top + (1 - a) * 10, x + 672, top + 52 + (1 - a) * 10],
                    R_CTRL, fill=A.over((40, 20, 22) if is_hot else CARD, a),
                    outline=A.over(col if is_hot else LINE_CARD, a),
                    width=HAIRLINE)
            A.role(d, (x + 28, top + 35 + (1 - a) * 10), s, "body",
                   colour=TX_1 if is_hot else TX_2, alpha=a)
        q = A.window(t, delay + (5.0 if col is DANGER else 5.2), 0.5)
        if q > 0:
            A.role(d, (x, 964), verdict, "verdict", colour=col, alpha=A.out_cubic(q))


def a5_sequence(d, rows, t, delay=0.0, accent=AC, top0=340, pitch=140):
    """Numbered rows with a value and a bar. One accent, not four."""
    for i, (title, note, value, frac) in enumerate(rows):
        p = A.stagger(i, t, each=0.5, gap=0.24, delay=delay)
        if p <= 0:
            continue
        a = A.out_cubic(p)
        top = top0 + pitch * i
        A.role(d, (COL(0), top + 46), f"{i+1:02d}", "mono_data", colour=TX_4, alpha=a)
        A.role(d, (COL(2), top + 46), title, "lead", colour=TX_1, alpha=a)
        if note:
            A.role(d, (COL(2), top + 92), note, "mono_label", alpha=a)
        if value:
            A.role(d, (COL(16), top + 26), value, "mono_data", alpha=a, anchor="rs")
        if frac is not None:
            A.bar(d, COL(8), top + 44, COL(16) - COL(8), 20,
                  frac * a, A.over(accent, a), track=A.over(RAISED, a))
        if i < len(rows) - 1:
            d.rectangle([COL(0), top + pitch - 12, COL(16), top + pitch - 12 + HAIRLINE],
                        fill=A.over(LINE_PAGE, a))


# ================================================================= the cues
# region · the verbatim phrase from this scene's narration · the caption.
# The build asserts each phrase occurs in the narration and each region is
# measured, so a marker can never land somewhere merely plausible.
CUES = {
    "dashboard": ("app-full.png", [
        dict(region="funnel",      phrase="On the left, the funnel", caption="1,890 → 22"),
        dict(region="table_top8",  phrase="Below it, every",         caption="ranked, with the reason"),
        dict(region="detail_card", phrase="on the right",            caption="the selected candidate"),
    ]),
    "wow": ("app-full.png", [
        dict(region="flagged_row", phrase="Now look at this row",    caption="KIT D816V"),
    ]),
    "structure": ("app-full.png", [
        dict(region="viewer",  phrase="the tumour peptide sitting",  caption="peptide in the groove"),
        dict(region="contact", phrase="this contact was chosen",     caption="2.58 Å vs 2.73 Å"),
    ]),
    "evidence": ("app-full.png", [
        dict(region="auc_stats",  phrase="Two and a half thousand",  caption="2,555 lab-tested"),
        dict(region="roc_bj",     phrase="Area under the curve",     caption="AUC 0.777"),
        dict(region="enrichment", phrase="our own failure",          caption="0.96× — below random"),
    ]),
    "holdout": ("app-holdout.png", [
        dict(region="holdout_scatter", phrase="Confidence barely moves", caption="0.011 of ipTM"),
        dict(region="holdout_stats",   phrase="Correlation, minus",      caption="r = −0.23"),
    ]),
    "summary": ("app-summary.png", [
        dict(region="summary_facts", phrase="It only gets these facts", caption="the only inputs"),
        dict(region="summary_meta",  phrase="checked against them",     caption="verified"),
    ]),
}

PLATE_HEAD = {
    "dashboard": ("running on the Nano", "Everything the screen considered, ranked and explained."),
    "wow":       ("the catch", "The top-ranked candidate is a healthy human protein."),
    "structure": ("predicted complex", "One contact, chosen before the prediction was run."),
    "evidence":  ("validated against lab outcomes", "2,555 peptides that were physically tested on human T-cells."),
    "holdout":   ("nine crystals the model never saw", "Confidence does not predict error."),
    "summary":   ("written on-device", "The model only restates facts it was given."),
}
PLATE_FOOT = {
    "dashboard": "docs/img/app-full.png · captured from the running app",
    "wow":       "ICDFGLARV occurs verbatim in ERK2 · the DFG motif is conserved across the kinome",
    "structure": "PDB 6ULN · Sim et al., PNAS 2020",
    "evidence":  "Bjerregaard 2017 (n=1,947) and TESLA 2020 (n=608)",
    "holdout":   "held out on Boltz-2's 2023-06-01 training cutoff",
    "summary":   "qwen3:8b via Ollama · verified against the supplied facts",
}


def make_plate_scene(sid):
    capture, cues = CUES[sid]
    eyebrow, assertion = PLATE_HEAD[sid]
    footer = PLATE_FOOT[sid]

    def render(t, dur, text=""):
        resolved = P.plan([dict(c, scale=P.pick_scale(capture, c["region"]))
                           for c in cues], text, dur)
        return P.draw_plate(capture, resolved, t, dur, eyebrow, assertion,
                            footer, dim_cue=0 if sid == "wow" else None)
    return render


# =================================================================== scenes
def meta(t, dur, text=""):
    return a1_title(["We made this video", "on the Nano too."],
                    eyebrow="before we start",
                    meta=["voice", "music", "every frame"], t=t)


def what(t, dur, text=""):
    return a1_title(["Picks the targets a", "cancer vaccine aims at."],
                    eyebrow="NeoFold Edge",
                    meta=["one small computer", "completely offline"], t=t)


def hook(t, dur, text=""):
    im = A.canvas(); d = ImageDraw.Draw(im)
    a2_head(d, "why this matters",
            "A dog named Rosie was dying of cancer. Her owner is an engineer, not a biologist.",
            t, lead="He sequenced her tumour, used AI to pick the targets, and designed her a vaccine.")
    p = A.window(t, 4.0, 1.4)
    if p > 0:
        s = A.counter(75, p, comma=False)
        w = A.role(d, (COL(0), 852), s, "stat", colour=SUCCESS, alpha=min(1, p * 4))
        A.role(d, (COL(0) + w + 18, 852), "%", "stat_unit", alpha=min(1, p * 4))
        A.role(d, (COL(0) + w + 130, 852), "her largest tumour shrank", "lead",
               alpha=A.window(t, 4.6, 0.5))
    A.role(d, (COL(0), 968),
           "one dog · not a controlled study · given with a checkpoint inhibitor",
           "caption", colour=WARNING, alpha=A.window(t, 5.4, 0.6))
    return im


def question(t, dur, text=""):
    im = A.canvas(); d = ImageDraw.Draw(im)
    A.role(d, (COL(0), Y_EYEBROW), "the genome has to move", "eyebrow",
           alpha=A.window(t, 0, 0.4))
    A.kicker(d, alpha=A.window(t, 0.12, 0.4))
    A.role(d, (COL(0), Y_HEADLINE), "Sending it out costs weeks, not a network hop.",
           "headline", alpha=A.out_cubic(A.window(t, 0.2, 0.5)))
    a4_ladder(d, "CLOUD", "NEOFOLD EDGE",
              ["the genome", "Data Use Certification", "Access Committee review",
               "signing official", "vendor agreement", "transfer", "inference",
               "someone else holds it"],
              ["the genome", "inference, on the Nano", "shortlist"],
              "weeks", "minutes", t, hot_l=(1, 2, 3, 4))
    return im


def problem(t, dur, text=""):
    N, COLS, CELL, RAD = 1890, 70, 21, 7
    rng = np.random.default_rng(11)
    real = set(rng.choice(N, 51, replace=False).tolist())
    appear = A.out_cubic(A.window(t, 0.2, 1.2))
    dim = A.out_cubic(A.window(t, 2.4, 2.0))
    # The grid has made its point by the time the 6% lands; recede it rather
    # than letting the stat sit on top of it.
    recede = A.out_cubic(A.window(t, 4.3, 0.7)) * 0.82
    base_c, off_c = TX_3, A.mix(TX_4, PAGE, 0.55)
    cols = np.zeros((N, 3), np.uint8)
    for i in range(N):
        if i / N > appear:
            cols[i] = PAGE
        elif i in real:
            cols[i] = A.mix(A.mix(base_c, SUCCESS, dim), PAGE, recede)
        else:
            cols[i] = A.mix(A.mix(base_c, off_c, dim), PAGE, recede)
    im = A.dot_grid(N, COLS, CELL, RAD, cols, ((W - COLS * CELL) / 2, 296))
    d = ImageDraw.Draw(im)
    A.role(d, (COL(0), Y_EYEBROW), "one tumour", "eyebrow", alpha=A.window(t, 0, 0.4))
    A.kicker(d, alpha=A.window(t, 0.12, 0.4))
    A.role(d, (COL(0), Y_HEADLINE), "1,890 candidates. About fifty are real.",
           "headline", alpha=A.out_cubic(A.window(t, 0.2, 0.5)))
    p = A.window(t, 4.6, 1.2)
    if p > 0:
        s = A.counter(6, p, comma=False)
        w = A.role(d, (COL(0), 900), s, "stat", colour=DANGER, alpha=min(1, p * 4))
        A.role(d, (COL(0) + w + 16, 900), "%", "stat_unit", alpha=min(1, p * 4))
        A.role(d, (COL(0) + w + 110, 900),
               "of the best candidates ever lab-tested actually worked", "lead",
               alpha=A.window(t, 5.1, 0.5))
    A.role(d, (COL(0), 968), "TESLA, Cell 2020 · 608 nominated by 25 expert pipelines · 37 worked",
           "caption", alpha=A.window(t, 5.6, 0.5))
    return im


def nano(t, dur, text=""):
    im = A.canvas(); d = ImageDraw.Draw(im)
    last = a2_head(d, "one device", "All four models stay resident.", t)
    a5_sequence(d, [
        ("MHCflurry", "binding screen · CPU", "1,890", 1.0),
        ("Boltz-2", "structure prediction · GPU", "64 s", 0.62),
        ("OpenMM", "molecular dynamics · GPU", "4 fs", 0.42),
        ("qwen3:8b", "plain-English summary · GPU", "100%", 0.78),
    ], t, delay=0.8, top0=last + 92, pitch=140)
    A.role(d, (COL(0), 968),
           "128 GB unified memory · 38 W peak, measured · about what a laptop pulls",
           "caption", alpha=A.window(t, 3.6, 0.6))
    return im


def proof(t, dur, text=""):
    im = A.canvas(); d = ImageDraw.Draw(im)
    a3_stat(d, 13, "minutes", "one tumour, end to end", "No internet connection at any point.",
            t, colour=AC, source="22 candidates × 36 s batched, measured on the Nano")
    return im


def close(t, dur, text=""):
    return a1_title(["A cancer research lab", "that fits on a desk."],
                    eyebrow="neofold edge",
                    meta=["github.com/nitishsjsucs/neofold-edge",
                          "research prioritisation only"], t=t, accent_idx=0)


SCENES = {"meta": meta, "what": what, "hook": hook, "question": question,
          "problem": problem, "nano": nano, "proof": proof, "close": close}
for _sid in CUES:
    SCENES[_sid] = make_plate_scene(_sid)

NOMINAL = {"meta": 2.2, "what": 2.4, "hook": 6.4, "question": 6.2,
           "problem": 6.4, "nano": 4.4, "proof": 2.6, "close": 2.2}
