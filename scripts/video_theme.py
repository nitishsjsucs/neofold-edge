"""Design tokens for the demo video. Single source of truth.

Derived from research/research-video-visual.md, which was built from shadcn/ui's
dark theme, Tailwind's neutral scale, Vercel's Geist type scale and the EBU R 95
safe areas. Values are literal on purpose -- nothing here is computed from a
"looks about right" guess.

Three decisions worth knowing before editing:

  * RAQM IS REQUIRED. Without it Pillow falls back to Layout.BASIC, which
    ignores GPOS -- and Geist ships its kerning only in GPOS. Unkerned headlines
    are a large part of what reads as "plain", and no font swap fixes it. The
    build fails loudly rather than degrading silently.

  * BORDERS ARE PRE-FLATTENED. ImageDraw takes a solid RGB tuple, so every
    white-alpha hairline is pre-composited against the surface it sits on.
    Drawing over a SCREENSHOT is the exception -- that needs a real RGBA layer,
    because the surface underneath is not a known flat colour.

  * ONE ACCENT PER FRAME. The old palette put four hues on one slide, which is
    the amateur tell. Semantic colours carry meaning and never decorate.
"""
from __future__ import annotations

import pathlib

from PIL import ImageFont, features

if not features.check("raqm"):                       # pragma: no cover
    raise SystemExit(
        "RAQM unavailable (install libfribidi). Refusing to render unkerned type: "
        "Geist carries its kerning in GPOS, which Layout.BASIC ignores.")
LAYOUT = ImageFont.Layout.RAQM

FONT_DIR = pathlib.Path(__file__).resolve().parent.parent / "video" / "fonts"

# ----------------------------------------------------------------- canvas
W, H = 1920, 1080
FPS = 30

# ------------------------------------------------------------- surfaces
# A ladder, not a shadow. Each step is ~9-17 units, wide enough to survive
# H.264 banding at 1080p.
PAGE   = (10, 10, 10)
PANEL  = (18, 19, 20)
CARD   = (27, 28, 30)
RAISED = (36, 37, 40)
SCRIM  = (0, 0, 0)                    # only ever used with alpha

# ------------------------------------------------- hairlines (pre-flattened)
LINE_PAGE    = (44, 44, 44)           # white 14% over PAGE
LINE_PANEL   = (51, 52, 53)           # white 14% over PANEL
LINE_CARD    = (59, 60, 61)           # white 14% over CARD -- the standard ring
LINE_STRONG  = (77, 78, 79)           # white 22% over CARD
INSET_HILITE = (50, 51, 52)           # white 10% -- the lit top edge of a card

# --------------------------------------------------------------- text tiers
# Four, not two. Contrast measured against PAGE.
TX_1 = (247, 248, 248)                # headings, stats        16.6:1
TX_2 = (208, 214, 224)                # body, lead             11.9:1
TX_3 = (138, 143, 152)                # labels, captions        6.1:1
TX_4 = (98, 102, 109)                 # decorative ONLY         3.4:1 (fails AA)

# ------------------------------------------------------------------ accent
AC      = (113, 112, 255)             # fills, rules
AC_TEXT = (165, 164, 255)             # accent-coloured TEXT (passes AA)
AC_TINT = (24, 24, 47)                # accent 8%, pre-flattened

# ---------------------------------------------------------------- semantic
SUCCESS = (0, 188, 125)               # a verified claim
WARNING = (254, 154, 0)               # a caveat or scope limit
DANGER  = (255, 100, 103)             # the problem, the failure
INFO    = (126, 198, 255)             # a neutral data series

# -------------------------------------------------- annotation (reserved)
MARK     = (219, 109, 40)             # rings and badges, nothing else
MARK_DIM = (96, 61, 35)               # a marker that has had its moment
BADGE_FG = (10, 10, 10)               # numeral inside a badge

# ---------------------------------------------------------------- geometry
R_CTRL, R_CARD, R_PLATE, R_RING = 8, 16, 20, 12
HAIRLINE = 2                          # 1px does not survive H.264 at 1080p
PAD_CARD, GAP_SECTION, GAP_TIGHT = 48, 48, 16
GRID = 8

# -------------------------------------------------------------------- grid
MARGIN_X, MARGIN_TOP, MARGIN_BOT = 192, 108, 108
LIVE = (192, 108, 1728, 972)          # all TEXT lives here
SAFE_GFX = (96, 54, 1824, 1026)       # EBU R 95 5% -- images may bleed, text not
COL_PITCH = 96


def COL(i: int) -> int:
    """Column edge. COL(0)=192 ... COL(16)=1728. Every text element starts at
    COL(0); there is no centred stack anywhere in the deck."""
    return MARGIN_X + COL_PITCH * i


# ---------------------------------------------------------------- type scale
# (face, px, line_height, tracking_px, all_caps, colour, tabular_numerals)
# Tracking is negative at display sizes -- large type set at body tracking is
# the other half of why the old frames read as plain.
FONTS = {
    "sans_r":  "Geist-Regular.ttf",
    "sans_m":  "Geist-Medium.ttf",
    "sans_sb": "Geist-SemiBold.ttf",
    "mono_r":  "GeistMono-Regular.ttf",
    "mono_m":  "GeistMono-Medium.ttf",
    "mono_sb": "GeistMono-SemiBold.ttf",
}

TYPE = {
    "display":    ("sans_sb", 120, 126, -3.60, False, TX_1, False),
    "headline":   ("sans_sb",  72,  80, -2.16, False, TX_1, False),
    "subhead":    ("sans_sb",  56,  64, -1.68, False, TX_1, False),
    "lead":       ("sans_m",   44,  58, -0.88, False, TX_2, False),
    "body":       ("sans_r",   34,  48, -0.48, False, TX_2, False),
    "caption":    ("sans_r",   28,  38, -0.39, False, TX_3, False),
    "eyebrow":    ("mono_m",   26,  26, +2.60, True,  TX_3, False),
    "mono_data":  ("mono_m",   30,  42,  0.00, False, TX_1, True),
    "mono_label": ("mono_r",   24,  32, +0.96, True,  TX_3, False),
    "stat":       ("sans_sb", 240, 240, -7.20, False, TX_1, True),
    "stat_unit":  ("sans_sb",  96, 240, -2.88, False, TX_3, False),
    "verdict":    ("sans_sb",  72,  80, -2.16, False, TX_1, False),
    "badge_num":  ("mono_sb",  28,  28,  0.00, False, BADGE_FG, True),
    "rail_num":   ("mono_sb",  20,  20,  0.00, False, BADGE_FG, True),
}

_FC: dict = {}


def font(role: str):
    """The ImageFont for a type role, cached."""
    face, px = TYPE[role][0], TYPE[role][1]
    key = (face, px)
    if key not in _FC:
        _FC[key] = ImageFont.truetype(str(FONT_DIR / FONTS[face]), px,
                                      layout_engine=LAYOUT)
    return _FC[key]


def spec(role: str) -> dict:
    f, px, lh, track, caps, colour, tnum = TYPE[role]
    return {"font": font(role), "px": px, "lh": lh, "track": track,
            "caps": caps, "colour": colour, "tnum": tnum}


# ---------------------------------------------------------------- vertical
# Standard rhythm, integer baselines so type never lands on a half pixel.
Y_EYEBROW   = 132
Y_RULE      = 168
Y_HEADLINE  = 268
RULE_W      = 96
LINE_STEP   = 80

# ------------------------------------------------------------ A6 plate box
PLATE_BOX  = (192, 300, 1728, 944)
PLATE_PAD  = 26
IMAGE_BOX  = (218, 326, 1702, 918)
WINDOW_W, WINDOW_H = IMAGE_BOX[2] - IMAGE_BOX[0], IMAGE_BOX[3] - IMAGE_BOX[1]

# -------------------------------------------------------------- annotation
RING_CLEARANCE, RING_STROKE = 8, 4
BADGE_D = 52
DIM_ALPHA = 0.32                      # Material scrim, used exactly once
LEADER_W = 3

# ------------------------------------------------------------------ timing
REVEAL_LEAD = 0.10                    # marker lands 100 ms EARLY: BT.1359
RING_IN, BADGE_IN, CAPTION_IN = 0.22, 0.16, 0.20
SPENT_FADE, MIN_DWELL = 0.20, 0.85
PLATE_CUT, SCENE_XFADE = 0.13, 0.20
PAUSE_W = {",": 6, ";": 8, ":": 10, ".": 12, "?": 12, "!": 12, "—": 8}
