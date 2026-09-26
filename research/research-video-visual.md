# NeoFold Edge — demo video visual spec v2

Implement verbatim. Every number is literal. New module `scripts/video_theme.py` is the single source of truth; `video_anim.py` keeps only easing + geometry helpers; `video_scenes.py` is rewritten against the archetypes below.

Files referenced:
- `/Users/nitishcs/Developer/neofold-edge/scripts/video_anim.py`
- `/Users/nitishcs/Developer/neofold-edge/scripts/video_scenes.py`
- `/Users/nitishcs/Developer/neofold-edge/scripts/make_video.py`
- `/Users/nitishcs/Developer/neofold-edge/video/narration.txt`
- `/Users/nitishcs/Developer/neofold-edge/video/app-regions.json`
- `/Users/nitishcs/Developer/neofold-edge/docs/img/app-full.png` (3000×6738, 2× device scale)

---

## 0. BLOCKING PREREQUISITE — enable RAQM before anything else

Pillow's manylinux wheel falls back to `Layout.BASIC` without FriBiDi, and `Layout.BASIC` ignores GPOS. Geist ships kerning **only** in GPOS. Unkerned headlines are a large part of the "plain" look, and no font swap fixes it.

```bash
sudo apt install -y libfribidi0
python3 -c "from PIL import features; assert features.check('raqm'), 'RAQM OFF'; print('raqm ok')"
```

Every `ImageFont.truetype()` call passes `layout_engine=ImageFont.Layout.RAQM`. The build must **fail loudly**, not silently degrade:

```python
from PIL import features, ImageFont
if not features.check("raqm"):
    raise SystemExit("RAQM unavailable — apt install libfribidi0. "
                     "Refusing to render unkerned type.")
LAYOUT = ImageFont.Layout.RAQM
```

RAQM also unlocks `features=["tnum"]`, required for every animated number (see §1.4).

---

## 1. FONTS

### 1.1 Download (vendor into the repo — OFL-1.1, offline build stays offline)

```bash
cd /Users/nitishcs/Developer/neofold-edge
mkdir -p video/fonts
B=https://raw.githubusercontent.com/vercel/geist-font/main/fonts
wget -P video/fonts $B/Geist/ttf/Geist-Regular.ttf        # 126,048 B
wget -P video/fonts $B/Geist/ttf/Geist-Medium.ttf         # 127,660 B
wget -P video/fonts $B/Geist/ttf/Geist-SemiBold.ttf       # 127,872 B
wget -P video/fonts $B/GeistMono/ttf/GeistMono-Regular.ttf   # 149,284 B
wget -P video/fonts $B/GeistMono/ttf/GeistMono-Medium.ttf    # 150,096 B
wget -P video/fonts $B/GeistMono/ttf/GeistMono-SemiBold.ttf  # 150,468 B
wget -O video/fonts/OFL.txt https://raw.githubusercontent.com/vercel/geist-font/main/OFL.txt
```

Six faces, no zip, no Bold (700) anywhere — Vercel's own Geist scale never uses 700. Delete the DejaVu path.

### 1.2 Type scale — Python-ready

Tracking derives from three flat bands (Vercel's Geist bands, softened to their own Remotion-video values): **≥56px → −0.030em · 40–55px → −0.020em · 28–39px → −0.014em · 24–27px → −0.008em · mono → 0 · ALL-CAPS label → +0.100em**.

```python
# scripts/video_theme.py
FONTS = {                      # (file, weight)
    "sans_r":  ("Geist-Regular.ttf",       400),
    "sans_m":  ("Geist-Medium.ttf",        500),
    "sans_sb": ("Geist-SemiBold.ttf",      600),
    "mono_r":  ("GeistMono-Regular.ttf",   400),
    "mono_m":  ("GeistMono-Medium.ttf",    500),
    "mono_sb": ("GeistMono-SemiBold.ttf",  600),
}

# role          face       px   lh   track_em  track_px  caps   colour     tnum
TYPE = {
 "display":   ("sans_sb", 120, 126, -0.030,   -3.60,   False, "TX_1", False),
 "headline":  ("sans_sb",  72,  80, -0.030,   -2.16,   False, "TX_1", False),
 "subhead":   ("sans_sb",  56,  64, -0.030,   -1.68,   False, "TX_1", False),
 "lead":      ("sans_m",   44,  58, -0.020,   -0.88,   False, "TX_2", False),
 "body":      ("sans_r",   34,  48, -0.014,   -0.48,   False, "TX_2", False),
 "caption":   ("sans_r",   28,  38, -0.014,   -0.39,   False, "TX_3", False),
 "eyebrow":   ("mono_m",   26,  26, +0.100,   +2.60,   True,  "TX_3", False),
 "mono_data": ("mono_m",   30,  42,  0.000,    0.00,   False, "TX_1", True),
 "mono_label":("mono_r",   24,  32, +0.040,   +0.96,   True,  "TX_3", False),
 # derived roles
 "stat":      ("sans_sb", 240, 240, -0.030,   -7.20,   False, "TX_1", True),
 "stat_unit": ("sans_sb",  96, 240, -0.030,   -2.88,   False, "TX_3", False),
 "verdict":   ("sans_sb",  72,  80, -0.030,   -2.16,   False, "TX_1", False),
 "badge_num": ("mono_sb",  28,  28,  0.000,    0.00,   False, "BADGE_FG", True),
}
```

Hard floors: **no glyph below 24px**, **no weight below 400**, every line-height an integer so `y` steps by whole pixels.

### 1.3 Tracked text — Pillow has no `letter_spacing`

Kerning-preserving (measure cumulative prefixes, never sum per-character widths):

```python
def draw_tracked(d, xy, s, font, fill, track_px, anchor="ls"):
    """anchor: 'ls' left-baseline, 'ms' centre-baseline, 'rs' right-baseline."""
    total = font.getlength(s) + track_px * max(0, len(s) - 1)
    x, y = xy
    if anchor[0] == "m": x -= total / 2
    elif anchor[0] == "r": x -= total
    for i, ch in enumerate(s):
        gx = x + font.getlength(s[:i]) + i * track_px
        d.text((round(gx), round(y)), ch, font=font, fill=fill, anchor="ls")
    return total

def measure_tracked(font, s, track_px):
    return font.getlength(s) + track_px * max(0, len(s) - 1)
```

Every glyph position is rounded to an integer. Sub-pixel positions that drift between frames cause visible crawl on held text.

### 1.4 Numbers

Any digit that changes between frames is drawn with a tabular-figure font instance and right-aligned:

```python
def tnum_font(face_key, px):
    file, _ = FONTS[face_key]
    return ImageFont.truetype(str(FONT_DIR / file), px, layout_engine=LAYOUT)
# draw with: d.text(..., features=["tnum"])   # requires RAQM
```
Counters (`counter()` in `video_anim.py`) use `mono_data` / `stat` with `tnum` and anchor `rs` at a fixed x. No centre-anchored counters — the string width changes and the number wobbles.

---

## 2. COLOUR CONSTANTS

Dark only. shadcn/Tailwind-neutral base, surface ladder widened per the H.264 note (5-unit deltas band), all alpha borders **pre-flattened** so `ImageDraw` can use a single RGB tuple. Every neutral is chroma 0.

```python
# scripts/video_theme.py  — RGB tuples, dark theme
# ---- surface ladder (page → raised). Depth comes from the step, not a shadow.
PAGE      = (10, 10, 10)     # #0A0A0A  shadcn --background / neutral-950
PANEL     = (18, 19, 20)     # #121314  sidebar / section band
CARD      = (27, 28, 30)     # #1B1C1E  card, screenshot plate
RAISED    = (36, 37, 40)     # #242528  input well, code block, bar track
SCRIM     = (0, 0, 0)        # used only with alpha, see §5.7

# ---- hairlines, white-alpha pre-flattened onto each surface (14% / 22%)
LINE_PAGE   = (44, 44, 44)   # white 14% over PAGE    — section dividers on page
LINE_PANEL  = (51, 52, 53)   # white 14% over PANEL
LINE_CARD   = (59, 60, 61)   # white 14% over CARD    — the standard 2px card ring
LINE_STRONG = (77, 78, 79)   # white 22% over CARD    — emphasised divider
INSET_HILITE= (50, 51, 52)   # white 10% over CARD    — 2px top inside edge of a card

# ---- text tiers (four, not two). Contrast measured vs PAGE #0A0A0A.
TX_1 = (247, 248, 248)       # #F7F8F8  headings, stats           16.6:1
TX_2 = (208, 214, 224)       # #D0D6E0  body, lead                11.9:1
TX_3 = (138, 143, 152)       # #8A8F98  labels, captions, units     6.1:1
TX_4 = ( 98, 102, 109)       # #62666D  disabled / decorative      3.4:1  <-- FAILS
#   TX_4 carries NO fact. Decorative or ≥32px sequence numerals only.

# ---- exactly ONE deck accent (links, focus, the active item, the repo URL)
AC        = (113, 112, 255)  # #7170FF  solid fills / rules        5.2:1
AC_TEXT   = (165, 164, 255)  # #A5A4FF  accent-coloured TEXT      10.0:1
AC_TINT   = ( 24,  24,  47)  # #18182F  accent @8% pre-flattened — badge/callout fill

# ---- semantic (shadcn chart dark, gamut-clipped). Never decorative.
SUCCESS = (  0, 188, 125)    # #00BC7D  a claim that was verified   8.0:1
WARNING = (254, 154,   0)    # #FE9A00  a caveat / scope limit      9.3:1
DANGER  = (255, 100, 103)    # #FF6467  the problem, the failure    6.9:1
INFO    = (126, 198, 255)    # #7EC6FF  neutral data series        10.9:1

# ---- annotation (RESERVED: appears nowhere else in the deck)
MARK     = (219, 109,  40)   # #DB6D28  Primer severe/fg dark       5.9:1
MARK_DIM = ( 96,  61,  35)   # MARK @30% pre-flattened over PAGE — spent markers
BADGE_FG = ( 10,  10,  10)   # numeral inside the badge, on MARK    5.9:1

# ---- geometry tokens (shadcn measured, ×2 for slide scale)
R_CTRL, R_CARD, R_PLATE, R_RING, R_PILL = 8, 16, 20, 12, 9999
HAIRLINE = 2                 # 1px is destroyed by H.264 at 1080p
PAD_CARD, GAP_SECTION, GAP_TIGHT = 48, 48, 16
GRID = 8
```

Discipline rules, enforced by review:
1. **One chromatic hue per frame** outside the semantic roles. `AC`, `SUCCESS`, `WARNING`, `DANGER`, `INFO`, `MARK` never appear more than one-at-a-time per slide except in an explicit legend.
2. Foreground never `#FFFFFF`, canvas never `#000000`.
3. Anything drawn **over a screenshot** composites on an RGBA layer with real alpha. `fade()`'s pre-flatten-against-`BG` trick is valid only over a known flat surface; pass the surface explicitly.

---

## 3. LAYOUT GRID (1920×1080)

```python
W, H = 1920, 1080
MARGIN_X, MARGIN_TOP, MARGIN_BOT = 192, 108, 108
LIVE = (192, 108, 1728, 972)          # 1536 × 864 — ALL TEXT lives inside this
SAFE_GFX = (96, 54, 1824, 1026)       # EBU R 95 5% — images may bleed here, text may not
SAFE_ACT = (67, 38, 1853, 1042)       # EBU R 95 3.5%

COLS, COL_PITCH, GUTTER = 16, 96, 32  # Carbon 16-col; 16×96 = 1536 = live width
def COL(i):  return 192 + 96 * i      # COL(0)=192 … COL(16)=1728
def SPAN(a, b): return (COL(a), COL(b))   # content edges are always COL() values
SPACE = (8, 16, 24, 32, 48, 64, 96, 128, 192)
```

**Every text element on every slide starts at x = COL(0) = 192.** One entry point, one pixel, whole deck. Two exceptions: (a) a title card statement of ≤6 words may be bottom-left anchored (still x=192 — it is never centred); (b) a screenshot plate may be centred in the live width. There is **no centred stack** anywhere.

Standard vertical rhythm (baselines, integer):

| slot | value |
|---|---|
| eyebrow cap-top / baseline | 108 / 132 |
| kicker rule (2px, x 192→288) | y = 168 |
| headline first baseline | 268 (+80 per extra line) |
| lead first baseline | last headline baseline + 112 |
| evidence block top | 300 (no lead) / 600 (with lead) |
| evidence block bottom | 944 |
| footer caption baseline | 968 |

Block gaps: eyebrow→rule 36 · rule→headline 100 · headline→lead 112 · lead→evidence 64 · evidence→footer 24.

---

## 4. SLIDE ARCHETYPES

All coordinates absolute. Left edge 192 unless stated.

### A1 — TITLE CARD (bottom-left anchored) — `meta`, `what`, `close`
```
eyebrow      cap-top 648, baseline 672,  x=192, TYPE.eyebrow, TX_3
rule         2px, x 192→288, y=704, LINE_PAGE
display      1–2 lines, TYPE.display; LAST baseline = 892 (2 lines: 766 + 892)
meta row     baseline 956, x=192, TYPE.mono_label, TX_3
             segments joined by "  ·  "; at most one segment in AC_TEXT (the URL)
```
Top 60% of the frame stays empty. This is the single composition change that most alters how the title cards read.

### A2 — STATEMENT — `hook`, `question` header, `proof`
```
eyebrow   108/132 · rule y=168 · headline baselines 268, 348, 428 (max 3 lines, width ≤ COL(12)=1344)
lead      first baseline = last headline baseline + 112, max 2 lines at +58, width ≤ COL(11)=1248
evidence  y 600→944 (a stat, a bar row, or a plate)
footnote  baseline 968, TYPE.caption, TX_3 (scope limits in WARNING)
```
The headline is a **full sentence stating the takeaway** (assertion-evidence), never a topic phrase, never a bullet list. Colour **exactly one word or one number** per slide.

### A3 — BIG STAT — the 75%, 38 W, 13 minutes, 6%
```
eyebrow   108/132 (this IS the stat's label — label always above value)
rule      y=168
value     TYPE.stat, baseline 560, x=192, tnum, colour = claim colour
unit      TYPE.stat_unit, SAME baseline 560, x = 192 + measure_tracked(value) + 24, TX_3
delta     TYPE.lead, baseline 660, TX_2
caption   TYPE.caption, baseline 720, TX_3
source    TYPE.caption, baseline 968, TX_3
right half x COL(11)=1248 → COL(16)=1728 free for a sparkline or small plate
```
Never centre a number that has a caption.

### A4 — COMPARISON LADDER — `question`
```
header    eyebrow 108/132 · rule 168 · headline baseline 268 (1 line)
col L     x 192 → 864  (672 wide, COL 0–7)
col R     x 1056 → 1728 (672 wide, COL 9–16)   gutter 192
col title TYPE.mono_label, baseline 372, DANGER (L) / SUCCESS (R)
col rule  2px, full column width, y=392, LINE_PAGE
rows      h=58, gap=10, pitch=68, row i top = 416 + 68*i, max 8 rows (last bottom 890)
          rounded rect r=R_CTRL(8), fill CARD, ring HAIRLINE(2) LINE_CARD
          hot rows: fill (58,26,30)→ retune to (40,20,22), ring DANGER
          label TYPE.body baseline = top + 38, x = col_x + 28, TX_2 (TX_1 when hot)
verdict   TYPE.verdict, baseline 964, x = col_x, DANGER (L) / SUCCESS (R)
```

### A5 — SEQUENCE / FUNNEL — `funnel`, `nano`
```
header    as A2 (headline baseline 268)
rows      4 max, pitch 152, row i top = 340 + 152*i (last bottom 948)
  numeral "01".."04" TYPE.mono_data 40px TX_4, x=192, baseline top+46
  title   TYPE.lead, x=COL(2)=384, baseline top+46, TX_1
  note    TYPE.mono_label, x=384, baseline top+92, TX_3
  value   TYPE.mono_data 40px tnum, anchor "rs" at x=COL(16)=1728, baseline top+26
  bar     x COL(8)=960 → 1728, y top+44 → top+64, h=20, r=10
          track RAISED, fill = one accent only
  divider 2px, x 192→1728, y = top+140, LINE_PAGE (omit after last row)
```

### A6 — ANNOTATED CAPTURE (replaces every pan/zoom) — `dashboard`, `wow`, `structure`, `evidence`, `holdout`, `summary`
```
eyebrow    cap-top 108, baseline 132, x=192, TX_3
rule       2px, x 192→288, y=168
assertion  TYPE.subhead, ONE line, baseline 232, x=192, width ≤ 1536
plate      wide:  box (192, 300) → (1728, 944)      1536 × 644
           image box (218, 326) → (1702, 918)       1484 × 592   [PLATE_PAD = 26]
           rail:  plate (192,300) → (192+img_w+52, 352+img_h)
                  rail  x = plate_right + 96 → 1728 (require img_w ≤ 1000 → rail ≥ 388 wide)
caption    TYPE.caption, baseline 988, x = 218 (flush to the image's left edge), TX_3
```
Plate treatment is §6. Markers, leaders, captions are §5.

### A7 — ESTABLISH + DETAIL (used for `dashboard` only)
Frame 0 is an A6 plate showing the whole above-the-fold page with **all** markers visible at 100% simultaneously, held 1.20 s, no dim, no caption-rail text. Then a 4-frame dissolve to each detail plate in narration order. Purpose is orientation only — nothing in frame 0 has to be readable.

---

## 5. SCREENSHOT ANNOTATION SYSTEM

### 5.1 The one non-negotiable rule: the screenshot is never resampled

`docs/img/app-full.png` is a 2× device-scale capture. Only two display scales are permitted, both pixel-exact:

```python
BASE_2X = Image.open(IMG / "app-full.png")            # 3000 × 6738  (capture px)
BASE_1X = BASE_2X.reduce(2)                           # 1500 × 3369  (CSS px, clean box filter)
WINDOW_W, WINDOW_H = 1484, 592                        # == the A6 image box, exactly

# "2x": crop WINDOW from BASE_2X  → native capture pixels, pasted 1:1  (sharpest)
# "1x": crop WINDOW from BASE_1X  → 1 CSS px per screen px, pasted 1:1
```

Window placement is deterministic:
```python
def window_for(region_px, src_w, src_h):
    x0, y0, x1, y1 = region_px
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return (int(max(0, min(src_w - WINDOW_W,  cx - WINDOW_W / 2))),
            int(max(0, min(src_h - WINDOW_H,  cy - WINDOW_H / 2))))

def pick_scale(region_2x):                 # prefer 2x; fall back to 1x; else split the scene
    w = region_2x[2] - region_2x[0]; h = region_2x[3] - region_2x[1]
    if w <= WINDOW_W and h <= WINDOW_H: return "2x"
    if w <= 2 * WINDOW_W and h <= 2 * WINDOW_H: return "1x"
    raise ValueError("region does not fit one plate — split into two cues")
```
If a scene's named regions do not fit one window, **cut to a second static plate**. Never pan, never scale to fit.

### 5.2 Worked cue table (from the measured `video/app-regions.json`)

CSS px = fraction × (1500, 3369); capture px = ×2.

| cue | scene | region | scale | window origin | window box |
|---|---|---|---|---|---|
| E0 | dashboard | establish | 1x | (8, 0) | (8,0)→(1492,592) |
| D1 | dashboard | `funnel` | 2x | (0, 387) | (0,387)→(1484,979) |
| D2 | dashboard | `table_top8` | 2x | (0, 2032) | (0,2032)→(1484,2624) |
| D3 | dashboard | `detail_card` | 1x | (16, 0) | (16,0)→(1500,592) |
| W1 | wow | `table` + `flagged_row` | 1x | (16, 890) | (16,890)→(1500,1482) |
| W2 | wow | `flagged_row` | 2x | (0, 2519) | (0,2519)→(1484,3111) |
| S1 | structure | `viewer` | 1x | (16, 435) | (16,435)→(1500,1027) |
| S2 | structure | `confidence`+`contact` | 1x | (16, 826) | (16,826)→(1500,1418) |
| V1 | evidence | `auc_stats`+`roc_bj`+`roc_te` | 1x | (16, 1648) | (16,1648)→(1500,2240) |
| V2 | evidence | `precision_k` | 1x | (16, 2054) | (16,2054)→(1500,2646) |

Region boxes in CSS px, for marker placement: `funnel` (31,205,580,478) · `table` (15,1001,604,1482) · `table_top8` (15,1017,604,1311) · `flagged_row` (15,1392,604,1424) · `detail_card` (611,70,1486,376) · `viewer` (612,482,1485,922) · `confidence` (612,981,1485,1104) · `contact` (628,1104,1469,1264) · `auc_stats` (628,1684,1469,1759) · `roc_bj` (628,1808,1041,2204) · `roc_te` (1057,1808,1469,2204) · `precision_k` (628,2250,1469,2450) · `enrichment` (628,2704,1469,2986).

`holdout` and `summary` currently point at `vid-holdout.png` / `vid-summary.png`, which have **no measured regions**. Extend `video/app-regions.json` to a keyed map and re-measure with `getBoundingClientRect` (per `scripts/measure_regions.md`) before those scenes render:

```json
{ "captures": {
    "app-full.png":    { "size": [3000, 6738], "regions": { "...": [0,0,0,0] } },
    "vid-holdout.png": { "size": [2160, 2000], "regions": {
        "holdout_scatter": [0,0,0,0], "holdout_corr": [0,0,0,0] } },
    "vid-summary.png": { "size": [2160, 1800], "regions": {
        "summary_facts": [0,0,0,0], "summary_verified": [0,0,0,0] } } } }
```
The build **asserts** every cue's region exists in the JSON and fails otherwise. No eyeballed fractions.

### 5.3 Marker: ring

```python
RING_CLEARANCE = 8        # gap between the UI element and the stroke
RING_STROKE    = 4        # GitHub's 3 logical px, scaled for 1080p
RING_RADIUS    = R_RING   # 12
RING_COLOUR    = MARK     # #DB6D28, reserved
# box = element box in plate coords, inflated by RING_CLEARANCE; stroke drawn outward.
# NO drop shadow. NO glow. One primitive, never mixed with arrows or boxes.
```

### 5.4 Marker: numbered badge

```python
BADGE_D        = 52                  # ≈4.8% of frame height
BADGE_FILL     = MARK
BADGE_NUMERAL  = TYPE["badge_num"]   # GeistMono SemiBold 28, tnum, BADGE_FG (10,10,10) = 5.9:1
BADGE_RING     = None                # add 3px TX_1 ring ONLY when it overlaps busy UI
BADGE_CENTRE   = (ring_x0, ring_y0)  # pinned to the ring's top-left corner
# clamp: keep the full circle ≥ 30px inside the image box; push inward along both axes
```
Numbers are assigned in narration order, which is also reading order. No drop shadow.

### 5.5 Caption placement

Two modes; a scene uses one, never both.

**Rail** (preferred when `img_w ≤ 1000`): entry `i` top = `326 + 132*i`, badge (36px, same fill/typography scaled) centred at `(rail_x + 18, top + 18)`, caption `TYPE.body` at `x = rail_x + 60`, first baseline `top + 26`, max 2 lines at +40, max width `rail_w - 60`.

**On-plate chip** (wide plates): rounded rect `r = R_CARD(16)`, drawn on an RGBA layer — fill `CARD` at alpha 235, ring `HAIRLINE(2)` `LINE_CARD` at alpha 235, padding 24 × 16, text `TYPE.body` `TX_1`, max width 520, placed 24px from the ring on the side with the most free space, and required not to overlap any other ring or the assertion line.

Caption text is **1–5 words, or one short clause**. It is never the narration transcript (redundancy principle, 16/16 experiments, median d = 0.86). The narration carries the sentence; the caption names the thing.

### 5.6 Leader line

Used only when a chip or rail entry is >120px from its ring and there are ≤2 markers on the plate.
```python
LEADER_W      = 3
LEADER_COLOUR = MARK        # drawn on an RGBA layer at alpha 200
LEADER_LEN    = (88, 160)   # px, clamped
LEADER_ANGLE  = (45, 30, 60)  # try in this order; NEVER 0° or 90°
# from a point on the ring perimeter, to a point 24px from the chip edge.
```

### 5.7 Dim / spotlight — one moment in the film only

Dimming is used **once**: the `wow` reveal (W2). Everywhere else the ring alone carries the signal, at full screenshot contrast.
```python
DIM_ALPHA    = 0.32                 # Material scrim. NOT 0.80/0.86.
DIM_CUTOUT   = ring_box inflated by 12, radius 14
DIM_IN       = 0.35 s, out_cubic
DIM_COLOUR   = SCRIM (0,0,0)        # true black at alpha, on an RGBA layer
```

### 5.8 Reveal timing relative to narration

Kokoro returns no alignment, so anchors are computed from the text with punctuation weighting, then verified in the build log.

Cue syntax — add to `video/narration.txt` immediately under each `@ scene | note` header, one line per marker:
```
> 1 | funnel      | "the funnel"            | 1,890 screened in 9 s
> 2 | table_top8  | "every one of them"     | ranked, with the reason
> 3 | detail_card | "on the right"          | the selected candidate
```
Fields: index · region key · verbatim anchor phrase from this block's narration · caption text.

```python
PAUSE_W = {",": 6, ";": 8, ":": 10, ".": 12, "?": 12, "!": 12, "—": 8}

def anchor_time(text, phrase, clip_dur):
    i = text.index(phrase)                      # KeyError → build fails, fix the cue
    def weight(s): return len(s) + sum(PAUSE_W.get(c, 0) for c in s)
    return clip_dur * weight(text[:i]) / weight(text)

REVEAL_LEAD  = 0.10      # marker lands 100 ms EARLY. ITU-R BT.1359 tolerates ~125 ms of
                         # audio lag but only ~45 ms of audio lead: early reads in-sync,
                         # late reads broken.
RING_IN      = 0.22      # alpha 0→1, scale 1.04→1.00, out_cubic ≈ cubic-bezier(.2,0,0,1)
BADGE_IN     = 0.16      # starts RING_IN_START + 0.06, scale 0.80→1.00, out_back
CAPTION_IN   = 0.20      # starts RING_IN_START + 0.10, alpha 0→1 + 8px rise
SPENT_FADE   = 0.20      # previous markers → alpha 0.30 (MARK_DIM). Exactly one signal lit.
MIN_DWELL    = 0.85      # Netflix minimum event duration 5/6 s. asserted.
PLATE_CUT    = 0.13      # 4-frame dissolve between plates inside a scene
SCENE_XFADE  = 0.20      # 6-frame dissolve between scenes (was 0.45 — too mushy on stills)
```
Build-time assertions: cue times monotonic; `cue[i+1].t - cue[i].t ≥ MIN_DWELL`; last cue ≥ `MIN_DWELL` before scene end; plate cut placed at `(last_cue_of_A + first_cue_of_B)/2 - 0.10`. Print the cue table with times so sync is checkable without watching:
```
dashboard  9.6s | 1 funnel      1.42s "the funnel"
                | 2 table_top8  4.05s "every one of them"
                | 3 detail_card 7.11s "on the right"   cut A→B 2.74s  B→C 5.58s
```

---

## 6. ELEVATION ON DARK (no black shadows)

A card is elevated by **a surface step plus a light ring**, never by a blur. Tailwind's `shadow-sm`…`shadow-2xl` are pure black at 5–25% alpha: invisible on `#0A0A0A` and destroyed by H.264 anyway.

Plate / card recipe, in draw order:
1. Page is `PAGE` (10,10,10).
2. Rounded rect `r = R_PLATE(20)`, fill `CARD` (27,28,30) — **one ladder step up**, a 17-unit delta that survives compression.
3. Ring: `rounded_rectangle(..., outline=LINE_CARD, width=2)` — white 14% pre-flattened. This does the elevating.
4. Inset top highlight: a 2px horizontal line in `INSET_HILITE` (50,51,52) across the inside top edge, inset 3px from the ring, spanning `r`→`w−r`. Reads as light falling on the top edge.
5. Content (the screenshot) pasted at the image box, then a 2px `LINE_CARD` ring drawn directly around the image so the capture's own dark chrome does not bleed into the card fill.
6. No shadow.

A genuinely floating element (an on-plate caption chip, a popover) may have a shadow, at video alpha: black, offset (0, 4), Gaussian blur radius 24, alpha 0.45 (raised 3–8× from light-mode's 0.04–0.16), composited under the chip on an RGBA layer. Inline cards never get one.

Bands and dividers: a section band is `PANEL` (18,19,20) on `PAGE`; a divider is 2px `LINE_PAGE` (44,44,44) — never a mid-grey line.

---

## 7. WHAT TO DELETE

Named, by symbol:

1. **`video_anim.FD` and `video_anim.font()`'s DejaVu map** (`/usr/share/fonts/truetype/dejavu`, `DejaVuSans*.ttf`). Replaced by `video_theme` + `video/fonts/Geist*`. DejaVu has no display cut, no optical size, and loose spacing designed for 10–12px UI text.
2. **`video_scenes.screen()`'s crop interpolation** — `box = [a[i] + (b[i]-a[i]) * e ...]`, the `a`/`b`/`ease` parameters and every call site's crop pair. This is the pan/zoom. It resamples the screenshot every frame, softens it, and travels while the narration says something else. Gone entirely; replaced by §5.
3. **`make_video.scene_frame()`'s `drift` parameter** and the trailing `im.resize(...).crop(...)` "slow global push", plus `0.016 * (i / n)` at the call site. It breaks the 1:1 rule on every capture frame and causes text crawl on held type.
4. **`video_anim.spotlight()`'s defaults `dim=0.80`** and the `dim=0.8` / `dim=0.86` call sites in `screen()` and `wow()`. Replaced by `DIM_ALPHA = 0.32`, used once (W2).
5. **`video_scenes.eyebrow()`** — centred at `W/2`, `FAINT`, 22px, `anchor="ma"`. Replaced by the left-aligned `TYPE.eyebrow` (GeistMono Medium 26, uppercase, +0.10em, `TX_3`, x=192) plus the 96px kicker rule.
6. **Every `anchor="ma"` / `"mm"` in a multi-element slide** — `meta`, `what`, `hook`, `question` headers, `problem` labels, `nano` chips, `proof` pairs, `close`. Left-align to x=192 with `"ls"`. Centring is retained only for A1's ≤6-word statement, which is anyway bottom-left in the new spec.
7. **The five-colour-at-once palette** — `funnel`'s `MUTED/ACCENT/TEAL/PURPLE` step colours and `nano`'s `TEAL/PURPLE/ACCENT/AMBER` chip colours. One accent per frame; the four model chips differentiate by `mono_label` role text and surface step, not by four hues.
8. **`video_anim`'s legacy palette names** — `BG`, `PANEL`, `INK`, `MUTED`, `FAINT`, `ACCENT`, `TEAL`, `PURPLE`, `AMBER`, `RED`, `GREEN`. Two text tiers (`INK`/`MUTED`) is the amateur tell; four tiers is the fix.
9. **`make_video`'s duplicate constants** — `BG`, `INK`, `MUTED`, `ACCENT`, `GOOD`, `BAD`, `FONT_DIR`, `F_REG`, `F_BOLD`, `F_MONO`. Dead duplicates of a different palette. Import `video_theme`.
10. **`make_video.XFADE = 0.45`** → `SCENE_XFADE = 0.20`. A 0.45 s dissolve between static screenshots reads as mush.
11. **`video_scenes.NOMINAL` + the `s = min(1.7, max(1.0, dur/nominal))` time-warp** in `scene_frame()`. Animation timing comes from the cue list, which is derived from the measured clip length — no global stretch.
12. **`video_scenes.real_ui()`** (unused, scales `dashboard.png` by an arbitrary factor) and the multi-capture set `vid-dashboard.png`, `vid-roc.png`, `vid-holdout.png`, `vid-summary.png` as *primary* sources. `app-full.png` + measured regions is the single source; anything else needs its own measured region block (§5.2).
13. **Ad-hoc radii and track colours** — `rrect(..., 6)`, `8`, `9`, `12`, `14` and `bar(track=(38,45,54))`. Use `R_CTRL/R_CARD/R_PLATE/R_RING` and `RAISED`.
14. **`video_scenes.screen()`'s `caption` at 42px centred on y=96 and `sub` at y=H−40** — the `sub` line sits at y=1040, outside the 972 text-safe box and at the edge of EBU action-safe. Replaced by A6's assertion (baseline 232) and footer caption (baseline 988).
15. **`problem`'s colour mixing toward `MUTED` at 0.55** and `mix(BG, MUTED, ...)` grid maths — retarget to `TX_4`→`SUCCESS` over `PAGE`.

---

## 8. Implementation order

1. `libfribidi0` + the RAQM assert (§0). Verify a 72px headline visibly kerns before touching anything else.
2. `video/fonts/` wgets; new `scripts/video_theme.py` holding §1.2, §2, §3 verbatim; `draw_tracked` / `measure_tracked` into `video_anim.py`.
3. Delete list §7 items 1–9, then re-render `what` and `close` as A1 to confirm type and palette.
4. `BASE_1X`/`BASE_2X`/`window_for`/`pick_scale` + the A6 plate renderer + §6 elevation. Render `dashboard` D1 as a single still and check the screenshot is pixel-sharp.
5. Cue syntax in `video/narration.txt`, `anchor_time()`, the assertion set, the printed cue table. Re-render all six product scenes as A6/A7.
6. Delete list §7 items 10–15; rebuild `question` (A4), `funnel`/`nano` (A5), `hook`/`proof` (A2/A3).
7. Full build; check the cue table in the log before watching, then watch once at 1× with sound to confirm every marker lands on its noun.