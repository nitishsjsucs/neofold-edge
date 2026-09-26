# Re-capturing the video's UI screenshots, and re-measuring their regions

The demo video never aims a pointer by eye. Every callout is placed from a measured
`getBoundingClientRect`, normalised to a fraction of the capture, and stored in
`video/app-regions.json`. `scripts/video_plates.py` asserts the region a cue names exists
before it renders, so a missing or stale region fails the build instead of producing a
pointer aimed at nothing.

That means **the capture and the measurement are one operation.** If you re-capture at a
different viewport, you must re-measure, or the build will fail (best case) or point at the
wrong element (only possible if you also hand-edit the JSON — don't).

The three captures, and what they are:

| File | Viewport (CSS px) | Pixels | Regions |
|---|---|---|---|
| `docs/img/app-full.png` | 1500 × 3369 | 3000 × 6738 | 16 |
| `docs/img/app-holdout.png` | 1500 × 2662 | 3000 × 5324 | 4 |
| `docs/img/app-summary.png` | 1500 × 3756 | 3000 × 7512 | 5 |

All three are **full-page** captures at **device scale 2**. The 2× matters: `video_plates.py`
crops at native 2× and pastes 1:1, or `reduce(2)` to 1×, and never resamples — so a capture
taken at 1× produces visibly soft type in the film.

## 1. Start the app

```bash
./scripts/serve.sh            # loopback only, by design — see the comment in that file
```

## 2. Capture

Full-page, 1500 CSS px, DPR 2. With headless Chrome:

```bash
CHROME=/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --force-device-scale-factor=2 --window-size=1500,3369 \
  --screenshot=docs/img/app-full.png 'http://127.0.0.1:8000/?run=1'
```

Two things that will bite you:

- **WebGL will not paint** in headless Chrome, so the Mol\* viewer comes out blank. The
  `app-full.png` in the repo has a rendered molecule because it was captured from a
  **headed** browser. If you need the viewer, capture headed.
- `--window-size` height must already be the full document height, because
  `--screenshot` does not auto-expand. Get it first with
  `document.documentElement.scrollHeight`.

## 3. Measure

In the **same** browser at the **same** viewport, with the page in the **same** state:

```js
// paste in the console; copy the JSON it prints into video/app-regions.json
const W = document.documentElement.scrollWidth;
const H = document.documentElement.scrollHeight;
const SEL = {                       // region name -> CSS selector
  offline_badge: '.eyebrow-offline',
  funnel:        '#funnel',
  // ... one entry per region; see the existing file for the full set
};
const out = {};
for (const [name, sel] of Object.entries(SEL)) {
  const el = document.querySelector(sel);
  if (!el) { console.warn('MISSING', name, sel); continue; }
  const r = el.getBoundingClientRect();
  const x = r.left + scrollX, y = r.top + scrollY;
  out[name] = [ +(x / W).toFixed(4),        +(y / H).toFixed(4),
                +((x + r.width) / W).toFixed(4), +((y + r.height) / H).toFixed(4) ];
}
console.log(JSON.stringify({ css: [W, H], size: [W * 2, H * 2], regions: out }, null, 1));
```

Regions are `[x0, y0, x1, y1]` as **fractions of the capture**, so they survive a uniform
rescale but not a reflow.

## 4. Verify

```bash
python scripts/video_plates.py --check     # asserts every CUES region resolves
python scripts/make_video.py               # asserts picture >= voice per scene
```

If you removed or renamed an element, `video_scenes.CUES` is the other half of the contract —
a cue names both a region **and** the narration phrase it must land under. Fix both.
