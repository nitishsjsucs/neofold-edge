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
sys.path.insert(0, str(ROOT / "scripts"))
IMG = ROOT / "docs" / "img"
OUT = ROOT / "video" / "build"
VOICES = pathlib.Path.home() / "voices"

from video_theme import FPS, H, SCENE_XFADE, W          # noqa: E402

# Kokoro (82M, StyleTTS2 + ISTFTNet). Better prosody than Piper: it stresses
# the operative word and reads punctuation as phrasing.
VOICE = "af_heart"
SPEED = 1.04                       # ~166 wpm, just above Guo's engagement dip
KOKORO_DIR = pathlib.Path.home() / "voices" / "kokoro"


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


_KOKORO = None


def kokoro():
    global _KOKORO
    if _KOKORO is None:
        from kokoro_onnx import Kokoro
        _KOKORO = Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"),
                         str(KOKORO_DIR / "voices-v1.0.bin"))
    return _KOKORO


def render_audio(scenes: list[dict]) -> None:
    import soundfile as sf

    OUT.mkdir(parents=True, exist_ok=True)
    k = kokoro()
    for s in scenes:
        wav = OUT / f"vo-{s['id']}.wav"
        audio, sr = k.create(s["text"], voice=VOICE, speed=SPEED, lang="en-us")
        sf.write(str(wav), audio, sr)
        s["dur"] = len(audio) / sr
        print(f"  {s['id']:10} {s['dur']:5.1f}s  {s['text'][:56]}…")
    total = sum(s["dur"] for s in scenes)
    print(f"  {'TOTAL':10} {total:5.1f}s  ({int(total//60)}:{int(total%60):02d})")


def write_cues(scenes: list[dict], gap: float) -> pathlib.Path:
    """Scene start times, so the score can be cued to the edit rather than
    merely laid under it."""
    import json
    out, at = {}, 0.0
    for s in scenes:
        out[s["id"]] = {"start": round(at, 3), "dur": round(s["dur"], 3)}
        at += s["dur"] + gap
    path = OUT / "cues.json"
    path.write_text(json.dumps({"scenes": out, "total": round(at, 3)}, indent=2))
    return path


def make_music(cues: pathlib.Path) -> pathlib.Path:
    dest = OUT / "music.wav"
    subprocess.run([sys.executable, str(ROOT / "scripts" / "make_music.py"),
                    str(cues), str(dest)], check=True)
    return dest


def concat_audio(scenes: list[dict]) -> pathlib.Path:
    """One narration track, with a short beat of silence between scenes."""
    lst = OUT / "audio.txt"
    gap = OUT / "gap.wav"
    subprocess.run([ffmpeg(), "-y", "-f", "lavfi", "-i",
                    "anullsrc=r=24000:cl=mono", "-t", "0.35", str(gap)],
                   check=True, capture_output=True)
    parts = []
    for s in scenes:
        clip = OUT / ("vo-" + s["id"] + ".wav")
        parts += [f"file '{clip}'", f"file '{gap}'"]
    lst.write_text("\n".join(parts) + "\n")
    track = OUT / "narration.wav"
    subprocess.run([ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(track)], check=True, capture_output=True)
    return track


# -------------------------------------------------------------------- visuals
sys.path.insert(0, str(ROOT / "scripts"))


def scene_frame(sid: str, t_s: float, dur: float, text: str):
    """One frame. No drift push and no global time-warp: a capture is pasted
    1:1 and held, and its markers are timed from the narration itself."""
    import video_scenes as vs
    return vs.SCENES[sid](t_s, dur, text)


# ------------------------------------------------------------------- encoding
def render_video(scenes: list[dict], dest: pathlib.Path) -> None:
    from PIL import Image
    from video_anim import canvas

    proc = subprocess.Popen(
        [ffmpeg(), "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(FPS), "-i", "pipe:0",
         "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", str(dest)],
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    prev, written = None, 0
    xf = int(SCENE_XFADE * FPS)
    for s in scenes:
        n = max(1, int(round(s["dur"] * FPS)))
        for i in range(n):
            f = scene_frame(s["id"], i / FPS, s["dur"], s["text"])
            if prev is not None and i < xf:
                f = Image.blend(prev, f, (i + 1) / xf)
            proc.stdin.write(f.tobytes())
            written += 1
        prev = f
        print(f"  {s['id']:10} {n:5d} frames  ({s['dur']:.1f}s)")

    for i in range(FPS):
        proc.stdin.write(Image.blend(prev, canvas(), (i + 1) / FPS).tobytes())
        written += 1
    proc.stdin.close(); proc.wait()
    print(f"  {'video':10} {written:5d} frames  ({written / FPS:.1f}s)")


def mux(video: pathlib.Path, vo: pathlib.Path, music: pathlib.Path | None,
        dest: pathlib.Path) -> None:
    """Narration on top, score underneath and sidechain-ducked by it, so the
    music opens up between sentences instead of fighting them."""
    if music is None:
        fc = ("[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,"
              "pan=stereo|c0=c0|c1=c0[a]")
        ins = [ffmpeg(), "-y", "-i", str(video), "-i", str(vo)]
    else:
        fc = ("[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,asplit=2[vo][key];"
              "[2:a]volume=0.42[mu];"
              "[mu][key]sidechaincompress=threshold=0.03:ratio=9:"
              "attack=8:release=420:makeup=1[duck];"
              "[vo][duck]amix=inputs=2:duration=longest:normalize=0,"
              "alimiter=limit=0.95,aresample=48000,"
              "pan=stereo|c0=c0|c1=c0[a]")
        ins = [ffmpeg(), "-y", "-i", str(video), "-i", str(vo), "-i", str(music)]
    subprocess.run(
        ins + ["-filter_complex", fc, "-map", "0:v", "-map", "[a]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
               "-ar", "48000", "-ac", "2",
               "-shortest", "-movflags", "+faststart", str(dest)],
        check=True, capture_output=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scene", help="re-render one scene's audio only")
    ap.add_argument("--audio-only", action="store_true")
    ap.add_argument("--remux", action="store_true",
                    help="rebuild audio and re-mux onto the existing frames")
    a = ap.parse_args()

    if not (KOKORO_DIR / "kokoro-v1.0.onnx").exists():
        sys.exit(f"kokoro model missing under {KOKORO_DIR}")
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
    print("score:")
    cues = write_cues(scenes, gap=0.35)
    music = make_music(cues)

    print("cues:")
    import video_plates as vp
    import video_scenes as vs
    for s in scenes:
        if s["id"] not in vs.CUES:
            continue
        capture, cues = vs.CUES[s["id"]]
        resolved = vp.plan([dict(c, scale=vp.pick_scale(capture, c["region"]))
                            for c in cues], s["text"], s["dur"])
        print(vp.describe(s["id"], resolved, s["dur"]))

    silent = OUT / "silent.mp4"
    if a.remux:
        if not silent.exists():
            sys.exit("no rendered frames yet -- run a full build first")
        print("frames:\n  reusing silent.mp4")
    else:
        print("frames:")
        render_video(scenes, silent)

    dest = ROOT / "video" / "neofold-edge-demo.mp4"
    mux(silent, track, music, dest)
    mb = dest.stat().st_size / 1e6
    print(f"\nwrote {dest.relative_to(ROOT)}  ({mb:.1f} MB)")


if __name__ == "__main__":
    main()
