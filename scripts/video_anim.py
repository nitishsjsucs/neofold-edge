"""Drawing and easing primitives for the demo video.

Tokens live in video_theme; this module knows how to put them on a canvas.

The one thing here that is not obvious: Pillow has no letter-spacing, so
`draw_tracked` places glyphs itself. It measures CUMULATIVE PREFIXES rather
than summing per-character widths, which preserves kerning -- summing
`getlength(ch)` would silently throw away the GPOS pairs that RAQM just
enabled. Every glyph lands on an integer x, because sub-pixel positions that
drift between frames make held type crawl.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from video_theme import (AC, BADGE_D, BADGE_FG, CARD, DIM_ALPHA, H, HAIRLINE,
                         INSET_HILITE, LEADER_W, LINE_CARD, LINE_PAGE, MARK,
                         MARK_DIM, PAGE, RAISED, RING_CLEARANCE, RING_STROKE,
                         R_CARD, R_CTRL, R_PLATE, R_RING, SCRIM, TX_1, TX_3,
                         W, font, spec)


# ------------------------------------------------------------------- easing
def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def out_cubic(t):  return 1 - (1 - clamp(t)) ** 3
def out_quint(t):  return 1 - (1 - clamp(t)) ** 5
def in_out_cubic(t):
    t = clamp(t)
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2
def out_back(t, s=1.70158):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def window(t, start, dur):
    return clamp((t - start) / max(1e-6, dur))


def stagger(i, t, each=0.5, gap=0.08, delay=0.0):
    return clamp((t - delay - i * gap) / each)


def mix(c1, c2, t):
    t = clamp(t)
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def over(colour, alpha, surface=PAGE):
    """Pre-flatten a colour at `alpha` against a KNOWN flat surface. Never use
    this over a screenshot -- that needs a real RGBA layer."""
    return mix(surface, colour, clamp(alpha))


def canvas(colour=PAGE):
    return Image.new("RGB", (W, H), colour)


# --------------------------------------------------------------------- text
def measure_tracked(f, s, track):
    return f.getlength(s) + track * max(0, len(s) - 1)


def draw_tracked(d, xy, s, f, fill, track, anchor="ls"):
    """Letter-spaced text. `anchor` is 'ls' (left), 'ms' (centre) or 'rs'
    (right), all baseline-relative."""
    if not s:
        return 0.0
    total = measure_tracked(f, s, track)
    x, y = xy
    if anchor[0] == "m":
        x -= total / 2
    elif anchor[0] == "r":
        x -= total
    if abs(track) < 0.01:                       # no tracking: one shaped run
        d.text((round(x), round(y)), s, font=f, fill=fill, anchor="ls")
        return total
    for i, ch in enumerate(s):
        gx = x + f.getlength(s[:i]) + i * track   # prefix measure keeps kerning
        d.text((round(gx), round(y)), ch, font=f, fill=fill, anchor="ls")
    return total


def role(d, xy, s, name, colour=None, alpha=1.0, anchor="ls", surface=PAGE,
         track=None):
    """Draw text in a type role from video_theme."""
    if alpha <= 0.01 or not s:
        return 0.0
    sp = spec(name)
    txt = s.upper() if sp["caps"] else s
    col = colour if colour is not None else sp["colour"]
    if alpha < 1.0:
        col = over(col, alpha, surface)
    return draw_tracked(d, xy, txt, sp["font"], col,
                        sp["track"] if track is None else track, anchor)


def role_width(s, name, track=None):
    sp = spec(name)
    txt = s.upper() if sp["caps"] else s
    return measure_tracked(sp["font"], txt, sp["track"] if track is None else track)


def wrap_role(s, name, max_w):
    sp = spec(name)
    words, lines, cur = s.split(), [], ""
    for w_ in words:
        cand = (cur + " " + w_).strip()
        if measure_tracked(sp["font"], cand.upper() if sp["caps"] else cand,
                           sp["track"]) <= max_w or not cur:
            cur = cand
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines


def counter(value, t, decimals=0, comma=True, ease=out_quint):
    v = value * ease(t)
    if decimals:
        return f"{v:,.{decimals}f}" if comma else f"{v:.{decimals}f}"
    return f"{round(v):,}" if comma else f"{round(v)}"


# --------------------------------------------------------------- primitives
def rrect(d, box, r, fill=None, outline=None, width=HAIRLINE):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def kicker(d, y=None, x=None, w=None, alpha=1.0):
    """The 96px rule under an eyebrow. Present on every non-title slide."""
    from video_theme import COL, RULE_W, Y_RULE
    y = Y_RULE if y is None else y
    x = COL(0) if x is None else x
    w = RULE_W if w is None else w
    d.rectangle([x, y, x + w * clamp(alpha), y + HAIRLINE],
                fill=over(LINE_PAGE, min(1.0, alpha * 2)))


def bar(d, x, y, w, h, frac, colour, track=RAISED):
    r = h // 2
    rrect(d, [x, y, x + w, y + h], r, fill=track)
    fw = int(w * clamp(frac))
    if fw > 2 * r:
        rrect(d, [x, y, x + fw, y + h], r, fill=colour)


# ---------------------------------------------------------------- elevation
def plate(im, box, radius=R_PLATE):
    """A card that reads as raised WITHOUT a shadow: one surface step up, a
    light ring, and a lit top inside edge. Tailwind's shadows are pure black at
    5-25% alpha -- invisible on a #0A0A0A page and destroyed by H.264 anyway."""
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = box
    rrect(d, box, radius, fill=CARD)
    rrect(d, box, radius, outline=LINE_CARD, width=HAIRLINE)
    d.line([(x0 + radius, y0 + 3), (x1 - radius, y0 + 3)],
           fill=INSET_HILITE, width=HAIRLINE)
    return im


def chip(im, xy, text_lines, max_w=520, anchor="lt"):
    """A floating caption. The ONE element allowed a shadow, because it really
    is floating above the plate -- raised to alpha 0.45 for video."""
    sp = spec("body")
    lines = []
    for ln in text_lines:
        lines.extend(wrap_role(ln, "body", max_w))
    tw = max(role_width(l, "body") for l in lines)
    th = len(lines) * sp["lh"]
    pw, ph = tw + 48, th + 32
    x, y = xy
    if anchor[0] == "r": x -= pw
    if anchor[1] == "b": y -= ph

    shadow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        [x, y + 4, x + pw, y + ph + 4], radius=R_CARD, fill=(0, 0, 0, 115))
    shadow = shadow.filter(ImageFilter.GaussianBlur(24))
    im.alpha_composite(shadow) if im.mode == "RGBA" else \
        im.paste(Image.alpha_composite(im.convert("RGBA"), shadow).convert("RGB"), (0, 0))

    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([x, y, x + pw, y + ph], radius=R_CARD,
                         fill=(*CARD, 235), outline=(*LINE_CARD, 235),
                         width=HAIRLINE)
    for i, ln in enumerate(lines):
        draw_tracked(ld, (x + 24, y + 16 + i * sp["lh"] + sp["px"]), ln,
                     sp["font"], (*TX_1, 255), sp["track"])
    out = Image.alpha_composite(im.convert("RGBA"), layer)
    return out.convert("RGB"), (pw, ph)


# --------------------------------------------------------------- annotation
def ring(layer_d, box, alpha=1.0, colour=MARK, scale=1.0):
    """The marker. One primitive -- never mixed with arrows or filled boxes."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hw, hh = (x1 - x0) / 2 * scale, (y1 - y0) / 2 * scale
    b = [cx - hw - RING_CLEARANCE, cy - hh - RING_CLEARANCE,
         cx + hw + RING_CLEARANCE, cy + hh + RING_CLEARANCE]
    layer_d.rounded_rectangle(b, radius=R_RING, outline=(*colour, int(255 * clamp(alpha))),
                              width=RING_STROKE)
    return b


def badge(layer_d, centre, n, alpha=1.0, scale=1.0, colour=MARK, d_px=BADGE_D,
          num_role="badge_num"):
    r = d_px / 2 * scale
    cx, cy = centre
    a = int(255 * clamp(alpha))
    layer_d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*colour, a))
    sp = spec(num_role)
    s = str(n)
    wpx = measure_tracked(sp["font"], s, sp["track"])
    draw_tracked(layer_d, (cx - wpx / 2, cy + sp["px"] * 0.36), s, sp["font"],
                 (*BADGE_FG, a), sp["track"])


def leader(layer_d, p0, p1, alpha=1.0, colour=MARK):
    layer_d.line([p0, p1], fill=(*colour, int(200 * clamp(alpha))), width=LEADER_W)


def scrim(im, cutout, alpha):
    """Dim everything except `cutout`. Used exactly once in the film."""
    if alpha <= 0.01:
        return im
    a = int(255 * DIM_ALPHA * clamp(alpha))
    layer = Image.new("RGBA", im.size, (*SCRIM, a))
    ImageDraw.Draw(layer).rounded_rectangle(
        [cutout[0] - 12, cutout[1] - 12, cutout[2] + 12, cutout[3] + 12],
        radius=14, fill=(0, 0, 0, 0))
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def dot_grid(n, cols, cell, radius, colours, origin):
    """n dots via numpy -- per-dot ImageDraw calls dominate the frame at 1,890."""
    rows = math.ceil(n / cols)
    arr = np.zeros((rows * cell, cols * cell, 3), np.uint8)
    arr[:, :] = PAGE
    yy, xx = np.mgrid[0:cell, 0:cell]
    c = cell / 2
    disc = ((xx - c) ** 2 + (yy - c) ** 2) <= radius ** 2
    for i in range(n):
        r_, c_ = divmod(i, cols)
        arr[r_ * cell:(r_ + 1) * cell, c_ * cell:(c_ + 1) * cell][disc] = colours[i]
    im = canvas()
    im.paste(Image.fromarray(arr), (int(origin[0]), int(origin[1])))
    return im
