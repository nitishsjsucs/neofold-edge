"""Build the 2-minute demo video from video/narration.txt and docs/img/.

Runs entirely on the Nano: Piper for the voice, cairosvg to rasterise the
diagrams, Pillow to compose every frame, ffmpeg (the static aarch64 binary
that ships inside imageio-ffmpeg) to encode. No cloud service touches it,
which is the same claim the film itself makes.

Frames are composed in Python rather than driven by ffmpeg filter graphs
because the shots need things filters make awkward: a zoom that lands on a
bounding box found by colour-searching the source image, a highlight that
fades in partway through a shot, and dimming everything except one table row.

    python scripts/make_video.py                 # full build
    python scripts/make_video.py --scene wow     # re-render one scene
    python scripts/make_video.py --audio-only    # just the narration clips

Timing is driven by the AUDIO: each scene's visuals are stretched to the
measured length of its narration clip, so editing a line of script re-times
the picture automatically.
"""
from __future__ import annotations

import argparse
import math
import pathlib
import re
import shutil
import subprocess
import sys
import wave

ROOT = pathlib.Path(__file__).resolve().parent.parent
IMG = ROOT / "docs" / "img"
OUT = ROOT / "video" / "build"
VOICES = pathlib.Path.home() / "voices"

W, H, FPS = 1920, 1080, 30
BG = (13, 17, 23)                  # #0d1117, the project's canvas
INK = (230, 237, 243)
MUTED = (139, 148, 158)
ACCENT = (168, 199, 250)
GOOD = (111, 214, 111)
BAD = (248, 81, 73)
XFADE = 0.45                       # seconds of crossfade between shots
VOICE = "en_GB-alan-medium"
LENGTH_SCALE = "0.97"              # slightly quicker than default

FONT_DIR = pathlib.Path("/usr/share/fonts/truetype/dejavu")
F_REG, F_BOLD, F_MONO = (FONT_DIR / "DejaVuSans.ttf",
                         FONT_DIR / "DejaVuSans-Bold.ttf",
                         FONT_DIR / "DejaVuSansMono.ttf")


def ffmpeg() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


# ----------------------------------------------------------------- narration
def parse_narration() -> list[dict]:
    txt = (ROOT / "video" / "narration.txt").read_text()
    out = []
    for sid, note, body in re.findall(
            r'^@ (\S+) \| (.*?)$\n(.*?)(?=^@ |\Z)', txt, re.S | re.M):
        lines = [l.strip() for l in body.strip().split("\n")
                 if l.strip() and not l.strip().startswith("#")]
        out.append({"id": sid, "note": note.strip(), "text": " ".join(lines)})
    return out


def render_audio(scenes: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    model = VOICES / f"{VOICE}.onnx"
    if not model.exists():
        sys.exit(f"voice model missing: {model}")
    for s in scenes:
        wav = OUT / f"vo-{s['id']}.wav"
        subprocess.run(["piper", "-m", str(model), "-f", str(wav),
                        "--length_scale", LENGTH_SCALE],
                       input=s["text"].encode(), check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(str(wav)) as w:
            s["dur"] = w.getnframes() / w.getframerate()
        print(f"  {s['id']:10} {s['dur']:5.1f}s  {s['text'][:58]}…")
    total = sum(s["dur"] for s in scenes)
    print(f"  {'TOTAL':10} {total:5.1f}s  ({int(total//60)}:{int(total%60):02d})")


def concat_audio(scenes: list[dict]) -> pathlib.Path:
    """One narration track, with a short beat of silence between scenes."""
    lst = OUT / "audio.txt"
    gap = OUT / "gap.wav"
    subprocess.run([ffmpeg(), "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=22050:cl=mono", "-t", "0.35", str(gap)],
                   check=True, capture_output=True)
    parts = []
    for s in scenes:
        parts += [f"file '{OUT / f'vo-{s['id']}.wav'}'", f"file '{gap}'"]
    lst.write_text("\n".join(parts) + "\n")
    track = OUT / "narration.wav"
    subprocess.run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(track)], check=True, capture_output=True)
    return track


# -------------------------------------------------------------------- visuals
def _img():
    from PIL import Image, ImageDraw, ImageFont
    return Image, ImageDraw, ImageFont


def font(path: pathlib.Path, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(str(path), size)


def canvas():
    Image, _, _ = _img()
    return Image.new("RGB", (W, H), BG)


def wrap(draw, text: str, fnt, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            lines.append(cur); cur = w_
    if cur:
        lines.append(cur)
    return lines


def rasterise_svg(name: str, target_w: int) -> "Image.Image":
    """SVG diagram -> RGB image on the project canvas colour."""
    import io
    import cairosvg
    from PIL import Image
    src = IMG / f"diagram-{name}.dark.svg"
    png = cairosvg.svg2png(url=str(src), output_width=target_w)
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    flat = Image.new("RGB", im.size, BG)
    flat.paste(im, (0, 0), im)
    return flat


def fit(im, pad: int = 90):
    """Letterbox an image into the frame, preserving aspect."""
    Image, _, _ = _img()
    box_w, box_h = W - 2 * pad, H - 2 * pad
    sc = min(box_w / im.width, box_h / im.height)
    im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))),
                   Image.LANCZOS)
    out = canvas()
    out.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
    return out


def find_colour(im, rgb, tol=26):
    """Bounding box of pixels near `rgb` -- used to locate the flagged row in
    the candidate table instead of hard-coding a pixel offset that would break
    the moment the screenshot is regenerated."""
    px = im.convert("RGB").load()
    xs, ys = [], []
    for y in range(0, im.height, 2):
        for x in range(0, im.width, 2):
            r, g, b = px[x, y]
            if abs(r-rgb[0]) < tol and abs(g-rgb[1]) < tol and abs(b-rgb[2]) < tol:
                xs.append(x); ys.append(y)
    if not xs:
        return None
    return min(xs), min(ys), max(xs), max(ys)


# ------------------------------------------------------------------ the cards
def card_title():
    Image, ImageDraw, _ = _img()
    im = canvas(); d = ImageDraw.Draw(im)
    f1, f2 = font(F_BOLD, 96), font(F_REG, 34)
    d.text((W/2, H/2 - 60), "NeoFold Edge", font=f1, fill=INK, anchor="mm")
    d.text((W/2, H/2 + 34), "a cancer research lab that never phones home",
           font=f2, fill=MUTED, anchor="mm")
    d.line([(W/2 - 190, H/2 - 4), (W/2 + 190, H/2 - 4)], fill=(48, 54, 61), width=2)
    return im


def card_text(lines: list[tuple[str, str]]):
    """Big/small pairs, stacked and centred."""
    Image, ImageDraw, _ = _img()
    im = canvas(); d = ImageDraw.Draw(im)
    fb, fs = font(F_BOLD, 62), font(F_REG, 30)
    blocks = []
    for big, small in lines:
        blocks.append((wrap(d, big, fb, W - 400), fb, INK, 78))
        if small:
            blocks.append((wrap(d, small, fs, W - 500), fs, MUTED, 42))
    total = sum(len(ls) * step for ls, _, _, step in blocks) + 30 * (len(lines) - 1)
    y = H / 2 - total / 2
    for ls, f, col, step in blocks:
        for ln in ls:
            d.text((W/2, y), ln, font=f, fill=col, anchor="ma")
            y += step
        y += 16
    return im


def card_stat(value: str, label: str, sub: str = "", colour=ACCENT):
    Image, ImageDraw, _ = _img()
    im = canvas(); d = ImageDraw.Draw(im)
    fv, fl, fsub = font(F_BOLD, 200), font(F_REG, 42), font(F_REG, 28)
    d.text((W/2, H/2 - 70), value, font=fv, fill=colour, anchor="mm")
    d.text((W/2, H/2 + 80), label, font=fl, fill=INK, anchor="mm")
    if sub:
        for i, ln in enumerate(wrap(d, sub, fsub, W - 600)):
            d.text((W/2, H/2 + 145 + i * 38), ln, font=fsub, fill=MUTED, anchor="ma")
    return im


def card_close():
    Image, ImageDraw, _ = _img()
    im = canvas(); d = ImageDraw.Draw(im)
    f1, f2, f3 = font(F_BOLD, 66), font(F_MONO, 30), font(F_REG, 25)
    for i, ln in enumerate(["A cancer research lab that fits on a desk.",
                            "And never phones home."]):
        d.text((W/2, H/2 - 150 + i * 88), ln, font=f1, fill=INK, anchor="ma")
    d.text((W/2, H/2 + 90), "github.com/nitishsjsucs/neofold-edge",
           font=f2, fill=ACCENT, anchor="mm")
    d.text((W/2, H/2 + 170),
           "Research prioritisation only. Every value is a prediction, not a measurement.",
           font=f3, fill=(250, 178, 25), anchor="mm")
    d.text((W/2, H - 70), "HP ZGX Nano  ·  NVIDIA GB10  ·  fully offline",
           font=f3, fill=MUTED, anchor="mm")
    return im


# --------------------------------------------------------------- the shot list
def build_shots(scenes: list[dict]) -> dict[str, list[dict]]:
    """Each shot: {kind, ...}. `still` holds a full frame; `pan` holds a source
    image plus start/end crop boxes so the frame generator can interpolate."""
    from PIL import Image

    cand = Image.open(IMG / "candidates.png").convert("RGB")
    # The flagged row is located by the colour of its "self peptide" pill text
    # (#f0879b) rather than a fixed offset.
    box = find_colour(cand, (240, 135, 155))
    if box:
        x0, y0, x1, y1 = box
        cy = (y0 + y1) / 2
        row = (0, max(0, cy - 90), cand.width, min(cand.height, cy + 90))
    else:                                   # fall back to the lower table area
        row = (0, cand.height * 0.72, cand.width, cand.height * 0.86)

    dash = Image.open(IMG / "dashboard.png").convert("RGB")
    struct = Image.open(IMG / "structure.png").convert("RGB")

    return {
        "hook": [
            {"kind": "still", "im": card_title, "motion": "breathe"},
            {"kind": "still", "im": lambda: card_text([
                ("Rosie, five years old.", "Terminal mast cell tumour."),
                ("Her owner had never studied biology.",
                 "He sequenced her tumour, used AI to pick the targets, "
                 "and designed her a vaccine."),
            ]), "motion": "breathe"},
            {"kind": "still", "im": lambda: card_stat(
                "75%", "her largest tumour shrank",
                "One dog, not a controlled study — and given alongside a "
                "checkpoint inhibitor. But the workflow is real.", GOOD),
             "motion": "breathe"},
        ],
        "question": [{"kind": "svg", "name": "governance", "motion": "slow-in"}],
        "problem": [
            {"kind": "svg", "name": "gates", "motion": "slow-in"},
            {"kind": "still", "im": lambda: card_stat(
                "6%", "of the best candidates ever tested actually worked",
                "608 peptides nominated by 25 expert pipelines. 37 were "
                "immunogenic. (TESLA, Cell 2020)", BAD), "motion": "breathe"},
        ],
        "build": [
            {"kind": "svg", "name": "pipeline", "motion": "drift-down"},
            {"kind": "pan", "src": dash,
             "a": (0, 0, dash.width, dash.width * H / W),
             "b": (0, dash.height - dash.width * H / W, dash.width, dash.height)},
        ],
        # The slow push onto the flagged row, with the highlight fading in late.
        "wow": [{"kind": "pan", "src": cand,
                 "a": (0, 0, cand.width, cand.width * H / W),
                 "b": row, "highlight": True, "ease": "in-out"}],
        "nano": [{"kind": "svg", "name": "hardware", "motion": "slow-in"}],
        "proof": [
            {"kind": "pan", "src": struct,
             "a": (0, 0, struct.width, struct.width * H / W),
             "b": (0, struct.height * 0.55, struct.width,
                   struct.height * 0.55 + struct.width * H / W)},
            {"kind": "svg", "name": "timeline", "motion": "slow-in"},
        ],
        "close": [{"kind": "still", "im": card_close, "motion": "breathe"}],
    }


def ease_in_out(t: float) -> float:
    return t * t * (3 - 2 * t)


def crop_lerp(src, a, b, t, highlight=False, hl_alpha=0.0):
    """Interpolate between two crop boxes and scale the result to the frame."""
    from PIL import Image, ImageDraw
    box = tuple(a[i] + (b[i] - a[i]) * t for i in range(4))
    box = (max(0, box[0]), max(0, box[1]),
           min(src.width, box[2]), min(src.height, box[3]))
    if box[2] - box[0] < 8 or box[3] - box[1] < 8:
        box = a
    im = src.crop(tuple(int(v) for v in box))
    # Preserve aspect: pad the crop to 16:9 before the resize.
    want = W / H
    have = im.width / max(1, im.height)
    if abs(have - want) > 0.01:
        if have > want:
            nh = int(im.width / want); pad = Image.new("RGB", (im.width, nh), BG)
            pad.paste(im, (0, (nh - im.height) // 2))
        else:
            nw = int(im.height * want); pad = Image.new("RGB", (nw, im.height), BG)
            pad.paste(im, ((nw - im.width) // 2, 0))
        im = pad
    im = im.resize((W, H), Image.LANCZOS)
    if highlight and hl_alpha > 0:
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        a_ = int(210 * hl_alpha)
        # Dim everything but a band across the middle, then outline the band.
        d.rectangle([0, 0, W, int(H * 0.36)], fill=(13, 17, 23, a_))
        d.rectangle([0, int(H * 0.64), W, H], fill=(13, 17, 23, a_))
        d.rectangle([int(W * 0.03), int(H * 0.37), int(W * 0.97), int(H * 0.63)],
                    outline=(248, 81, 73, int(255 * hl_alpha)), width=4)
        im = Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")
    return im


def shot_frame(shot, t: float, cache: dict):
    """One frame of a shot, t in [0,1]."""
    from PIL import Image
    kind = shot["kind"]
    if kind in ("still", "svg"):
        key = id(shot)
        if key not in cache:
            cache[key] = (fit(rasterise_svg(shot["name"], 1600), pad=70)
                          if kind == "svg" else shot["im"]())
        base = cache[key]
        m = shot.get("motion", "breathe")
        # Gentle motion so a static card does not look like a frozen stream.
        if m == "breathe":
            sc = 1.0 + 0.020 * t
        elif m == "slow-in":
            sc = 1.0 + 0.035 * ease_in_out(t)
        else:                                    # drift-down
            sc = 1.03
        nw, nh = int(W * sc), int(H * sc)
        im = base.resize((nw, nh), Image.LANCZOS)
        if m == "drift-down":
            oy = int((nh - H) * t)
        else:
            oy = (nh - H) // 2
        return im.crop(((nw - W) // 2, oy, (nw - W) // 2 + W, oy + H))

    tt = ease_in_out(t) if shot.get("ease") == "in-out" else t
    hl = 0.0
    if shot.get("highlight"):
        hl = max(0.0, min(1.0, (t - 0.55) / 0.22))     # fades in late
    return crop_lerp(shot["src"], shot["a"], shot["b"], tt,
                     highlight=shot.get("highlight", False), hl_alpha=hl)


# ------------------------------------------------------------------- encoding
def render_video(scenes: list[dict], shots: dict, dest: pathlib.Path) -> None:
    from PIL import Image
    proc = subprocess.Popen(
        [ffmpeg(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0",
         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
         "-pix_fmt", "yuv420p", str(dest)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    cache: dict = {}
    prev = None                      # last frame, for crossfading across cuts
    xf = int(XFADE * FPS)
    written = 0

    for s in scenes:
        sl = shots[s["id"]]
        n_total = max(1, int(round(s["dur"] * FPS)))
        per = [n_total // len(sl)] * len(sl)
        per[-1] += n_total - sum(per)

        for shot, n in zip(sl, per):
            for i in range(n):
                f = shot_frame(shot, i / max(1, n - 1), cache)
                if prev is not None and i < xf:
                    f = Image.blend(prev, f, (i + 1) / xf)
                proc.stdin.write(f.tobytes())
                written += 1
            prev = shot_frame(shot, 1.0, cache)
        print(f"  {s['id']:10} {n_total:5d} frames  ({s['dur']:.1f}s)")

    # Fade to black over the final second rather than cutting hard.
    for i in range(FPS):
        proc.stdin.write(Image.blend(prev, canvas(), (i + 1) / FPS).tobytes())
        written += 1
    proc.stdin.close()
    proc.wait()
    print(f"  {'video':10} {written:5d} frames  ({written / FPS:.1f}s)")


def mux(video: pathlib.Path, audio: pathlib.Path, dest: pathlib.Path) -> None:
    subprocess.run(
        [ffmpeg(), "-y", "-i", str(video), "-i", str(audio),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",      # broadcast-ish levelling
         "-shortest", "-movflags", "+faststart", str(dest)],
        check=True, capture_output=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", help="re-render one scene's audio only")
    ap.add_argument("--audio-only", action="store_true")
    a = ap.parse_args()

    if not shutil.which("piper"):
        sys.exit("piper not on PATH -- activate ~/media-venv")
    OUT.mkdir(parents=True, exist_ok=True)

    scenes = parse_narration()
    if a.scene:
        scenes = [s for s in scenes if s["id"] == a.scene] or sys.exit("no such scene")

    print("narration:")
    render_audio(scenes)
    if a.audio_only or a.scene:
        return

    print("audio track:")
    track = concat_audio(scenes)
    print(f"  {track.name}")

    print("frames:")
    shots = build_shots(scenes)
    silent = OUT / "silent.mp4"
    render_video(scenes, shots, silent)

    dest = ROOT / "video" / "neofold-edge-demo.mp4"
    mux(silent, track, dest)
    mb = dest.stat().st_size / 1e6
    print(f"\nwrote {dest.relative_to(ROOT)}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
