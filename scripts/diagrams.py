"""Generate the README diagrams as SVG, in light and dark variants.

Mermaid renders these fine but renders them plainly: its node sizing, type
scale and spacing are fixed, edge labels land in grey slabs, and there is no
way to express a timing badge or a de-emphasised branch. These are the hero
visuals of the README, so they are laid out by hand instead.

Everything uses presentation attributes rather than CSS, because GitHub's
markdown sanitiser strips <style> blocks from inline SVG. Fonts are a system
stack for the same reason -- no webfont will load.

    python3 scripts/diagrams.py        # -> docs/img/diagram-*.{light,dark}.svg
"""
from __future__ import annotations

import pathlib
from xml.sax.saxutils import escape

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "img"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"

# Two palettes. The dark one is tuned against GitHub's #0d1117 canvas, the
# light one against #ffffff -- the same contrast problem the app's pLDDT bands
# had, so the fills are not shared between them.
THEMES = {
    "light": dict(
        bg="#ffffff", ink="#1f2328", muted="#636c76", line="#d0d7de", arrow="#8c959f",
        data=("#f6f8fa", "#afb8c1"), cpu=("#dafbe1", "#2da44e"), gpu=("#eae5ff", "#8250df"),
        out=("#fff1e5", "#bc4c00"), cut=("#ffebe9", "#cf222e"), accent="#0969da",
        band=("#f6f8fa", "#d0d7de"),
    ),
    "dark": dict(
        bg="#0d1117", ink="#e6edf3", muted="#8b949e", line="#30363d", arrow="#6e7681",
        data=("#21262d", "#484f58"), cpu=("#0f2e21", "#2ea043"), gpu=("#241d3d", "#a371f7"),
        out=("#3a1d0d", "#db6d28"), cut=("#3d1519", "#f85149"), accent="#58a6ff",
        band=("#161b22", "#30363d"),
    ),
}


class Canvas:
    def __init__(self, w: int, h: int, t: dict):
        self.w, self.h, self.t = w, h, t
        self.parts: list[str] = []

    def rect(self, x, y, w, h, fill, stroke, r=10, sw=1.25, dash=None, op=1.0):
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" ry="{r}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"{d}/>')

    def text(self, x, y, s, size=13, fill=None, weight=400, anchor="middle",
             mono=False, op=1.0, ls=0.0):
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="{MONO if mono else FONT}" '
            f'font-size="{size}" font-weight="{weight}" fill="{fill or self.t["ink"]}" '
            f'text-anchor="{anchor}" opacity="{op}" letter-spacing="{ls}" '
            f'dominant-baseline="middle">{escape(s)}</text>')

    def node(self, x, y, w, h, kind, title, lines=(), badge=None, faded=False):
        """A titled box. `lines` are muted detail rows; `badge` is a timing pill."""
        fill, stroke = self.t[kind]
        op = 0.55 if faded else 1.0
        self.rect(x, y, w, h, fill, stroke, op=op)
        n = len(lines)
        # Centre the whole text block, then walk down it.
        cy = y + h / 2 - (n * 15) / 2 + (7 if n else 0)
        self.text(x + w / 2, cy, title, size=13.5, weight=650, op=op)
        for i, ln in enumerate(lines):
            self.text(x + w / 2, cy + 18 + i * 15, ln, size=11.5,
                      fill=self.t["muted"], op=op)
        if badge:
            bw = 8 + len(badge) * 6.6
            bx = x + w - bw - 10
            self.rect(bx, y + 8, bw, 17, self.t["band"][0], self.t["band"][1], r=8, sw=1)
            self.text(bx + bw / 2, y + 17, badge, size=10, mono=True,
                      fill=self.t["muted"])

    def arrow(self, x1, y1, x2, y2, dash=None, colour=None, label=None):
        c = colour or self.t["arrow"]
        d = f' stroke-dasharray="{dash}"' if dash else ""
        # Stop short of the target so the head is not buried in the box edge.
        dx, dy = x2 - x1, y2 - y1
        L = max(1e-6, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / L, dy / L
        ex, ey = x2 - ux * 9, y2 - uy * 9
        self.parts.append(
            f'<path d="M {x1} {y1} L {ex} {ey}" stroke="{c}" stroke-width="1.6" '
            f'fill="none" stroke-linecap="round"{d}/>')
        px, py = -uy, ux
        self.parts.append(
            f'<path d="M {x2} {y2} L {ex + px*4.6} {ey + py*4.6} '
            f'L {ex - px*4.6} {ey - py*4.6} Z" fill="{c}"/>')
        if label:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            self.text(mx + px * 13, my + py * 13, label, size=10.5,
                      fill=self.t["muted"])

    def elbow(self, x1, y1, x2, y2, dash=None, colour=None):
        """Down, across, then into the target from above."""
        c = colour or self.t["arrow"]
        d = f' stroke-dasharray="{dash}"' if dash else ""
        mid = y1 + (y2 - y1) / 2
        self.parts.append(
            f'<path d="M {x1} {y1} L {x1} {mid} L {x2} {mid} L {x2} {y2 - 9}" '
            f'stroke="{c}" stroke-width="1.6" fill="none" stroke-linejoin="round" '
            f'stroke-linecap="round"{d}/>')
        self.parts.append(
            f'<path d="M {x2} {y2} L {x2 - 4.6} {y2 - 9} L {x2 + 4.6} {y2 - 9} Z" fill="{c}"/>')

    def caption(self, x, y, s, size=11, anchor="middle", mono=False):
        self.text(x, y, s, size=size, fill=self.t["muted"], anchor=anchor, mono=mono)

    def render(self) -> str:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'role="img">\n'
                f'<rect width="{self.w}" height="{self.h}" fill="{self.t["bg"]}"/>\n'
                + "\n".join(self.parts) + "\n</svg>\n")


def emit(name: str, build) -> None:
    for variant, theme in THEMES.items():
        c = build(theme)
        path = OUT / f"diagram-{name}.{variant}.svg"
        path.write_text(c.render())
    print(f"  diagram-{name}.{{light,dark}}.svg")


# --------------------------------------------------------------- 1. overview
def overview(t):
    c = Canvas(900, 150, t)
    y, h = 30, 92
    c.node(20, y, 250, h, "data", "Tumour variant file",
           ["what the sequencer gives you", "50 mutations"])
    c.node(325, y, 250, h, "gpu", "NeoFold Edge",
           ["one desk-side box", "offline · 38 W"])
    c.node(630, y, 250, h, "cpu", "Ranked shortlist",
           ["with the evidence for each", "5 candidates"])
    c.arrow(270, y + h / 2, 325, y + h / 2)
    c.arrow(575, y + h / 2, 630, y + h / 2)
    return c


# ------------------------------------------------------------------ 2. gates
def gates(t):
    c = Canvas(980, 200, t)
    steps = [
        ("1 · Mutation", ["the typo happens"], "data"),
        ("2 · Protein", ["the typo", "gets printed"], "data"),
        ("3 · Processing", ["the page is", "shredded"], "data"),
        ("4 · Presentation", ["a shred is pinned", "to the noticeboard"], "cpu"),
        ("5 · Recognition", ["a guard walks", "past and reads it"], "out"),
    ]
    w, gap, y, h = 168, 22, 34, 96
    for i, (title, lines, kind) in enumerate(steps):
        x = 14 + i * (w + gap)
        c.node(x, y, w, h, kind, title, lines)
        if i:
            c.arrow(x - gap, y + h / 2, x, y + h / 2)
    c.caption(14 + 3 * (w + gap) + w / 2, y + h + 20, "our screen predicts this")
    c.caption(14 + 3 * (w + gap) + w / 2, y + h + 37, "AUC 0.777")
    c.caption(14 + 4 * (w + gap) + w / 2, y + h + 20, "not in any")
    c.caption(14 + 4 * (w + gap) + w / 2, y + h + 37, "training data")
    return c


# ------------------------------------------------------------- 3. governance
def governance(t):
    steps = ["Tumour + normal sequencing data", "Data Use Certification",
             "Data Access Committee review", "Institutional signing official",
             "Business Associate Agreement", "Transfer", "Inference",
             "Vendor now holds an identifiable genome"]
    h, gap, top = 50, 18, 62
    # Height follows the step count rather than a guessed constant -- the
    # previous hard-coded 560 clipped the last node and sat a caption on top
    # of another one.
    boxh = top + len(steps) * (h + gap) - gap + 18
    c = Canvas(900, boxh + 66, t)

    c.rect(14, 14, 420, boxh, t["band"][0], t["cut"][1], r=14, sw=1.25)
    c.text(224, 42, "Cloud — the file has to leave the building",
           size=13.5, weight=650, fill=t["cut"][1])
    y = top
    for i, s in enumerate(steps):
        c.node(34, y, 380, h, "cut" if 1 <= i <= 4 else "data", s)
        if i:
            c.arrow(224, y - gap, 224, y)
        y += h + gap
    c.caption(224, boxh + 40, "four of these are weeks, not paperwork")

    c.rect(466, 14, 420, boxh, t["band"][0], t["cpu"][1], r=14, sw=1.25)
    c.text(676, 42, "NeoFold Edge — the file never moves",
           size=13.5, weight=650, fill=t["cpu"][1])
    c.node(486, top, 380, h, "data", "Tumour + normal sequencing data")
    c.arrow(676, top + h + 2, 676, top + h + gap + 2)
    c.node(486, top + h + gap + 2, 380, 88, "gpu", "Inference",
           ["on the institution's own device", "air-gapped, 38 W"])
    yy = top + h + gap + 90 + 2
    c.arrow(676, yy, 676, yy + gap)
    c.node(486, yy + gap, 380, h, "cpu", "Shortlist")
    c.caption(676, yy + gap + h + 34, "no disclosure to approve,")
    c.caption(676, yy + gap + h + 52, "so there is no step to approve it")
    c.caption(676, boxh + 40, "one step, on hardware the institution owns")
    return c


# ---------------------------------------------------------------- 4. pipeline
def pipeline(t):
    x, w, h, gap = 250, 380, 62, 24
    c = Canvas(880, 22 + 8 * (h + 10 + gap) + 34, t)
    rows = [
        ("data", "Tumour variant file", ["VCF · 50 variants"], None),
        ("data", "Peptide windows", ["1,890 candidates"], None),
        ("cpu", "Self-similarity filter", ["20,431 human proteins"], "CPU"),
        ("cpu", "MHC binding screen", ["MHCflurry → 22 presented"], "8.8 s"),
        ("gpu", "Structure prediction", ["Boltz-2 → top 5"], "64 s"),
        ("gpu", "Evidence layer", ["contact · dynamics · TCR"], "GB10"),
        ("gpu", "Local summary", ["qwen3:8b, verified"], "4 s"),
        ("out", "Construct assembly", ["exhaustive junction search"], None),
    ]
    y = 22
    ys = []
    for i, (kind, title, lines, badge) in enumerate(rows):
        hh = h + (10 if lines else 0)
        c.node(x, y, w, hh, kind, title, lines, badge=badge)
        ys.append((y, hh))
        if i:
            py, ph = ys[i - 1]
            c.arrow(x + w / 2, py + ph, x + w / 2, y)
        y += hh + gap
    # The rejected branch is a real terminal node, not an invisible one.
    sy, sh = ys[2]
    c.node(28, sy + 4, 196, 64, "cut", "✕ 13 discarded",
           ["verbatim normal", "human peptides"])
    c.arrow(x, sy + sh / 2, 224, sy + 36)
    c.caption(440, y + 4, "teal = local CPU   ·   purple = GB10 GPU   ·   nothing leaves the box")
    return c


# ---------------------------------------------------------------- 5. timeline
def timeline(t):
    c = Canvas(920, 300, t)
    stages = [("Screen", "1,890 peptides", "8.8 s", "cpu", 8.8),
              ("Fold", "383 residues", "64 s", "gpu", 64.0),
              ("Evidence", "contact + MD", "~20 s", "gpu", 20.0),
              ("Explain", "qwen3:8b", "4 s", "gpu", 4.0)]
    total = sum(s[4] for s in stages)
    x0, x1, y, bh = 40, 880, 118, 52
    span = x1 - x0

    c.text(460, 40, "One run, end to end", size=14, weight=650)
    c.caption(460, 62, "segment width is proportional to measured wall time")

    # A stacked bar: labelling inside the segments fails at 4 s of 97, so the
    # names live in the legend below and the bar stays honest about width.
    x = x0
    for i, (name, sub, badge, kind, secs) in enumerate(stages):
        w = span * secs / total
        fill, stroke = t[kind]
        r = 0
        c.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{bh}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.25"/>')
        if w > 90:
            c.text(x + w / 2, y + bh / 2, badge, size=12.5, weight=650, mono=True)
        x += w
    c.parts.append(
        f'<path d="M {x0} {y + bh + 16} L {x1} {y + bh + 16}" '
        f'stroke="{t["line"]}" stroke-width="1"/>')
    c.caption(x0, y + bh + 32, "0 s", anchor="start", mono=True)
    c.caption(x1, y + bh + 32, "≈ 97 s", anchor="end", mono=True)

    # Legend: one row, four entries, each a swatch + name + detail + time.
    lx, ly = x0, y + bh + 70
    colw = span / 4
    for i, (name, sub, badge, kind, secs) in enumerate(stages):
        fill, stroke = t[kind]
        cx = lx + i * colw
        c.rect(cx, ly - 6, 11, 11, fill, stroke, r=3, sw=1.25)
        c.text(cx + 19, ly, name, size=12.5, weight=650, anchor="start")
        c.text(cx + 19, ly + 17, f"{sub} · {badge}", size=11,
               fill=t["muted"], anchor="start")
    c.caption(460, y - 22,
              "a tumour producing 22 candidates is ~13 minutes of GPU time")
    return c


# ---------------------------------------------------------------- 6. hardware
def hardware(t):
    c = Canvas(900, 400, t)
    c.rect(200, 60, 680, 300, t["band"][0], t["gpu"][1], r=14, sw=1.25)
    c.text(540, 88, "HP ZGX Nano · one device · 38 W peak · fits in a cupboard",
           size=13.5, weight=650, fill=t["gpu"][1])
    c.node(226, 112, 200, 106, "data", "20-core Arm",
           ["Cortex-X925 ×10", "Cortex-A725 ×10"])
    c.node(444, 112, 196, 106, "cpu", "128 GB LPDDR5x",
           ["coherent unified", "273 GB/s"])
    c.node(658, 112, 198, 106, "gpu", "Blackwell GPU",
           ["53.4 TFLOPS bf16", "96% util · 46 °C"])
    c.arrow(426, 165, 444, 165)
    c.arrow(640, 165, 658, 165)
    c.caption(540, 250, "one coherent memory pool — the folding model, the reference")
    c.caption(540, 268, "proteome and the candidate set all resident at once")
    c.caption(540, 300, "on a 24 GB consumer card you work through a letterbox")

    jobs = [("Screen", "8.8 s"), ("Boltz-2", "64 s"), ("OpenMM", "4 fs HMR"),
            ("qwen3:8b", "100% GPU")]
    for i, (nm, sub) in enumerate(jobs):
        y = 74 + i * 74
        c.node(14, y, 150, 58, "data", nm, [sub])
        c.arrow(164, y + 29, 200, y + 29)
    return c


# ----------------------------------------------------------------- 7. scaling
def scaling(t):
    c = Canvas(880, 290, t)
    c.node(20, 86, 190, 92, "data", "Work queue",
           ["candidates are", "independent jobs"])
    nodes = [("Nano 1", "100 / hr", "measured", False),
             ("Nano 2", "~200 / hr", "projection", True),
             ("Nano 4", "~400 / hr", "projection", True)]
    for i, (nm, rate, note, proj) in enumerate(nodes):
        y = 22 + i * 72
        c.node(400, y, 200, 60, "cut" if False else ("data" if proj else "cpu"),
               nm, [rate], faded=proj)
        c.arrow(210, 132, 400, y + 30, dash="6 4" if proj else None)
        c.caption(620, y + 30, note, anchor="start")
    c.caption(440, 262, "we had one Nano — every multi-node figure is labelled a projection")
    return c


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    print("writing diagrams to docs/img ...")
    for name, fn in [("overview", overview), ("gates", gates),
                     ("governance", governance), ("pipeline", pipeline),
                     ("timeline", timeline), ("hardware", hardware),
                     ("scaling", scaling)]:
        emit(name, fn)
    print("done.")
