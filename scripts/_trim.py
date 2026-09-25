"""Trim uniform margins from a screenshot, then cap its width.

Headless Chrome renders a fixed window, so a panel shorter than the window
leaves a band of dead background at the bottom. Cropping to content is more
reliable than hand-tuning a window height per figure.

Dev-only helper for scripts/screenshots.sh; Pillow is not an app dependency.
"""
import sys
from PIL import Image

MAX_W = 1600
PAD = 16


def trim(path: str) -> None:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    bg = im.getpixel((w - 2, h - 2))          # bottom-right is always page bg

    # Walk up while rows stay within a hair of the background colour. JPEG-free
    # PNGs are exact, but the tolerance costs nothing and survives dithering.
    px = im.load()
    def uniform(y: int) -> bool:
        return all(abs(px[x, y][c] - bg[c]) <= 2
                   for x in range(0, w, max(1, w // 160)) for c in range(3))

    bottom = h
    while bottom > 1 and uniform(bottom - 1):
        bottom -= 1
    bottom = min(h, bottom + PAD)

    right = w
    while right > 1 and all(abs(px[right - 1, y][c] - bg[c]) <= 2
                            for y in range(0, bottom, max(1, bottom // 160))
                            for c in range(3)):
        right -= 1
    right = min(w, right + PAD)

    if bottom < h or right < w:
        im = im.crop((0, 0, right, bottom))
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    im.save(path, optimize=True)
    print(f"  {path.rsplit('/', 1)[-1]:26} {im.width}x{im.height}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        trim(p)
