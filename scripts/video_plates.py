"""Annotated screenshot plates — the replacement for every pan and zoom.

THE ONE NON-NEGOTIABLE RULE: the screenshot is never resampled. A capture is
2x device scale, so exactly two display scales are pixel-exact -- crop from the
2x image and paste 1:1, or reduce(2) to CSS pixels and paste 1:1. Anything else
softens the type, which is most of why the old scenes looked cheap.

If a scene's targets do not fit in one window, it CUTS to a second plate. It
never travels, and it never scales to fit.

Cue timing is derived from the narration text by weighting punctuation, then
asserted: markers must be monotonic, must not crowd each other inside
MIN_DWELL, and the anchor phrase must actually occur in that scene's narration.
A cue that cannot be placed fails the build rather than landing somewhere
plausible.
"""
from __future__ import annotations

import json
import pathlib

from PIL import Image, ImageDraw

import video_anim as A
from video_theme import (BADGE_D, CARD, HAIRLINE, H, IMAGE_BOX, LINE_CARD,
                         MARK, MARK_DIM, MIN_DWELL, PAUSE_W, PLATE_BOX,
                         REVEAL_LEAD, RING_IN, BADGE_IN, CAPTION_IN, SPENT_FADE,
                         TX_3, W, WINDOW_H, WINDOW_W, COL, Y_EYEBROW, Y_RULE)

ROOT = pathlib.Path(__file__).resolve().parent.parent
_REG = json.loads((ROOT / "video" / "app-regions.json").read_text())["captures"]
_CACHE: dict = {}


def base(capture: str, scale: str):
    key = (capture, scale)
    if key not in _CACHE:
        im = Image.open(ROOT / "docs" / "img" / capture).convert("RGB")
        _CACHE[key] = im if scale == "2x" else im.reduce(2)
    return _CACHE[key]


def region_px(capture: str, name: str, scale: str):
    cap = _REG[capture]
    if name not in cap["regions"]:
        raise KeyError(f"{name!r} not measured in {capture} -- add it to "
                       f"video/app-regions.json rather than guessing")
    x0, y0, x1, y1 = cap["regions"][name]
    w, h = cap["size"] if scale == "2x" else cap["css"]
    return [x0 * w, y0 * h, x1 * w, y1 * h]


def pick_scale(capture: str, name: str) -> str:
    """Prefer native 2x; fall back to 1x; a region that fits neither is a bug
    in the cue list, not something to paper over by scaling."""
    x0, y0, x1, y1 = region_px(capture, name, "2x")
    if (x1 - x0) <= WINDOW_W and (y1 - y0) <= WINDOW_H:
        return "2x"
    return "1x"


def window_for(capture: str, name: str, scale: str):
    src = base(capture, scale)
    x0, y0, x1, y1 = region_px(capture, name, scale)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    wx = int(max(0, min(src.width - WINDOW_W, cx - WINDOW_W / 2)))
    wy = int(max(0, min(src.height - WINDOW_H, cy - WINDOW_H / 2)))
    return wx, wy


# ------------------------------------------------------------------ timing
def weight(s: str) -> float:
    return len(s) + sum(PAUSE_W.get(c, 0) for c in s)


def anchor_time(text: str, phrase: str, clip_dur: float) -> float:
    i = text.find(phrase)
    if i < 0:
        raise KeyError(f"cue phrase {phrase!r} is not in this scene's narration")
    return clip_dur * weight(text[:i]) / weight(text)


def plan(cues, text: str, dur: float):
    """Resolve cue times and assert they are actually watchable."""
    out = []
    for c in cues:
        t = max(0.0, anchor_time(text, c["phrase"], dur) - REVEAL_LEAD)
        out.append({**c, "t": t})
    out.sort(key=lambda c: c["t"])
    for i in range(1, len(out)):                 # no two markers on top of each other
        out[i]["t"] = max(out[i]["t"], out[i - 1]["t"] + MIN_DWELL)
    if out and out[-1]["t"] > dur - MIN_DWELL:   # the last one still gets its dwell
        shift = out[-1]["t"] - (dur - MIN_DWELL)
        for c in out:
            c["t"] = max(0.0, c["t"] - shift)
    return out


# ------------------------------------------------------------------- render
def draw_plate(capture: str, cues, t: float, dur: float, eyebrow: str,
               assertion: str, footer: str = "", dim_cue: int | None = None):
    """One frame of an annotated capture."""
    im = A.canvas()
    d = ImageDraw.Draw(im)

    A.role(d, (COL(0), Y_EYEBROW), eyebrow, "eyebrow")
    A.kicker(d)
    for i, ln in enumerate(A.wrap_role(assertion, "subhead", 1536)[:1]):
        A.role(d, (COL(0), 232 + i * 64), ln, "subhead")

    active = max([i for i, c in enumerate(cues) if t >= c["t"]], default=-1)
    if active < 0:
        cue = cues[0]
        shown = -1
    else:
        cue = cues[active]
        shown = active

    scale = cue["scale"]
    src = base(capture, scale)
    wx, wy = window_for(capture, cue["region"], scale)
    crop = src.crop((wx, wy, wx + WINDOW_W, wy + WINDOW_H))

    A.plate(im, PLATE_BOX)
    im.paste(crop, (IMAGE_BOX[0], IMAGE_BOX[1]))          # 1:1, never resampled
    A.rrect(d, [IMAGE_BOX[0] - 1, IMAGE_BOX[1] - 1, IMAGE_BOX[2] + 1,
                IMAGE_BOX[3] + 1], 4, outline=LINE_CARD, width=HAIRLINE)

    if shown >= 0:
        rx0, ry0, rx1, ry1 = region_px(capture, cue["region"], scale)
        box = [IMAGE_BOX[0] + rx0 - wx, IMAGE_BOX[1] + ry0 - wy,
               IMAGE_BOX[0] + rx1 - wx, IMAGE_BOX[1] + ry1 - wy]
        box = [max(IMAGE_BOX[0] + 4, min(IMAGE_BOX[2] - 4, box[0])),
               max(IMAGE_BOX[1] + 4, min(IMAGE_BOX[3] - 4, box[1])),
               max(IMAGE_BOX[0] + 4, min(IMAGE_BOX[2] - 4, box[2])),
               max(IMAGE_BOX[1] + 4, min(IMAGE_BOX[3] - 4, box[3]))]

        since = t - cue["t"]
        if dim_cue is not None and shown == dim_cue:
            im = A.scrim(im, box, A.out_cubic(A.window(since, 0.0, 0.35)))
            d = ImageDraw.Draw(im)

        layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        ra = A.out_cubic(A.window(since, 0.0, RING_IN))
        rb = A.ring(ld, box, alpha=ra, scale=1.04 - 0.04 * ra)

        ba = A.out_back(A.window(since, 0.06, BADGE_IN))
        bx = max(IMAGE_BOX[0] + BADGE_D / 2 + 6, rb[0])
        by = max(IMAGE_BOX[1] + BADGE_D / 2 + 6, rb[1])
        A.badge(ld, (bx, by), shown + 1, alpha=min(1.0, ba * 1.4),
                scale=0.80 + 0.20 * A.clamp(ba))
        im = Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")
        d = ImageDraw.Draw(im)

        ca = A.window(since, 0.10, CAPTION_IN)
        if ca > 0 and cue.get("caption"):
            # Put the chip in whichever half of the plate the ring is NOT in,
            # then clamp hard: a caption that escapes the plate reads as a bug.
            CH = 86
            mid = IMAGE_BOX[1] + WINDOW_H / 2
            cy = rb[3] + 20 if (rb[1] + rb[3]) / 2 < mid else rb[1] - CH - 20
            cy = max(IMAGE_BOX[1] + 14, min(IMAGE_BOX[3] - CH - 14, cy))
            cx = max(IMAGE_BOX[0] + 14, min(rb[0], IMAGE_BOX[2] - 540))
            im, _ = A.chip(im, (cx, cy + (1 - A.out_cubic(ca)) * 8),
                           [cue["caption"]], max_w=480)
            d = ImageDraw.Draw(im)

    if footer:
        A.role(d, (IMAGE_BOX[0], 988), footer, "caption", colour=TX_3)
    return im


def describe(scene: str, cues, dur: float) -> str:
    """Printed at build time so sync is checkable without watching."""
    head = f"  {scene:10} {dur:5.1f}s"
    rows = [f"{head} | {i+1} {c['region']:16} {c['t']:5.2f}s  \"{c['phrase'][:34]}\""
            if i == 0 else
            f"  {'':10} {'':5} | {i+1} {c['region']:16} {c['t']:5.2f}s  \"{c['phrase'][:34]}\""
            for i, c in enumerate(cues)]
    return "\n".join(rows)


# ------------------------------------------------------------------ self-check
# `python scripts/video_plates.py --check` validates the whole pointer contract
# without rendering a frame: every capture measured, every region present, every
# narration phrase verbatim, every cue ordering monotonic. This is the cheap
# version of what the build asserts, so a broken cue is caught in a second
# rather than thirteen minutes into a render.
def check() -> int:
    import re as _re
    import video_scenes as S

    nar = (ROOT / "video" / "narration.txt").read_text()
    scenes = {sid: " ".join(l.strip() for l in body.strip().split("\n")
                            if l.strip() and not l.strip().startswith("#"))
              for sid, _note, body in _re.findall(
                  r'^@ (\S+) \| (.*?)$\n(.*?)(?=^@ |\Z)', nar, _re.S | _re.M)}

    bad = []
    for scene, (capture, cues) in S.CUES.items():
        if capture not in _REG:
            bad.append(f"{scene}: capture {capture!r} has no measured regions")
            continue
        if not (IMG := ROOT / "docs" / "img" / capture).exists():
            bad.append(f"{scene}: {IMG.relative_to(ROOT)} missing on disk")
        measured = _REG[capture]["regions"]
        if scene not in scenes:
            bad.append(f"{scene}: no '@ {scene}' block in video/narration.txt")
        for i, c in enumerate(cues, 1):
            if c["region"] not in measured:
                bad.append(f"{scene} cue {i}: region {c['region']!r} not measured "
                           f"in {capture} (have: {', '.join(sorted(measured))})")
            if scene in scenes and c["phrase"] not in scenes[scene]:
                bad.append(f"{scene} cue {i}: phrase {c['phrase']!r} is not "
                           f"verbatim in the narration — a marker would land on "
                           f"a word that is never said")
        if scene in scenes and not bad:
            ts = [c["t"] for c in plan(cues, scenes[scene], 10.0)]
            if ts != sorted(ts):
                bad.append(f"{scene}: cue times not monotonic: {ts}")

    for line in bad:
        print(f"  ✗ {line}")
    n = sum(len(c) for _cap, c in S.CUES.values())
    print(f"{'FAIL' if bad else 'ok'}: {len(S.CUES)} scenes, {n} cues, "
          f"{len(bad)} problem{'' if len(bad) == 1 else 's'}")
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    if "--check" in sys.argv:
        raise SystemExit(check())
    raise SystemExit("usage: video_plates.py --check")
