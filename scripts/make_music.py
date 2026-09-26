"""Synthesise an original score for the demo video, cued to the scene timings.

WHY SYNTHESISED RATHER THAN A STOCK TRACK. A library cue would need a licence
we do not have, and anything scraped off the internet is not ours to ship in a
public repo. This is additive synthesis from scratch -- every sample computed
here -- so the music is original, licence-free, and generated on the Nano like
everything else in the film.

It is also cued: the score is built FROM the measured narration lengths, so the
swell lands on the reveal instead of near it.

    python scripts/make_music.py video/build/cues.json video/build/music.wav
"""
from __future__ import annotations

import json
import pathlib
import sys
import wave

import numpy as np

SR = 44100
A1 = 55.0                                  # the drone root, A1

# Semitone offsets from A for the chords we use. A natural-minor palette:
# sparse and unresolved early, resolving only at the close.
CHORDS = {
    "Am":  [0, 3, 7],
    "F":   [-4, 0, 3],
    "C":   [3, 7, 10],
    "Dm":  [5, 8, 12],
    "G":   [-2, 2, 5],
    "Em":  [7, 10, 14],
}


def n2f(semis: float, octave: int = 0) -> float:
    return A1 * (2 ** (semis / 12.0)) * (2 ** octave)


def env(n: int, a: float, d: float, s: float, r: float, peak=1.0, sus=0.7):
    """ADSR over n samples, times in seconds."""
    ai, di, ri = int(a * SR), int(d * SR), int(r * SR)
    si = max(0, n - ai - di - ri)
    return np.concatenate([
        np.linspace(0, peak, ai, endpoint=False),
        np.linspace(peak, sus * peak, di, endpoint=False),
        np.full(si, sus * peak),
        np.linspace(sus * peak, 0, ri),
    ])[:n]


def pad(freq: float, dur: float, gain=0.2, detune=0.004, partials=4):
    """A slow, breathing pad: detuned sine stack with a gentle tremolo."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for p in range(1, partials + 1):
        for det in (-detune, 0.0, detune):
            f = freq * p * (1 + det)
            if f > SR / 2:
                continue
            out += np.sin(2 * np.pi * f * t + np.random.rand() * 6.28) / (p ** 1.6)
    lfo = 1 + 0.10 * np.sin(2 * np.pi * 0.13 * t)
    return out * lfo * env(n, min(2.2, dur * .35), 0.5, 0, min(2.6, dur * .4)) * gain


def drone(dur: float, gain=0.26):
    """Sub-bass foundation. Slight odd-harmonic colour so it survives on
    phone speakers, which cannot reproduce 55 Hz at all."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    o = (np.sin(2 * np.pi * A1 * t) * 1.0
         + np.sin(2 * np.pi * A1 * 2 * t) * 0.34
         + np.sin(2 * np.pi * A1 * 3 * t) * 0.12)
    o *= 1 + 0.06 * np.sin(2 * np.pi * 0.07 * t)
    return o * env(n, 3.0, 1.0, 0, 3.0) * gain


def pulse(dur: float, bpm=60.0, gain=0.22, accent_every=4):
    """A heartbeat. Quickens where the edit does."""
    n = int(dur * SR)
    out = np.zeros(n)
    beat = 60.0 / bpm
    i = 0
    pos = 0.0
    while pos < dur:
        s = int(pos * SR)
        ln = int(0.22 * SR)
        if s + ln > n:
            break
        t = np.arange(ln) / SR
        f = 48 if i % accent_every == 0 else 42
        hit = np.sin(2 * np.pi * f * t) * np.exp(-t * 16)
        hit += np.sin(2 * np.pi * f * 2.5 * t) * np.exp(-t * 30) * 0.3
        out[s:s + ln] += hit * (1.0 if i % accent_every == 0 else 0.55)
        pos += beat
        i += 1
    return out * gain


def swell(dur: float, gain=0.3):
    """Filtered-noise riser into a hit. The 'here it comes' gesture."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = np.random.randn(n) * 0.5
    # One-pole lowpass whose cutoff rises with time -> a brightening sweep.
    out = np.zeros(n)
    y = 0.0
    for i in range(n):
        cut = 0.0006 + 0.02 * (i / n) ** 2
        y += cut * (noise[i] - y)
        out[i] = y
    out *= (t / dur) ** 2.2
    tone = np.sin(2 * np.pi * np.linspace(n2f(0, 1), n2f(7, 2), n) * t) * (t / dur) ** 3
    return (out * 8 + tone * 0.5) * gain


def impact(gain=0.55):
    """The downbeat under the reveal."""
    n = int(2.6 * SR)
    t = np.arange(n) / SR
    body = (np.sin(2 * np.pi * 42 * t) * np.exp(-t * 2.2)
            + np.sin(2 * np.pi * 63 * t) * np.exp(-t * 3.0) * 0.5)
    crack = np.random.randn(n) * np.exp(-t * 26) * 0.25
    return (body + crack) * gain


def reverb(x, decay=2.4, mix=0.34):
    """Cheap convolution reverb: exponentially decaying noise as the impulse."""
    ln = int(decay * SR)
    ir = np.random.randn(ln) * np.exp(-np.arange(ln) / (decay * SR / 5.5))
    ir[0] = 1.0
    wet = np.convolve(x, ir / np.abs(ir).sum() * 3.0, mode="full")[:len(x)]
    return (1 - mix) * x + mix * wet


def add(buf, sig, at: float):
    s = int(at * SR)
    e = min(len(buf), s + len(sig))
    if e > s:
        buf[s:e] += sig[:e - s]


def compose(cues: dict) -> np.ndarray:
    """cues: {scene_id: {"start": s, "dur": s}} plus "total"."""
    total = cues["total"] + 1.5
    buf = np.zeros(int(total * SR))
    np.random.seed(7)                      # reproducible mixes

    def sc(name):
        return cues["scenes"].get(name)

    # A bed of drone under everything from the first real beat onward.
    hook = sc("hook")
    if hook:
        add(buf, drone(total - hook["start"] - 0.5), hook["start"])

    # Scene-by-scene gestures. Chord choice tracks the argument: unresolved
    # through the problem, moving under the build, minor-major lift at the
    # close where the film finally makes a positive claim.
    plan = [
        ("meta",     "Am", 0.10, None),     # the joke: almost nothing, just air
        ("hook",     "Am", 0.20, None),
        ("question", "F",  0.24, 52),
        ("problem",  "Dm", 0.26, 66),
        ("build",    "C",  0.26, 76),
        ("wow",      "Em", 0.30, None),     # handled specially below
        ("nano",     "Am", 0.24, 72),
        ("proof",    "F",  0.24, None),
        ("close",    "C",  0.30, None),
    ]
    for name, chord, gain, bpm in plan:
        s = sc(name)
        if not s:
            continue
        d = s["dur"]
        for semi in CHORDS[chord]:
            add(buf, pad(n2f(semi, 2), d + 1.2, gain=gain / 3), s["start"])
        if bpm:
            add(buf, pulse(d, bpm=bpm, gain=0.18), s["start"])

    # The reveal: riser into the last third of `wow`, an impact on the line
    # "an exact match to a healthy human protein", then pull back so the
    # voice carries the sentence alone.
    w = sc("wow")
    if w:
        hit_at = w["start"] + w["dur"] * 0.55
        add(buf, swell(min(4.0, w["dur"] * 0.5), gain=0.26), hit_at - min(4.0, w["dur"] * 0.5))
        add(buf, impact(0.5), hit_at)
        # duck the bed for two seconds after the hit
        s0, s1 = int(hit_at * SR), int((hit_at + 2.0) * SR)
        buf[s0:s1] *= np.linspace(0.45, 1.0, max(1, s1 - s0))

    # Final impact under the closing card.
    c = sc("close")
    if c:
        add(buf, impact(0.4), c["start"])

    buf = reverb(buf, decay=2.2, mix=0.30)
    # Soft-clip, then normalise to a conservative peak: this sits UNDER speech.
    buf = np.tanh(buf * 1.15)
    buf /= max(1e-9, np.abs(buf).max())
    return buf * 0.55


def main() -> None:
    cues = json.loads(pathlib.Path(sys.argv[1]).read_text())
    dest = pathlib.Path(sys.argv[2])
    audio = compose(cues)
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(str(dest), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"  {dest.name}  {len(audio)/SR:.1f}s")


if __name__ == "__main__":
    main()
