# Interface design for a structural-biology prediction dashboard

**Research date:** 2026-09-25 · **Audience:** whoever is restyling `app/static/index.html` and `charts.js` this week.

Everything in the "measured" column below was read **out of the live DOM in this session** with
`getComputedStyle` / canvas pixel sampling, not quoted from a blog post. Where a value comes from a
document rather than a measurement it is marked as such.

| Measured fact | Value | Source |
|---|---|---|
| AlphaFold DB pLDDT band 1 — Very high (>90) | **`#0053D6`** (`rgb(0,83,214)`) | live DOM, `span.legendColor` |
| AlphaFold DB pLDDT band 2 — High / Confident (70–90) | **`#65CBF3`** (`rgb(101,203,243)`) | live DOM |
| AlphaFold DB pLDDT band 3 — Low (50–70) | **`#FFDB13`** (`rgb(255,219,19)`) | live DOM |
| AlphaFold DB pLDDT band 4 — Very low (<50) | **`#FF7D45`** (`rgb(255,125,69)`) | live DOM |
| Same four values, independently, in Mol\* source | `0x0053d6 / 0x65cbf3 / 0xffdb13 / 0xff7d45` | `molstar/…/plddt.ts` |
| Mol\* "No Score" colour | `0xaaaaaa` | `plddt.ts` |
| AlphaFold DB PAE ramp | **ColorBrewer `Greens`**, `#00441B` (0 Å) → `#F7FCF5` (30 Å) | sampled from `horizontal_colorbar.png` |
| PAE colour bar is displayed **flipped** | `transform: matrix(-1,0,0,-1,0,0)` | live DOM |
| AlphaFold DB body font | **`"IBM Plex Sans", Helvetica, Arial, sans-serif`** @ 16px | live DOM |
| AlphaFold DB section heading | **19px / weight 500 / sentence case / `letter-spacing: normal`** | live DOM |
| AlphaFold DB PAE canvas | 320 × 320 CSS px (640² backing) inside a 430 × 430 axes SVG | live DOM |
| AlphaFold DB Mol\* viewport | 620 × 420 CSS px | live DOM |
| AlphaFold DB Mol\* chrome (light theme) | `#EEECE7` | live DOM |
| AlphaFold **Server** body background | **`#131314`** — dark by default | live DOM |
| AlphaFold Server accent / focus border | **`#A8C7FA`** (desaturated) | live DOM |
| AlphaFold Server borders | **`rgba(255,255,255,0.1)`** — alpha, not solid | live DOM |
| RCSB PDB master:detail split | **col-lg-4 / col-lg-8 = 480 px : 960 px (1 : 2)** | live DOM |
| RCSB validation slider | server-rendered PNG, displayed 500 × 272 px | live DOM |
| EMBL-EBI Visual Framework neutral ramp | `#ffffff #f3f3f3 #e4e4e4 #d0d0ce #a9abaa #8d8f8e #707372 #54585a #373a36 #000000` | live DOM, `--vf-color--neutral--*` |
| EMBL-EBI VF body max width | **1280 px** (`--vf-body-width: 80em`) | live DOM |
| EMBL-EBI VF mono | **IBM Plex Mono** | live DOM |
| **Our** `main` grid at 1440 px | `732.281px 665.719px`, 14 px gap — **list wider than detail** | live DOM |
| **Our** candidate table row height | **121–122 px × 60 rows** | live DOM |
| **Our** left / right column heights | **1185 px vs 3590 px** | live DOM |
| **Our** `<th>` authored `nM` renders as | **`NM`** — `text-transform: uppercase` | live DOM |
| **Our** metric keys authored `ipTM / pLDDT / pTM` render as | **`IPTM / PLDDT / PTM`** | live DOM |

---

## 0. TL;DR — the five changes, in priority order

1. **Delete `text-transform: uppercase` from everything except one micro-label class — it is
   currently corrupting scientific notation.** This is not a taste argument. Our HTML correctly authors
   `nM`, `ipTM`, `pLDDT`, `pTM`; the CSS renders them **`NM`, `IPTM`, `PLDDT`, `PTM`**. `nM` is
   nanomolar; `NM` is not a unit. The lower-case prefixes in `pLDDT` and `ipTM` are the load-bearing part
   ("predicted", "interface"). No reference tool uppercases section headings — AlphaFold DB is
   19 px/500 sentence case, RCSB 18 px/500 plus `<strong>` 16 px/700 — and the density research
   independently flags that uppercase *"wrecks scanning of mixed-case column names like pLDDT"*.
   Seven CSS rules, one afternoon. §5.1, §6.1

2. **The colour language our app is built on inverts on the background our app uses.** Measured: the
   canonical "very high confidence" band `#0053D6` scores **2.84 : 1 on our `#0d1117`** — below the 3 : 1
   non-text floor — while "low confidence" `#FFDB13` blazes at 13.62 : 1. On white those numbers are
   6.55 : 1 and 1.36 : 1, the correct way round. **Today our interface pulls the eye to the worst part of
   every model.** Fix it by going light (recommended — every structural-biology database is light, and
   both UCSC and cBioPortal rejected dark *in writing*), or by overriding the four hexes in dark mode
   (`#6E9BF2 / #7FD4F5 / #E5C33F / #F2895A`). Doing neither is not an option. §4.2

3. **Give the confidence numbers a reference frame — steal the wwPDB validation slider.** Three bare
   mono numbers (`0.991 / 0.984 / 0.989`) cannot answer "is that good?", and at three decimals they
   assert a precision our own data says is absent (a deliberately mismatched pair scores 0.988).
   AlphaFold 3 publishes explicit ipTM bands including a named **grey zone**; RCSB's slider converts a
   raw number into a position against a *named reference population* with the poles labelled
   *Worse* / *Better*. §1.3, §1.4, §6.2

4. **Make the candidate table a table again: 122 px rows are not a table.** The dense-scientific
   consensus is **1.7–1.9× the font size**; we are at **9.8×**, because a four-line prose paragraph
   lives in every `Assessment` cell. At 60 rows × 122 px we render a 7,300 px table into a 380 px scroll
   window — three rows visible. Move the prose to the detail panel, target 26–32 px rows, add
   `tabular-nums` (we have none), and replace the four-order `nM` column with a pChEMBL-style log value.
   §5.1, §5.3, §6.5

5. **Fix the geometry: the evidence column is the narrower one, and the two columns differ in height by
   3×.** We give the scan list 732 px and the panel holding the viewer *plus* all the evidence 666 px.
   RCSB solves the same crowding by splitting **picture one third, information two thirds**; our 666 px
   column is trying to be both. And a 1185 px left column beside a 3590 px right column leaves the page
   mostly void next to a very long scroll. §6.4

**The single most transferable finding**, if you read nothing else: four independent codebases converged
on one grammar for uncertainty — **category = hue, confidence = lightness/saturation, missing = neutral
grey, provisional = glyph with no semantic colour**. None of them uses a banner or a warning triangle to
say "this is a prediction". For an app where every number is model output, that is the difference between
an instrument and a continuous warning. §3.7.3

---

## 1. What AlphaFold's own interfaces actually do

### 1.0 The four pages examined

| Page | URL | Theme |
|---|---|---|
| AlphaFold DB entry | <https://alphafold.ebi.ac.uk/entry/AF-P01116-F1> | light |
| AlphaFold Server | <https://alphafoldserver.com/> | **dark** |
| RCSB PDB entry | <https://www.rcsb.org/structure/6VXX> | light |
| PDBe entry | <https://www.ebi.ac.uk/pdbe/entry/pdb/6vxx> | light |

Note `https://alphafold.ebi.ac.uk/entry/P01116` now **redirects to a search results page** — since v6 a
UniProt accession can map to several entries (18 for P01116: 2 monomers, 16 heterodimers). The canonical
entry URL is `/entry/AF-P01116-F1`.

### 1.1 AlphaFold DB entry page — screenshot in words

Top to bottom at 1440 px wide, content column **1372 px at x = 34** (so ~34 px side gutters):

1. **EMBL-EBI global strip** (dark slate, ~26 px tall) — institutional chrome, not product chrome.
2. **Product header**, saturated navy: *AlphaFold* in white + *Protein Structure Database* in
   `rgb(209,227,246)` at 24 px/500 in **DM Sans**. A full-width search field and example-query chips
   sit *inside* the coloured header.
3. **Entry title block** on white: `GTPase KRas` as a large h1, then a single inline metadata strip —
   a blue `Monomer` pill · `AF-P01116-F1` · `Version v6` · `Google DeepMind dataset` · two file-format
   icons. A navy **Download files ▾** button is right-aligned on the same line.
4. **Tab bar**: `Summary and Model Confidence` (active) · `Domains` · `Annotations` · `Similar Proteins`.
5. **Two metadata columns**, label/value, label column **179 px**, labels at **16 px weight 500**
   `rgb(26,28,26)`:
   - left: Protein, Gene, Source organism, UniProt, Biological function (truncated with *Show more*)
   - right: Found in, Experimental structures, **Average pLDDT `91.5 (Very high)`**, and a
     **pLDDT distribution** — four rows of `[swatch] 77.8% Very high / 14.8% High / 5.3% Low / 2.1% Very low`.

   This is the single best idea on the page: **the headline confidence number is immediately followed by
   the distribution behind it.** One number plus its histogram, in four lines, above the fold.
6. **Sequence strip**, full width, header `A | 1: GTPase KRas`, a `Copy sequence` link right-aligned,
   and the sequence monospaced in **blocks of ten with the residue index inline**:
   `1 MTEYKLVVVG 11 AGGVGKSALT 21 IQLIQNHFVD …`
7. **The three-panel evidence row**:

   | | width | content |
   |---|---|---|
   | left | 430 px axes / 320 px plot | interactive PAE heatmap |
   | centre | 620 × 420 px | Mol\* viewer |
   | right | ~150 px | `Model Confidence` accordion |

   The PAE plot carries `Aligned residue` on y (0 at **top**, increasing downward) and
   `Scored residue` on x (0 at left), with a **322 × 14 px** horizontal colour bar below the x-axis
   labelled `Expected position error (Ångströms)`, ticked 0 → 30.

   The right accordion stack is `Model Confidence` (open) → `Domains (1)` (collapsed) →
   `Annotations` (collapsed). Open, it shows the four swatches with their *threshold expressions spelled
   out* — `Very high (pLDDT > 90)`, `High (90 > pLDDT > 70)`, `Low (70 > pLDDT > 50)`,
   `Very low (pLDDT < 50)` — then one sentence and a `Learn more…` link.
8. **Caption under the PAE**: *"Predicted Aligned Error (PAE) — PAE measures the confidence in the
   relative position of two residues - see Help section below for more information."*
9. A quiet row: `Share your feedback on the structure` + a `Report an issue` outlined button, and
   right-aligned `Audit history / Model creation date: 31 Jul 2025 / Sequence version date: 20 Jul 1986`,
   each with a `?` info icon.
10. `Dataset publication` — the Jumper 2021 citation.
11. `Help` — expandable long-form explainers.

### 1.2 The three AlphaFold patterns worth stealing outright

**(a) Headline metric + its distribution, together.** `Average pLDDT 91.5 (Very high)` immediately
followed by `77.8% Very high / 14.8% High / 5.3% Low / 2.1% Very low`. A mean confidence alone is a lie
of omission; the four-row breakdown costs four lines and kills the lie.

**(b) The threshold is written into the legend.** Not `Very high` but `Very high (pLDDT > 90)`. The
reader never has to remember or look up where the band edges are.

**(c) Explicit anti-misreading statements.** From the Help section, verbatim:
*"The PAE plot is not an inter-residue distance map or a contact map."* They spend a sentence on what the
plot **is not**. Our app already does this well in prose (`structHint`); the pattern is to attach the
denial *to the artefact*, not to a paragraph 800 px further down.

Three more facts from that Help text worth knowing:
- The AFDB ramp runs "from 0 Å to an **arbitrary cut-off of 31 Å**" — **AFDB clips too.** Our
  `PAE_CEILING = 8` is legitimate practice; it just has to be labelled, which `charts.js` already does
  (`8+ Å`).
- *"A dark green tile corresponds to a good prediction (low error), whereas a light green tile indicates
  poor prediction (high error)."* Dark = good. Our blue ramp already runs this direction. ✓
- **PAE is asymmetric** — `(x,y) ≠ (y,x)`. Worth a tooltip note; we currently report the pair without
  saying which is scored and which is aligned.

And the interaction: dragging a region on the PAE plot highlights it on the 3D structure, with the
**x range (scored) highlighted orange** and the **y range (aligned) highlighted emerald green**, plus a
yellow line marking the main diagonal.

### 1.3 AlphaFold Server — the dark one, and the ipTM bands

`alphafoldserver.com` is DeepMind's own structural-biology product and it is **dark by default**, with a
light/dark toggle in the top bar. Measured tokens:

| Role | Value |
|---|---|
| Page background | `#131314` |
| Recessed surface | `#0F1012` |
| Raised surface | `#1B1B1B` |
| Body text | `#F6F6F6` |
| Divider | `#444746` |
| Hairline borders | `rgba(255,255,255,0.1)` |
| Accent / focus ring | `#A8C7FA` |
| Font | `"Google Sans", sans-serif` @ 14 px |
| Headings | 48 / 36 / 28 / 24 px, all **weight 400**, sentence case |

Two things to take from this: borders are **alpha white, not a solid hex**, and the accent is a
**desaturated pastel blue**, not a saturated one. §4.4 explains the mechanism and revises the "neutral
vs blue-tinted surface" question — the tint turns out not to be the problem; saturated accents at low
lightness are.

> **Do not read this as EMBL-EBI house style.** AlphaFold *Server* (`#131314`, Google Sans) is **Google
> DeepMind's** product design language; AlphaFold *DB* (white, IBM Plex Sans) is **EMBL-EBI's**. Two
> organisations, two design systems, one shared model. §4.2.

The FAQ is a stack of single-line accordion rows on 1 px hairlines with a right chevron — the cheapest
possible "caveats without shouting" component.

**The ipTM bands, verbatim from the AlphaFold Server FAQ** — directly applicable to us, because a
peptide–HLA complex *is* an interface prediction:

| ipTM | AlphaFold 3's own words |
|---|---|
| **> 0.8** | "confident high-quality predictions" |
| **0.6 – 0.8** | "a **gray zone** where predictions could be correct or incorrect" |
| **< 0.6** | "suggest likely a failed prediction" |
| pTM > 0.5 | "the overall predicted fold for the complex might be similar to the true structure" |

Also stated: *"pTM assigns values less than 0.05 when fewer than 20 tokens are involved"* — relevant,
since our peptide chain is 9 residues. And: *"The pLDDT is shown as color outputs in the image of the
structure, using the same value to color mapping as in AFDB"* — the palette in §2.1 is the official one.

A named **grey zone** is the best single answer to "confidence is not accuracy" I found anywhere in this
research. It is an officially-sanctioned band that means *we do not know*.

> The job-submission and results screens require a Google sign-in, which was not used. Everything above is
> from the public `/welcome` route.

### 1.4 RCSB PDB — the validation slider

Layout at 1440 px: a **col-lg-4 (480 px) left column** holding the structure, and a
**col-lg-8 (960 px) right column** holding everything else — i.e. the detail/metadata side gets
**two-thirds**. Bootstrap-based, white, `#333333` text, `system-ui` stack, 16 px / 24 px.

The left column does **not** embed a live viewer. It shows a **static rendered PNG** of Biological
Assembly 1 with `‹ ›` arrows to page between assemblies, then a line of explicit entry points:
`Explore in 3D: Structure | Sequence Annotations | Electron Density | Validation Report | Ligand Interaction (NAG)`.
The live viewer is a separate destination. The summary page stays fast and screenshots cleanly.

Inside the right column, a 5 : 7 split — `Experimental Data Snapshot` (390 px) beside
`wwPDB Validation` (546 px). Panel titles are `<strong>` at **16 px / 700, sentence case**; section
headers are `<h3>` at **18 px / 500**. The link blue is `#337AB7`.

**The slider itself** (`files.rcsb.org/validation/view/6vxx_multipercentile_validation.png`, 500 × 272 px
as displayed) is a three-column figure on a light grey field:

```
   Metric            Percentile Ranks                    Value
   Clashscore        [ RED ───── white ───── BLUE ] ▮      1
   Ramachandran…     [ RED ───── white ───── BLUE ] ▮      0
   Sidechain…        [ RED ──── ▯ white ──── ▮BLUE]        0.2%
                      Worse                    Better
                     ▮ Percentile relative to all structures
                     ▯ Percentile relative to all EM structures
```

Every element of that earns its place:

- **A diverging red → white → blue ramp**, poles labelled *Worse* (italic, left) and *Better* (right).
  Direction needs no domain knowledge.
- **The raw value sits outside the bar**, in its own right-hand column. The bar answers *is this good?*;
  the number answers *what is it?* They are not conflated.
- **Two markers per row** — solid = percentile against the whole PDB, hollow = percentile against
  structures of the same method. **The reference population is named, and there is more than one.**
- **Leader lines** connect a marker to its value when the marker is near the edge, so values never
  collide.
- A second, separate slider block for a different family of metrics (`Model-Map Fit Percentile Ranks`),
  rather than mixing incommensurable metrics into one scale.

RCSB's own documentation states the semantics plainly: *"Structures with values in the blue range conform
better to expected values … whereas structures in the red range may have issues."*
<https://www.rcsb.org/docs/general-help/assessing-the-quality-of-3d-structures>

This is the most transferable single component in this whole document. It turns "0.991" into
"0.991, which is better than 94% of predictions of this kind" — and that second sentence is the one a
reviewer actually needs.

### 1.5 PDBe — two small, good ideas

1. **The title line carries the whole identity.** `pdb_00006vxx` at h1 size, then inline on the same
   baseline: `Electron Microscopy` · `2.8Å` · `Released 11 Mar 2020` · `10.2210/pdb6vxx/pdb ↗`, with
   `Download files ▾` / `View files ▾` right-aligned. Method, resolution, date and DOI in one line,
   above the fold, no card required.
2. **The 3D viewer is deferred, and says so.** In place of the canvas: an outline glyph, the text
   *"3D viewer paused due to slow connection / Loading may take longer than usual."*, and a
   **`Load 3D anyway`** button. Opt-in rendering with a stated reason.

PDBe also promotes validation to its own top-level tab (`Model Quality`), alongside `Summary`,
`Complexes`, `Macromolecules`, `Ligands and Environments`, `Domains`, `Text Annotations (AI)`,
`Citations`. Labels are sentence case throughout; `New` badges are small green pills.

---

## 2. The colour conventions, exactly

### 2.1 pLDDT — four bands

Confirmed twice over: sampled from the live AlphaFold DB legend, and cross-checked against the Mol\*
source that AFDB itself renders with.

| Band | Threshold | Hex | RGB | Mol\* constant |
|---|---|---|---|---|
| Very high | pLDDT > 90 | **`#0053D6`** | `0, 83, 214` | `0x0053d6` |
| High / Confident | 90 > pLDDT > 70 | **`#65CBF3`** | `101, 203, 243` | `0x65cbf3` |
| Low | 70 > pLDDT > 50 | **`#FFDB13`** | `255, 219, 19` | `0xffdb13` |
| Very low | pLDDT < 50 | **`#FF7D45`** | `255, 125, 69` | `0xff7d45` |
| No score | — | `#AAAAAA` | `170,170,170` | `0xaaaaaa` |

Source: <https://alphafold.ebi.ac.uk/entry/AF-P01116-F1> (live DOM) and
<https://github.com/molstar/molstar/blob/master/src/extensions/model-archive/quality-assessment/color/plddt.ts>

**Naming.** Mol\* calls band 2 `Confident`; AlphaFold DB v6 labels it `High`. AFDB's own legend text is
`High (90 > pLDDT > 70)`. Either is defensible — pick one and use it in both the legend and the tooltip.

**Two near-misses to avoid.**

- **Float-rounded variants circulate widely**: `#0D57D3 / #6ACBF1 / #FED936 / #FD7D4D`, derived from
  matplotlib RGB floats `[0.051,0.341,0.827]`, `[0.416,0.796,0.945]`, `[0.996,0.851,0.212]`,
  `[0.992,0.490,0.302]`. These are the same four colours to within 1–4 per channel — close enough to look
  like a typo of the real thing, far enough to fail a design-token diff.
- **ColabFold's own `plot_plddt_legend()` uses something else entirely** — pure primaries
  `#FF0000 / #FFFF00 / #00FF00 / #00FFFF / #0000FF` across *five* bands (`Very low / Low / OK /
  Confident / Very high`). Verified in
  <https://raw.githubusercontent.com/sokrypton/ColabFold/main/colabfold/colabfold.py>. If someone pastes
  a "ColabFold pLDDT palette" at you, check which of the two they mean.

**Use the AFDB/Mol\* values in §2.1** — they are what the 3D viewer in our own app already paints with,
so they are the only choice that makes the chart and the structure agree.

### 2.2 PAE — sequential green, dark = good

Sampled at 10 % intervals from `https://alphafold.ebi.ac.uk/assets/img/horizontal_colorbar.png`
(a 256 × 1 px image):

| Position | PAE (Å) | Hex |
|---|---|---|
| 0 % | 0 | **`#00441B`** |
| 10 % | 3 | `#006428` |
| 20 % | 6 | `#157E3A` |
| 30 % | 9 | `#2E974E` |
| 40 % | 12 | `#4BB061` |
| 50 % | 15 | `#73C375` |
| 60 % | 18 | `#98D493` |
| 70 % | 21 | `#B7E2B0` |
| 80 % | 24 | `#D3EDCC` |
| 90 % | 27 | `#E8F6E3` |
| 100 % | 30 | **`#F7FCF5`** |

This is **ColorBrewer `Greens`, reversed** — `#00441B` and `#F7FCF5` are exactly the two endpoints of the
9-class `Greens` scheme. The stored PNG runs white → dark green and is displayed with
`transform: matrix(-1,0,0,-1,0,0)`, which is why the rendered bar reads dark-green-at-zero.

**Axis convention** (AFDB):
- **x = "Scored residue"**, 0 at left
- **y = "Aligned residue"**, 0 at **top**, increasing downward
- colour bar **horizontal, under the x-axis**, labelled `Expected position error (Ångströms)`
- semantics: *"The colour at (x, y) corresponds to the expected distance error in residue x's position
  when the predicted and true structures are aligned on residue y."*

Our `drawPae` puts the origin top-left and runs dark → light with increasing error. **Direction and
origin are already right**; only the hue differs. See §6.3 for whether to switch.

### 2.3 The other AlphaFold-adjacent ramps, measured on the same page

Worth knowing, because they are the house diverging/categorical schemes in this corner of the field:

| Use | Values | Scheme |
|---|---|---|
| AlphaMissense pathogenicity | `#2166AC` benign · `#A8A9AC` uncertain · `#B2182B` pathogenic | ColorBrewer `RdBu` |
| TED domain 1 | `#1B9E77` | ColorBrewer `Dark2` |
| wwPDB validation percentile | saturated red → white → saturated blue | diverging, `bwr`-family |

Note the convergence: **AlphaMissense, the wwPDB slider, and essentially every "is this good" scale in
structural biology are red↔blue diverging with a neutral middle.** If we need a "better/worse" axis
anywhere, that is the house convention, and `#B2182B` / `#A8A9AC` / `#2166AC` are safe, colour-blind-
tolerant anchors.

---

## 3. Scientific dashboard patterns worth stealing

All values below were read from live `getComputedStyle` / `getBoundingClientRect` at a 1600 × 1000
viewport and cross-checked against each project's own SCSS/TS source. Where a value is source-only it
says so.

> Two gaps, stated rather than papered over. **UCSC hgTracks sits behind a Cloudflare bot challenge**
> which was not circumvented, so UCSC below is from its served stylesheet only. **Benchling, Schrödinger
> LiveDesign and Dotmatics have no login-free demo**, so nothing here is measured from them; treat any
> claim about those three as unverified. Terra and Galaxy were still being examined at time of writing.

### 3.1 cBioPortal — the closest analogue we have

<https://www.cbioportal.org/results/mutations?cancer_study_list=brca_tcga_pan_can_atlas_2018&gene_list=TP53%20PIK3CA%20CDH1>
· <https://www.cbioportal.org/results/oncoprint?...>
· [`variables.scss`](https://raw.githubusercontent.com/cBioPortal/cbioportal-frontend/master/src/globalStyles/variables.scss)
· [`AlterationColors.ts`](https://raw.githubusercontent.com/cBioPortal/cbioportal-frontend/master/packages/cbioportal-frontend-commons/src/lib/AlterationColors.ts)

**(a) Funnel counts at three altitudes, and only one is loud.** This is the single best answer to our
funnel problem (§6.6):

| Altitude | String | Treatment |
|---|---|---|
| Cohort | `1,084 patients \| 1,084 samples` → `Selected: 201 patients \| 201 samples` | 14 px, `#333`, 30 px tall. The word **"Selected:"** appears only once a filter is active |
| Query | `Queried genes are altered in 781 (78%) of queried patients/samples` | 13 px / 400, `#333` — deliberately quiet prose |
| Result set | `350 Mutations (page 1 of 14)` | **16 px / 700, `#000`** — the loudest number on the page |

Our five equal-weight funnel boxes give every stage the same emphasis. cBioPortal makes the *survivors*
loud and the *journey* quiet.

**(b) Filter chips that read as a sentence.** `.userSelections` bar, 44.57 px tall, `margin 0 0 10px`:

- Outer group (one per attribute, AND-ed between groups): `background #ececec`,
  `border 1px solid #dddddd`, `radius 5px`, `padding 5px`, height 40.57 px.
- Attribute name sits **outside** the pill — 13 px / 700 `#333` + a bold `:` with `margin 0 5px`.
- Value pill (OR-ed within a group): `background #2986e2`, white text, `radius 5px`, height 28.57 px,
  label `margin 5px 10px`, `fa-times-circle` delete 11.1 × 13 px.
- `Clear All Filters`: 102.4 × 30 px, 12 px, white, `1px solid #ccc`, `radius 3px`.

Rendered: `Cancer Type Detailed: [Breast Invasive Lobular Carcinoma ×]  Sex: [Female ×]  [Clear All Filters]`.

**(c) The ranked table.** 1560 px wide, 8 of **92** available columns:

| Property | Value |
|---|---|
| Row height | **26 px** (first row 27 px) |
| Cell | `padding 3px 10px`, `line-height 20px`, `font-size 14px`, `vertical-align top` |
| Header | 45.28 px (two-line: label + inline filter box), 14 px / **700**, `padding 8px 8px 4px`, `border-bottom 2px solid #dddddd`, `background #fff`, **`position: sticky`** |
| Striping | zebra `#ffffff` / `#f9f9f9` — **no row borders at all** |
| Column grouping | **2 px-wide empty `<td>` spacers** between logical groups; no vertical rules |
| Column chooser | a button reading **`Columns (8 / 92)`** — 121.4 × 30 px |

Two things **not** to copy: numerics are `text-align: left` throughout (a genuine defect — one header is
right-aligned while its cells are not), and the 45 px two-line header is heavy. There are **no in-cell
bars or sparklines anywhere**; frequency is plain text (`32.6%`).

**(d) Master–detail is vertical, with the detail on top.** Gene sub-tabs → a **1150 × 200 px lollipop
plot** with a **252 × 298 px stats panel** beside it (≈ 74 % / 16 % with gutters) → the full-width table
beginning at y = 614. The evidence for the selected item is a **wide banner above a full-width list**,
not a side panel. Worth considering for us: our detail content is wide (a 3D viewer, a PAE map) and
fits a banner better than a column.

In that stats panel, **every count is itself a one-click filter** — an `ONLY` affordance appears on
hover. Counts double as controls.

**(e) The provenance pattern worth stealing outright: same hue, lighter = "unknown significance."**

| Class | Putative driver | Unknown significance (VUS) |
|---|---|---|
| Missense | `#008000` | `#53D400` |
| Truncating | `#000000` | `#708090` |
| Inframe | `#993404` | `#a68028` |
| Splice | `#e5802b` | `#f0b87b` |
| Structural variant | `#8B00C9` | `#ce92e8` |
| Promoter | `#00B7CE` | `#8cedf9` |
| Generic binary | `MUT_DRIVER #000000` | `MUT_VUS #696969` |

The uncertain variant is **not greyed out and not badged**. It keeps its category identity and loses
only conviction. Copy-number uses the same grammar with a near-white neutral: `AMP #ff0000`,
`GAIN #ffb6c1`, `DIPLOID #FAF9F6`, `HETLOSS #8fd8d8`, `HOMDEL #0000ff`, `NA #cccccc`.

The general rule, which recurs in every tool surveyed: **category = hue, confidence = lightness /
saturation, missing = neutral grey.**

**(f) Denominators live in panel titles.** `Mutated Genes (1066 profiled samples)`,
`CNA Genes (1070 profiled samples)`. The N never needs a footnote.

**(g) Evidence tier is a glyph, not a word.** The OncoKB column is an icon-only slot **22 px wide ×
18 px tall**, annotation text at **9 px**, loading state `#aaaaaa`; nested 18 × 18 SVG circles stroked
`#0968C3` with a 4 px-radius level badge `#984EA3`. Transcript provenance is small grey text above the
stats: `NM_000546 | ENST00000269305.4 | CCDS11118 | P53_HUMAN`.

**(h) The whole funnel state is a URL** — `filters=` JSON plus a dedicated 32 × 32 copy-link button
(`fa-link` on `fa-circle`, `#3786c2`). The entire filter funnel was driven in this research by
constructing URLs, without clicking anything.

Tokens: `$brand-primary/$headerColor #3786c2`, `$main-bg #f5f5f5`, body `#ffffff`/`#333333`,
Helvetica Neue 14 px/20 px, `$lightGrey #ececec`, `$mediumGrey #ddd`, `$darkGrey #999`,
`$redError #a71111`, `$greenSuccess #11a747`, `$lightBlue #f1f6fe`, `$gutterWidth 20px`,
`$cornerBorderRadius 5px`, `ICON_FILTER_ON #000000` / `ICON_FILTER_OFF #BEBEBE`.

### 3.2 CZ CELLxGENE — the filter control we should copy

<https://cellxgene.cziscience.com/collections> · Explorer at `/e/3d8d8c97-…cxg/`

**The idea worth taking: a mini-histogram *is* the filter.** The Explorer's "Continuous" section is 11
stacked histograms, each **340 × 135 px**, bars filled flat **`#777`**, with a three-part caption row
`min 498.0 | nCount_RNA: 498 | max 5.076e+4` in 14 px **Roboto Condensed**. Each continuous covariate
shows its distribution, its current brush range, and the hovered value at once.

For us this is close to ideal. Every candidate carries several continuous scores (`nM`, `WT nM`, `DAI`,
ipTM, pLDDT). Putting a small histogram behind each threshold control means **the user sees the shape of
the score before choosing a cutoff**, so `500 nM` and `DAI ≥ 10` stop looking arbitrary — you can see
where they fall in the actual distribution. That is a direct, visual answer to "is this threshold
reasonable?" and it costs one 340 × 135 sparkline per control.

Other measured details:
- **`N of M` chip inside the table header cell**, not in a toolbar: `394 of 394`, `background #f8f8f8`,
  `radius 4px`, `padding 2px 8px`, 24 px tall, 13 px / 600, `letter-spacing -0.084px`.
- Explorer count readout: embedding name (`umap`, 14 px `#1c2127`) over **`167156 of 167156 cells`** in
  `#767676`. Selection counts sit beside it as popover targets, so hovering explains what each means.
- Three-pane layout at 1600 px: **366 px / 868 px / 366 px** (22.9 % / 54.3 % / 22.9 %), borders
  `1px solid #d3d8de` and `#e5e5e5`, both rails `overflow-y: auto`. The right rail splits into two equal
  472 px halves stacked vertically.
- A **droplet/"tint" icon (16 × 16) pinned at the rail's right edge** colours the main view by that
  covariate — the facet list and the colour-by control are the same list.
- The Discover browse table runs **72 px rows** at 14 px Inter, headers 14 px/600 `#767676`, **not
  sticky**. Useful as the contrast case: 72 px is right when each row is an object you choose between,
  wrong when you are scanning 350 of them.

Blueprint v5 palette underneath (accessibility-tested, a safe semantic set):
`dark-gray1 #1c2127`, `gray1 #5f6b7c`, `light-gray1 #d3d8de`, `light-gray5 #f6f7f9`,
`blue3 #2d72d2`, `green3 #238551`, `orange3 #c87619`, `red3 #cd4246`.

### 3.3 IGV / igv.js — the detail popover

Source values from [`_variables.scss`](https://raw.githubusercontent.com/igvteam/igv.js/master/css/_variables.scss)
and `_color.scss` (the app shell loaded but did not instantiate its track DOM).

The transferable component is the **click-a-feature popover**: `min-width 260px`, `max-width 800px`,
`background #fff`, `border 1px solid #7F7F7F`, `radius 5px`, `box-shadow 0 2px 8px rgba(0,0,0,0.12)`,
a 24 px header with `background #eee` and `cursor: move`, bold ellipsised title, and
**`user-select: text`**. A draggable, bounded-width, *selectable* detail popover is exactly the right
primitive for "show me the evidence for this one epitope" without leaving the list — and selectable text
matters, because scientists copy accessions and sequences out of these things.

Also useful: a stable chrome budget of `$igv-axis-column-width 50px` + `$igv-track-drag-column-width 12px`
+ `$igv-track-gear-menu-column-width 28px`, navbar 32 px at 12 px, `$igv-border-color #bfbfbf`,
`$igv-grey-color #7F7F7F`, selection sweep **`rgba(68,134,247,0.25)`**.

### 3.4 UCSC Genome Browser — provenance in the section header

From [`HGStyle.css`](https://genome.ucsc.edu/style/HGStyle.css). One genuinely novel pattern:
**the section-header bar's colour encodes where the data came from.**

| Class | Colour | Meaning |
|---|---|---|
| `.nativeToggleBar` | `#00457c` navy | native, curated reference data |
| `.hubToggleBar` | `#536ED3` periwinkle | track hub — third-party |
| `.quickToggleBar` | `#108020` green | quick-lifted / user-supplied |
| `.errorToggleBar` | `#ff0000` red | error |

All 28 px tall, full width, bold white text.

For a dashboard mixing reference annotation, patient data and model output, **colouring the section
header by data origin is cheaper and quieter than badging every row** — and it maps almost perfectly onto
our three kinds of card: measured reference (crystal structures, GTEx), patient input (the VCF), and
model output (Boltz-2, MHCflurry, the LLM summary).

Also worth stealing: **`.trackLabelTd { min-width: 16ch; max-width: 22ch }`** — the label gutter is sized
in *characters*, not pixels. For peptide sequences and gene names, `ch` is the correct unit. Do **not**
steal UCSC's cream `#FFF9D2` page background.

### 3.5 Terra — provisional states, and prose provenance

[`colors.js`](https://raw.githubusercontent.com/DataBiosphere/terra-ui/dev/src/libs/colors.js) ·
[`table.js`](https://github.com/DataBiosphere/terra-ui/blob/dev/src/components/table.js) ·
[`job-common.js`](https://github.com/DataBiosphere/terra-ui/blob/dev/src/components/job-common.js) ·
[`FileProvenance.js`](https://github.com/DataBiosphere/terra-ui/blob/dev/src/workspace-data/provenance/FileProvenance.js)

**(a) No colour ramp — an intensity function.** `colors.js` is 12 lines; every tint is computed at call
time as `Color(base).mix(Color('white'), 1 - intensity)`. Base: `primary/success #74ae43`,
`accent #4d72aa`, `warning #f7981c`, `danger #db3214`, `dark #333f52`, `light #e9ecef`, `grey #808080`.
Intensity **> 1 extrapolates past the base** (`primary(1.5)` = `#2e8600`). Resolved: row divider
`#d6d9dc`, table header `#f4f6f7`, warning banner `#fef0dd` on `#f9ad49`, error banner `#fae0dc` on
`#e25b43`.

**(b) The total-count pill inverts when a filter is on.** One component serves both the global total and
every facet: `width: 4.5rem` (72 px fixed, so all pills align), `radius 1rem`, `1px solid #cccfd4`,
white ground. `highlight = isEmpty(selectedSections)` — **solid green while unfiltered, hollow the moment
any facet engages.** That single inversion is the entire "you are now looking at a subset" signal.

**(c) Facet counts are computed against the *other* facets**, union within a section and intersect
across sections, with zero-count values dropped — so a facet never shows `(0)` for something you could
still usefully enable.

**(d) Provisional states get the glyph but not the colour.** In `job-common.js`, `retryableFailure`
renders the **error icon in the neutral `dark` colour**, tooltipped *"This attempt failed. It will retry
if the overall workflow is in a non-failed state."* Semantic colour is reserved for terminal facts.
Related: `renderInProgressElement` prefixes partial numbers with italic `'In progress - '`, and tiny
costs floor to **`'< $0.01'` rather than printing false precision** — precisely the discipline our
three-decimal ipTM lacks (§6.2a).

**(e) Provenance is hedged prose with a named confidence tier.** `FileProvenance.js` has five outcomes,
each a full sentence, and `maybeSubmission` is **its own branch in the type system**: *"Unknown. This
file may be associated with submission ⟨link⟩, but it was not found in workflow outputs."* The
"probably, but I can't prove it" case gets a clickable lead **and** an explicit statement of why it is
unconfirmed. The negative case names its search window: *"…not configured as an output in any of the
last N workflows run on this data type."* No badge, no amber.

**(f) Tables**: row and header both **48 px**, cells `padding-left/right 1rem`, divider
`1px solid #d6d9dc`, header `#f4f6f7`. **No sticky header** — the header is a plain div rendered as a
*sibling* above a virtualised grid of `height − headerHeight`. Structurally simpler and it never
desyncs. Every truncated cell is tooltip-wrapped; truncate-plus-tooltip is the default, not wrap.
Detail surfaces are a **450 px right `ModalDrawer`** (`box-shadow 3px 0 13px 0 rgba(0,0,0,0.3)`).

**(g) Status as a tint on the identity cell, not a badge in a status column.** The first cell paints
itself by aggregate state (`#f8d6d0` / `#dbe3ee` / `#e3efd9`) using `margin: 0 -1rem` +
`padding: 0 1rem` so the tint bleeds through the gutter.

> ⚠️ Terra sets `font-variant-numeric: proportional-nums` — **the wrong default for a score column.**
> Use `tabular-nums`.

### 3.6 Galaxy — the cheapest uncertainty vocabulary anywhere

[`blue.scss`](https://github.com/galaxyproject/galaxy/blob/dev/client/src/style/scss/theme/blue.scss) ·
[`states.ts`](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/History/Content/model/states.ts)

`$brand-primary #25537b`, `$success #66cc66`, `$info #2077b3`, `$warning #fe7f02`, `$danger #e31a1e`,
`$border-color #bcc6cf`, `$panel-width 288px`, and **`$font-size-base 0.85rem` = 13.6 px app-wide**.

**(a) Four lines that do the whole "there's more to know here" job** (`help-text.scss`):

```scss
.help-text      { text-decoration-line: underline; text-decoration-style: dashed; }
.help-info-icon { cursor: help; opacity: 0.6; }   /* → 1 on hover */
```

A dashed underline, `cursor: help`, and 0.6 opacity. No badge, no colour, zero layout cost. This is the
right treatment for every defined term in our app (`DAI`, `ipTM`, `anchor`, `TCR-facing`, `%rank`) and it
would let us shorten several of the grey prose blocks to a sentence plus hover.

**(b) A non-colour channel for "not really here."** `deleted` and `hidden` states get
**`border-style: dotted`** in addition to their colour — a channel that survives colour-blindness,
greyscale printing and photocopied slides.

**(c) `deferred` is an explicit state meaning "data exists but metadata may be incomplete"** — `info`
blue, cloud glyph, and the sentence *"This dataset is remote, has not been ingested by Galaxy, and full
metadata may not be available."* And `nonDb: true` marks states that are **purely visual and do not
exist server-side** — the model distinguishes *what is true* from *what we are currently showing*.

**(d) In-flight states get no semantic colour at all** — `running`, `queued`, `new`, `upload` are
neutral. Same discipline as Terra (3.5d). Colour means a settled fact.

**(e) Staleness as an escalating ladder** (`ContentExpirationIndicator.vue`): `secondary` grey →
`warning` at ≤ 5 days → `danger` when expired, tooltipped with the store and the date, and rendered only
when expiry is actually possible. **Directly transferable** to "this prediction was computed N days ago
against model version X" — which we will need the moment the demo is not run live.

**(f) State applied via `[data-state="…"]` attribute selector**, with hover/focus generated by
`scale-color($bg, ±10%)` — one attribute on the row, zero per-state CSS written by hand. Resolved
backgrounds include `ok #c2ebc2`/border `#94db94`, `error #f4a3a5`/`#eb5f62`, `running #ffe6cd`/`#bcc6cf`,
`new|queued|waiting #e9ecef`/`#bcc6cf`, `deleted #90a0af`/`#657a8d`.

**(g) Selection is `border-left: 4px solid #25537b`** — not a background fill. State icons are
**14 × 14 px, deliberately sub-text-size**, so they read as markers rather than alerts. Rows ≈ 32 px.

**(h) Provenance is addressable**: `/datasets/<id>/details`, `/datasets/<id>/error`,
`/workflows/invocations/<id>`, with every opaque ID shown beside its decoded integer and a copy button.
Terra prefers modals and prose; Galaxy prefers URLs and raw identifiers. We can afford both.

### 3.7 Cross-cutting conclusions

1. **Row height is the load-bearing decision.** Measured: cBioPortal analysis table **26 px**, cBioPortal
   tiles **25 px**, Galaxy list rows ≈ **32 px** (`.table-sm` 31 px), Mol\* control rows **32 px**, Terra
   tables **48 px**, CELLxGENE browse table **72 px**. For a ranked list people *scan*, the consensus is
   **26–32 px at 13–14 px with ~`3px 10px` cell padding**. Reserve 48–72 px for "choose one of twelve".
   **Our 122 px is off this scale by 4×.**
2. **Nobody uses heavy chrome.** Zero box-shadows on cBioPortal tiles. Borders are 1 px in the
   `#bcc6cf`–`#dddddd` band. **Zebra striping at `#f9f9f9` against white — a ~2.4 % luminance step —
   replaces row borders entirely.** Our per-row `border-bottom:1px solid #21262d` is heavier than any
   reference tool.
3. **Uncertainty is encoded in the object, never in an adjacent warning.** This is the strongest signal
   in the entire survey, because **four independent codebases converged on the same grammar**:

   > **category = hue · confidence = lightness/saturation · missing = neutral grey ·
   > provisional = glyph with *no* semantic colour**

   cBioPortal lightens the hue for VUS; AlphaFold/Mol\* colours the backbone by pLDDT; Terra's
   `retryableFailure` pairs the error icon with neutral `#333f52`; Galaxy leaves `running`/`queued`/`new`
   uncoloured and marks non-solid facts with `border-style: dotted`. **Not one of them uses a yellow
   banner or a warning triangle to say "this is a prediction."** For a dashboard where essentially every
   number is model output, that convergence is the most transferable finding available — and it is the
   direct argument for demoting our amber header banner (§6.6).
4. **Colour means a settled fact.** Both Terra and Galaxy withhold semantic colour from in-flight and
   provisional states entirely. If we adopt this, `ipTM` in the 0.6–0.8 grey zone (§1.3) should be
   rendered *neutral*, not amber — the grey zone is literally named for this.
5. **Counts appear at every altitude; exactly one is loud** — and Terra's total-count pill **inverts
   from solid to hollow** the moment any filter engages.
6. **The funnel state is a URL.** cBioPortal, CELLxGENE, Terra and Galaxy all encode filter state in the
   address bar; cBioPortal and Galaxy add explicit copy-link affordances.
7. **Two things nobody gives you — decide deliberately, don't assume precedent:**
   - **No in-cell bars or sparklines exist in any of these codebases.** Galaxy's quota meter is the only
     quantitative bar anywhere in the set. If we want a score bar in the candidate table we are
     **inventing, not borrowing** (see §6.5).
   - **Sticky headers are rare.** cBioPortal uses `position: sticky`; Terra renders the header as a
     fixed-height *sibling* above a virtualised grid, which is the more robust pattern past a few
     thousand rows.

---

## 4. Dark or light

### 4.1 The census — what serious tools actually default to

Every row below was observed directly in this research (live DOM or project source), not inferred.

| Tool | Default | Evidence |
|---|---|---|
| AlphaFold DB | **light** | body `#ffffff`, text `rgb(10,10,10)` |
| RCSB PDB | **light** | body `#ffffff`, text `#333333` |
| PDBe | **light** | white, EMBL-EBI green chrome |
| EMBL-EBI Visual Framework | **light** | `--vf-color--neutral--0 #ffffff`, text `#1a1c1a` |
| cBioPortal | **light** | body `#ffffff`/`#333`, `$main-bg #f5f5f5` |
| CZ CELLxGENE | **light** | Blueprint light, text `#1c2127` |
| IGV / igv.js | **light** | navbar `#f3f3f3`, text `#444` |
| UCSC Genome Browser | **light** | page `#FFF9D2` / `#F9F9F7` |
| Terra | **light** | `light #e9ecef`, header `#f4f6f7` |
| Galaxy | **light** | `$border-color #bcc6cf`, light theme default |
| UniProt | **light** | `#FBFEFF` |
| **Mol\* viewer** (molstar.org/viewer) | **light**, warm `#EEECE7` | black canvas; dark chrome only added in **v5.5.0, 2025-12-22** |
| pdbe-molstar **library default** | **dark** `#111318` | black canvas; a `-light` build ships alongside |
| IGV web (igv.js) | **light** | maintainer: *"there is no dark mode"* |
| IGV desktop | light | dark added in 3.0; colour fixes merged Sept 2026 |
| PyMOL / ChimeraX / VMD | n/a | **black canvas** by default, white for figures |
| Grafana | **dark** | light available |
| **AlphaFold Server** | **dark** | `#131314` / `#F6F6F6`, with a toggle |

Three findings settle this, and they point one way:

1. **Every database and every published reference resource in structural biology is light**, without
   exception — AlphaFold DB, PDBe, RCSB, UniProt, cBioPortal, UCSC, IGV, Galaxy, Terra.
2. **Two tools opted out of dark deliberately and said so in writing** — UCSC in a CSS comment,
   cBioPortal in a closed issue (§4.2).
3. **The strongest single signal: pdbe-molstar's *own* default is dark chrome + black canvas, and every
   EMBL-EBI production deployment overrides it to light + white.** AlphaFold DB loads
   `pdbe-molstar-light.css`; RCSB sets `backgroundColor: ColorNames.white`. The people who ship the
   viewer we embed, for the audience we are targeting, chose to override its default.

The one dark example, AlphaFold Server, is **Google DeepMind's product design language, not a
structural-biology convention** — see the caveat at the end of §4.2.

### 4.2 The recommendation: light by default, dark as a real opt-in

This reverses the intuition. The decisive argument is not taste, not screenshots, and not the viewer —
it is that **the canonical pLDDT palette inverts on a dark ground.**

Measured WCAG contrast for the four bands (§2.1) against white and against a near-black canvas:

| Band | Hex | OKLCH L | vs `#FFFFFF` | vs `#111318` |
|---|---|---|---|---|
| Very high (> 90) | `#0053D6` | 0.491 | **6.55 : 1** | **2.84 : 1** ← fails the 3 : 1 graphics floor |
| Confident (90–70) | `#65CBF3` | 0.796 | 1.84 : 1 | 10.08 : 1 |
| Low (70–50) | `#FFDB13` | 0.895 | 1.36 : 1 | 13.62 : 1 |
| Very low (< 50) | `#FF7D45` | 0.731 | 2.54 : 1 | 7.32 : 1 |

On white the ramp reads correctly: *very high confidence* is the most prominent band. **On near-black the
ordering flips** — the band that matters most nearly disappears (2.84 : 1, below even the 3 : 1 non-text
floor) while *low confidence* blazes at 13.62 : 1. The interface pulls the eye to the worst part of the
model. The same hazard applies to any heatmap whose palette was authored against white, which is most of
them in this field.

**This is a live defect in our app today**, not a hypothetical: our page is `#0d1117` and our 3D viewer
is already painting these exact hexes.

Corroborating evidence, all verified:

- **cBioPortal's maintainers explicitly rejected dark mode**
  ([issue #11815](https://github.com/cBioPortal/cbioportal/issues/11815), opened and closed 18 Nov 2025)
  for exactly this reason: *"given all the custom color coding we do, some of it dynamic, I think this
  mode will be quite difficult to achieve, test, and then maintain."*
- **UCSC opts out in code**, with a comment: `HGStyle.css` opens with *"The browser UI is designed for a
  light background only"* followed by `:root { color-scheme: light; }`.
- **Zero `prefers-color-scheme` rules** in any of `molstar.css`, `pdbe-molstar.css`,
  `pdbe-molstar-light.css`, EBI Visual Framework v2.5, EBI global v1.4, UCSC, IGV or Observable.
  The EBI VF's only "dark-mode" selectors in 170 KB are seven rules for social-media icons.
- **Piepenbrock et al. 2014** (*Human Factors* 56(5):942–51, doi:10.1177/0018720813515509): *"the positive
  polarity advantage linearly increased with decreasing character size."* The light-mode advantage
  **grows as type shrinks** — and a dense 12–13 px scientific table is precisely where dark costs most.
- Screenshots land in decks and papers on white.

**So: light default.** But ship dark as a genuine opt-in — respect `prefers-color-scheme`, allow a manual
override — because **Legge et al. 1985** (*Vision Research* 25(2):253–65) is the real counter-case:
readers with cataract or otherwise cloudy ocular media are measurably faster in negative polarity. Don't
force either.

**If you ship dark, you must override the pLDDT hexes in dark mode.** A dark-tuned set that lands all
four in a 7–11 : 1 window, so *hue* carries the distinction instead of accidental lightness:

| Band | Light (canonical) | Dark override | Contrast on `#111318` |
|---|---|---|---|
| Very high | `#0053D6` | **`#6E9BF2`** | 6.75 : 1 |
| Confident | `#65CBF3` | **`#7FD4F5`** | 11.18 : 1 |
| Low | `#FFDB13` | **`#E5C33F`** | 10.80 : 1 |
| Very low | `#FF7D45` | **`#F2895A`** | 7.52 : 1 |

Keep the canonical hexes untouched in light mode — those are the colours people recognise from the
papers, and recognition is the whole reason to adopt the convention.

> **A correction worth making in our own notes.** AlphaFold *Server* (`#131314`, Google Sans) is **Google
> DeepMind's** product design language; AlphaFold *DB* (`#ffffff`, IBM Plex Sans) is **EMBL-EBI's**.
> Different organisations, different design systems. They should not be cited as one house style — and
> once separated, the "the field's own prediction tool chose dark" argument weakens considerably: it is
> one vendor's product language, not a structural-biology convention.

### 4.3 The actual problem: we are not "GitHub-like", we *are* Primer

Checked against Primer's published dark tokens
(<https://primer.style/foundations/color/overview/>). Our `:root` is not merely similar — it is
GitHub's dark theme copied token for token:

| Our variable | Our value | Primer `dark` token |
|---|---|---|
| `--bg` | `#0d1117` | `canvas.default` |
| `--panel` | `#161b22` | `canvas.subtle` |
| `--line` | `#30363d` | `border.default` |
| `--text` | `#e6edf3` | `fg.default` |
| `--muted` | `#8b949e` | `fg.muted` |
| `--accent` | `#58a6ff` | `accent.fg` |
| `--chip` | `#21262d` | `neutral.muted` |
| `charts.js` `STATUS.muted` | `#6e7681` | `neutral.emphasis` |

That is why it reads as a developer tool: it **is** the developer tool. Three specific properties of
Primer dark work against "scientific instrument":

1. **It is blue-cooled.** `#0d1117` is `rgb(13,17,23)` — blue > green > red. Primer's own documentation
   describes it as "a deep, slightly blue-cooled near-black". Both of our credible reference points
   avoid this: AlphaFold Server sits at `#131314` (`rgb(19,19,20)` — essentially neutral), and the
   EMBL-EBI neutrals are slightly *warm/green* (`#373a36`, `#54585a`, `#707372`). A blue cast plus
   saturated cyan-blue accents is the specific combination that reads as terminal chrome.
2. **Borders are solid hex.** `#30363d` is a fixed colour, so it is correct at exactly one elevation and
   slightly wrong at every other. AlphaFold Server uses `rgba(255,255,255,0.1)` — an alpha border sits
   correctly on every surface automatically, and it is what makes stacked dark panels look considered
   rather than assembled.
3. **The accent is saturated on near-black.** `#58a6ff` against `#0d1117` is a high-chroma, high-contrast
   pairing that produces visible halation (the glow/bleed at the edges of small blue text and 1 px blue
   rules). This is why our `Run triage` button and every blue link feel slightly electric. AlphaFold
   Server's answer is `#A8C7FA` — the same hue, desaturated and lightened, so it is legible without
   vibrating.

### 4.4 The dark ramp, if you ship dark

Anchor the canvas on **`#111318`** — that is Mol\*'s own `$default-background`
(`src/mol-plugin-ui/skin/dark.scss`), so the embedded viewer's chrome fuses with the app instead of
sitting in a box.

| Step | Role | Hex | OKLCH L | ΔL |
|---|---|---|---|---|
| −1 | well / inset (sequence strip, inputs) | `#0C0E12` | 0.163 | — |
| 0 | app canvas (**= Mol\* base**) | `#111318` | 0.187 | +2.3 |
| 1 | panel / card / table body | `#171A20` | 0.217 | +3.0 |
| 2 | raised: table header, toolbar | `#1E222A` | 0.251 | +3.4 |
| 3 | popover / menu / dialog | `#272C36` | 0.293 | +4.1 |
| 4 | border-subtle (row rules) | `#2E3440` | 0.324 | +3.2 |
| 5 | border-default (panel edges) | `#3A4150` | 0.375 | +5.1 |

Text and accents (contrast vs `#111318` / `#171A20` / `#1E222A`):

| Token | Hex | Contrast |
|---|---|---|
| text-primary | `#E4E8F0` | 15.13 / 14.19 / 12.98 |
| text-secondary | `#A7B0C0` | 8.51 / 7.98 / 7.30 |
| text-muted | `#78808F` | 4.67 / 4.38 / 4.01 |
| accent | `#6E9FFF` | 7.14 / 6.69 / 6.12 |
| accent-hover | `#93B8FF` | 9.33 / 8.75 / 8.00 |

These steps are not invented: Mol\*'s SCSS derives its whole dark theme from the base by lightness delta
(`$control-background = +6.5% L`, `$border-color = +15% L`, `$msp-form-control-background = −2.5% L`,
with `$color-adjust-sign: -1` flipping the sign for dark). Computing those gives `#1F222B` and `#313645`,
both confirmed live on the pdbe-molstar demo (`.msp-layout-left` computes to `rgb(31,34,43)` = `#1F222B`
exactly). The table above is that model with intermediate steps.

**Note the inset step goes *darker* than the canvas.** Mol\* does this (−2.5 % L) and GitHub Primer does
it independently (`--bgColor-inset #010409` under `--bgColor-default #0d1117`). Recessed things recede;
they do not elevate.

**Borders: use relative tokens, not solid hex, for anything that sits on more than one surface.**
Grafana's dark theme (`packages/grafana-data/src/themes/createColors.ts`) defines a single
`whiteBase = '204, 204, 220'` and derives `border.weak rgba(…,0.12)`, `medium rgba(…,0.2)`,
`strong rgba(…,0.30)`, plus `text.secondary rgba(…,0.65)`. Observable does the same with `color-mix`:
row rules at `color-mix(in srgb, var(--theme-foreground) 14%, …)`, the header rule at 30 %. Three
independent professional tools converge on relative tokens — copy that mechanism, not a hardcoded list.
Solid hexes (`#2E3440` / `#3A4150`) are fine for fixed, known pairings such as row rules on a known panel.

**Halation has a measurable threshold.** Same hue family, all on `#111318`:

| Hex | OKLCH L | C | Contrast |
|---|---|---|---|
| `#0053D6` (AlphaFold's raw blue) | 0.49 | 0.213 | 2.84 : 1 |
| `#3D71D9` | 0.57 | 0.169 | 4.04 : 1 |
| `#51A2FB` (Mol\*'s dark hover) | 0.70 | 0.153 | 7.00 : 1 |
| `#6E9FFF` (Grafana's dark link) | 0.71 | 0.151 | 7.14 : 1 |
| `#68BEFD` (Mol\*'s "current entity") | 0.77 | 0.123 | 9.18 : 1 |

**Rule: on near-black keep accents at OKLCH L ≥ 0.65 and C ≤ ~0.16.** The mechanism is optics, not
folklore — longitudinal chromatic aberration puts the red and blue focal planes roughly 1.25–1.50 D
apart, so the eye cannot focus a saturated blue edge and a near-black ground simultaneously, and the
effect is documented as strongest against a dark field specifically
(<https://pmc.ncbi.nlm.nih.gov/articles/PMC12962248/>). Our `#58a6ff` on `#0d1117` sits right in the
bad zone.

**Do not use pure black.** `#FFFFFF` on `#000000` is 21.00 : 1, the theoretical maximum and the classic
halation case for the ~47 % of people with ≥ 0.75 D astigmatism. Every shipped professional dark UI backs
off to 15–19 : 1: Mol\* `#111318` (18.58), Grafana `#111217` (18.70), Primer `#0d1117` (18.92),
Material's recommended `#121212` (18.73). None of them uses pure white text either — Grafana `#CCCCDC`,
Mol\* `#CCD4E0`, Primer `#f0f6fc`.

**On tint:** go *blue-tinted neutral*, not pure grey — Mol\*, Grafana and Primer are all blue-leaning;
VS Code Dark Modern is the outlier at pure neutral (`#1F1F1F` / `#181818` / `#2B2B2B`). Since our accent,
our links and the pLDDT "very high" band are all blue, a blue-leaning ground stops them reading as
foreign objects. Keep it subtle (C ≈ 0.011 at the canvas, only legible by the time you reach the borders
at C ≈ 0.027). This revises §4.3's "blue-cooled is the problem" — the problem is **saturated blue accents
at low lightness**, not the ground's tint.

**One structural idea worth stealing:** VS Code Dark Modern makes the **chrome darker than the content**
(`#181818` sidebar/tab strip/status bar vs `#1F1F1F` editor), and its light theme does the same
(`#F8F8F8` chrome, `#FFFFFF` editor). Content is the lightest surface; furniture recedes. For a dashboard
where the viewer and the table *are* the point, that reads better than the usual "elevation = lighter"
stack.

### 4.5 The viewer canvas and the charts

**3D canvas → pure black `#000000`.** Not a lighter near-black. Verified empirically on
`molstar.org/pdbe-molstar/`: `gl.getParameter(gl.COLOR_CLEAR_VALUE)` returns `[0,0,0,1]` and sampling
rendered corner pixels gives `#000000`, while the surrounding chrome computes to `#111318` and the panels
to `#1F222B`. It matches source — `src/mol-gl/renderer.ts`:
`backgroundColor: PD.Color(Color(0x000000))`. So Mol\*'s own answer is a **deliberate black canvas inside
near-black chrome**: the slight step makes the viewport read as a separate optical device, and black
maximises depth cues for the molecule.

Also **give the user a one-click white-canvas toggle for figure export.** Mol\* exposes it as a
first-class setting and the pdbe-molstar demo literally ships `Set Background: White / Black` buttons.
This matters for us: our demo screenshots need a white canvas.

**In light mode the answer differs, and this is the strongest single signal in the whole census:** RCSB
sets its canvas to **white** (`rcsb-molstar`, `backgroundColor: ColorNames.white`), and AlphaFold DB
loads `pdbe-molstar-light.css` with a white bgColor. The pdbe-molstar library's *own* default is dark
chrome + black canvas — **every EMBL-EBI production deployment overrides it to light + white.** That
override tells you what this audience expects.

**Charts → transparent, drawn straight onto the panel.** Measured on `play.grafana.org`: the panel
surface is `#181B1F` and the chart content area computes to `rgba(0,0,0,0)`. Observable Framework does
the same declaratively — Plot's default is `--plot-background: white`, and Framework overrides it to
`--plot-background: var(--theme-background)`.

So: **no separate chart fill.** Define the plot area with a 1 px border at the border-subtle token plus
faint gridlines, not a background step. Gridlines at `#2E3440` on panel `#171A20` is **1.40 : 1** —
deliberately near-invisible, which is correct for grid. Our `INK.grid = #30363d` is a solid hex already
applied on two different surfaces.

**Keep `#ffa657` for the peptide.** It is distinct from every pLDDT band and survives both themes.

### 4.6 If you build a light mode

Use the EMBL-EBI Visual Framework values directly rather than inventing: neutrals
`#ffffff · #f3f3f3 · #e4e4e4 · #d0d0ce · #a9abaa · #8d8f8e · #707372 · #54585a · #373a36`, text
`#1a1c1a` / `#373a36`, link `#3b6fb6` (hover `#193f90`, visited `#563d82`), and semantic
`#18974c` / `#f49e17` / `#d41645`. That is a real, maintained, accessibility-reviewed scientific design
system, and using it makes our light mode look like it belongs beside AlphaFold DB and PDBe — which is
exactly the association we want when a screenshot lands in a slide.

---

## 5. Density and typography

### 5.1 Row height — the measured consensus

| Tool | Row | Font / line-height | **Ratio** | Cell padding |
|---|---|---|---|---|
| Observable Framework | **22 px** | 13 px / 1.2 | **1.69×** | `3px 6.5px 3px 0` |
| cBioPortal study grid | 25 px | 13 px / 18.57 px | 1.92× | — |
| cBioPortal mutations | **26 px** | 14 px / 20 px | 1.86× | `3px 10px` |
| EBI VF `.vf-table__cell` | 35 px | 19 px | 1.84× | `8px 16px` |
| Galaxy history items | ≈ 32 px | 13.6 px | — | `.p-2.px-3` |
| Mol\* control rows | 32 px | 14 px | — | `$row-height` |
| Grafana table panel | 36 px | 14 px / 22 px | 2.57× | `6px` |
| RCSB (Bootstrap) | 38 px | 16 px | 2.38× | `8px` |
| Terra tables | 48 px | — | — | `1rem` L/R |
| IBM Carbon data-table | 24 / 32 / 40 / 48 / 64 px | — | — | `md` default |
| CELLxGENE collections | 72 px | 14 px | — | `12px 0` |
| **NeoFold Edge now** | **121–122 px** | 12.5 px / 18.75 px | **9.8×** | `7px 9px` |

**The pattern is a ratio, not a pixel count: dense scientific tools cluster at 1.7–1.9× the font size;
generalist dashboards sit at 2.4–2.6×.**

**Target: 13 px text / 18 px line-height / 4 px vertical padding = 26 px rows**, with 10–12 px horizontal
padding. A truly dense mode would be 12 px / 16 px / 3 px = 22 px. If a tier pill makes 26 px tight, go
to 30–32 px (the Galaxy / Mol\* value) rather than growing the font.

**Header treatment.** The best measured precedent is Observable's **two-weight rule system**: `thead tr`
gets a rule at 30 % foreground while body rows get 14 % — the header is separated by a *heavier rule*,
not by a different type treatment. Combined with the other measurements, the recommendation is:

- same **13 px** as the body, **weight 600**
- **no uppercase** — independently corroborated here: uppercase *"wrecks scanning of mixed-case column
  names like pLDDT"*, which is precisely the bug documented in §6.1
- `text-align: left`, `vertical-align: bottom` (Observable)
- sticky, sitting on surface step 2, with a 1 px rule beneath at ~2× the body row rule's weight

Avoid cBioPortal's bold + uppercase + two-line header (heavy, and it is where their `nM`-style casing
would break too) and EBI's 19 px cells.

The rule underneath the numbers: **row height is set by purpose, not taste.** 26–32 px when the user is
*scanning to compare*; 48–72 px when each row is *an object they choose between*. Our candidates table is
the first kind. Our dataset/allele pickers are the second.

Two structural devices that keep rows short:
- **Truncate + tooltip as the default, never wrap** (Terra, §3.5f). A wrapping cell is what turned our
  rows into 122 px.
- **Column grouping with 2 px-wide empty `<td>` spacers**, not vertical rules (cBioPortal, §3.1c). Would
  let us group `nM | WT nM | DAI` as "the screen" and separate it from identity columns, for free.

### 5.2 What to monospace

Monospace is not decoration; it buys **column-alignment of glyphs** and **unambiguous character
identity**. Apply it where one of those two actually matters.

**Monospace:**
- Peptide and protein sequences — the whole point; alignment is the information. Consider the AFDB
  treatment (§1.1): blocks of ten with the residue index inline, plus a `Copy sequence` affordance.
- HLA alleles — `HLA-C*08:02`. The `*` and `:` are structural, and the digits should align down a column.
- Accessions and structure IDs — `P01116`, `AF-P01116-F1`, `8ULN`, `NM_000546`, `ENST00000269305.4`.
- All numeric columns — `nM`, `WT nM`, `DAI`, ipTM, pLDDT, RMSD, Å values.
- Run IDs, hashes, file paths, model versions.

**Do not monospace:**
- The `Variant` column. `KRAS G12D` is a *name*, not a code. We currently set the peptide cell `.mono`
  and leave `Variant` proportional — that split is already right; keep it.
- Gene symbols in prose, tier labels (`TCR-facing`, `presented`), assessments, any sentence.
- Section headers, buttons, form labels.

A useful test: **if two adjacent rows' values should line up character-for-character, monospace it.**
`GADGVGKSAL` above `ITDKHELF` — yes. `KRAS G12D` above `PIK3CA I45D` — no.

UCSC's `ch` trick (§3.4) is the right companion: size sequence/label gutters in **characters**
(`min-width: 16ch; max-width: 22ch`), not pixels, so the column fits the data by construction.

### 5.3 Numbers

1. **`font-variant-numeric: tabular-nums` on every numeric cell.** In a proportional face `1` is narrower
   than `8`, so `11.9` and `88.1` do not align and the column cannot be read as a column. Our `.num`
   and `.mono` classes do not set it. (Terra explicitly sets `proportional-nums` — §3.5 — which is the
   wrong default for a score column and is called out here so we do not copy it.)
2. **Right-align all numerics.** cBioPortal left-aligns them and is inconsistent about the headers; that
   is a defect, not a pattern. Right-alignment plus tabular figures gives decimal alignment for free when
   the decimal count is fixed.
3. **Fix the decimal count per column, and choose it honestly.** ipTM/pLDDT/pTM to **two** decimals
   (§6.2a). Å values to two. `DAI` to one. `nM` to zero.
4. **Mixed magnitude — transform, don't format.** `nM` runs 39 → 11,616 in our visible rows, nearly four
   orders. **The domain has already solved this**: `pChEMBL = −log₁₀(molar affinity)`, so 1 nM → 9.0 and
   10 µM → 5.0. One log-scale number, one or two decimals, sorts correctly, right-aligns cleanly, and
   **sidesteps the alignment problem entirely rather than fighting it typographically.** Display the log
   value; keep the raw value and unit as a secondary line or on hover.

   This is strictly better than the in-cell bar I was about to recommend (§6.5): it is an established
   convention in exactly our field, it needs no new visual vocabulary, and it makes a four-order spread
   into a 5-point linear range.

   A caveat to surface alongside it: *"Combining IC50 or Ki Values from Different Sources Is a Source of
   Significant Noise"* (*JCIM*, doi:10.1021/acs.jcim.4c00049). Don't imply more precision than
   cross-assay agreement supports.

   Avoid free-floating **scientific notation** in a scannable column — `1.16e4` is harder to compare at a
   glance than `11,616`, and it makes a table look like a REPL. For p/q-values, where it is unavoidable,
   use a **consistent mantissa width** (`1.2e-14`, never `1e-14` beside `1.23e-9`) and floor at
   `< 1e-300` rather than printing `0`.
5. **Floor tiny values rather than printing false precision** — Terra's `'< $0.01'` (§3.5d). Our
   equivalent: a sub-nanomolar affinity should read `< 1`, not a long decimal.
6. **Prefix partial results.** Terra's italic `'In progress - '` for numbers still accumulating.

**The only normative numeric treatment in any major design system is GOV.UK's, and it is three lines:**

```scss
.govuk-table__cell--numeric   { font-variant-numeric: tabular-nums; }
.govuk-table__header--numeric,
.govuk-table__cell--numeric   { text-align: right; }
```

For contrast: IBM Carbon documents five row heights and **no numeric guidance at all** (open issue
#3831 asks for it), and the EMBL-EBI Visual Framework contains **zero occurrences of `tabular-nums`** in
its entire 331 KB stylesheet. This is a genuinely under-specified corner of the discipline — which means
doing it deliberately is cheap differentiation.

### 5.4 Font stacks

Measured, as literal CSS:

| Tool | UI stack |
|---|---|
| AlphaFold DB, EMBL-EBI VF | `"IBM Plex Sans", Helvetica, Arial, sans-serif` |
| RCSB PDB | `system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", "Noto Sans", "Liberation Sans", Arial, sans-serif` |
| AlphaFold Server | `"Google Sans", sans-serif` |
| cBioPortal | `"Helvetica Neue", …` @ 14 px / 20 px |
| CZ CELLxGENE | `Inter` @ 14 px / 18 px — **plus `Roboto Condensed` for all numeric chrome** |
| IGV | `'Open Sans', sans-serif` |
| Galaxy | Bootstrap default, `$font-size-base 0.85rem` = **13.6 px app-wide** |
| **EMBL-EBI VF mono** | **IBM Plex Mono** |
| **NeoFold Edge now** | `-apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif` / `ui-monospace, SFMono-Regular, "SF Mono", Menlo, monospace` |

Two more, for context on how scientific publishers set tables:
`Nature` uses the system stack for both `body` **and** `table`; `eLife` pairs Noto Sans headings with
Noto Serif body.

**Recommended: IBM Plex Sans + JetBrains Mono.**

*Plex Sans* because it is literally what EMBL-EBI and AlphaFold DB render in — same typographic family
as the resources we want to be associated with — **and because its figures are tabular by default**
(see §5.3, the Inter trap).

*JetBrains Mono* for the mono, on measured evidence. Glyphs were rasterised to canvas at 120 px and the
result cross-checked independently against the fonts' OS/2 tables; the two methods agree:

| Font | x-height %em | advance/em | default zero | 1-vs-l | l-vs-I | Licence |
|---|---|---|---|---|---|---|
| **JetBrains Mono** | **55.0** | 0.600 | dotted | 0.296 | **0.210** | OFL |
| Menlo | 54.7 | 0.602 | slashed | 0.250 | 0.225 | **Apple-only** |
| Noto Sans Mono | 53.6 | 0.600 | marked | 0.094 | 0.088 | OFL |
| Roboto Mono | 52.8 | 0.600 | slashed | **0.615** | 0.085 | OFL |
| Fira Mono | 52.7 | 0.600 | dotted | 0.270 | 0.193 | OFL |
| SF Mono | 52.6 | 0.618 | slashed | — | — | **Apple-only** |
| IBM Plex Mono | 51.6 | 0.600 | dotted | 0.166 | 0.070 | OFL |
| Source Code Pro | 47.8 | 0.600 | dotted | 0.216 | 0.201 | OFL |
| Inconsolata | 45.7 | **0.500** | slashed | 0.590 | 0.073 | OFL |
| Courier New | 42.3 | 0.600 | **none** | 0.064 | 0.067 | system |

(`1-vs-l` and `l-vs-I` are mean per-cell bitmap differences on a normalised 26 × 26 grid — higher is
more distinguishable.)

**Why JetBrains Mono wins for us:** the highest x-height in the set at 55.0 % of em — which is the number
that decides whether an 11–12 px accession stays readable — combined with near-best `l`-vs-`I`
separation. Roboto Mono and Inconsolata have by far the most distinct `1` but the **weakest** lowercase-l
vs uppercase-I, and that is the wrong trade for us: HLA alleles and accessions mix `I` and `l` far more
often than they hinge on a bare `1`.

Three traps worth knowing:

- **The `zero` OpenType tag is a toggle, not a promise of a slash** — it *inverts* in Fira Code and
  Inconsolata.
- **Menlo has no GSUB table at all** (zero configurability), and both Menlo and SF Mono are unlicensable
  as webfonts. `Menlo, Consolas, monospace` is a *fallback strategy*, not a webfont strategy.
- **Courier New has no marked zero** (0.000 ink in the counter), and neither does the generic `monospace`
  fallback on most systems. **Always name a real font before falling back.**

Inconsolata is the only narrow face here (0.500 advance vs 0.600) — worth remembering if a sequence track
ever needs ~20 % more residues per line.

**But check it against our offline guarantee first.** `app/main.py` disables FastAPI's `/docs` precisely
because Swagger pulls from jsDelivr at runtime, and the README promises "no CDN". Using Plex therefore
means **vendoring the woff2 files into `app/static/vendor/`** alongside Mol\* — perfectly legal (SIL
Open Font License) but a real weight decision: two weights of Plex Sans plus one of Plex Mono is roughly
150–250 KB. A `@font-face` with `font-display: swap` and a `local()` first source keeps it cheap.

**The honest alternative is to keep the system stack.** It costs nothing, renders as SF Pro / SF Mono on
the demo machine, and SF Mono already has tabular figures and good `0/O` separation. The gain from Plex
is *kinship* — looking like it belongs beside AlphaFold DB — not legibility. Decide on that basis, and
if the demo is the priority, vendoring one mono and keeping the system sans is a reasonable middle.

Whatever is chosen: **keep the current type sizes small and the scale short.** Galaxy runs the entire
application at 13.6 px and does not feel cramped; our 12.5 px table text is slightly under the band and
13 px would read better at no density cost.

Also worth stealing: **CELLxGENE's condensed face for numerals only.** A condensed numeric face lets a
dense metrics row carry more digits per pixel without dropping the UI text size.

### 5.5 Sparklines and in-cell bars — when they earn their place

Tufte's definition: *"A sparkline is a small intense, simple, word-sized graphic with typographic
resolution"* (<https://www.edwardtufte.com/bboard/q-and-a-fetch-msg?msg_id=0001OR>, 27 May 2004; expanded
in *Beautiful Evidence*, 2006). Data-ink ratio and chartjunk are from *The Visual Display of Quantitative
Information* (1983).

**The restraint citation is the one that matters here**: Stephen Few, *Best Practices for Scaling
Sparklines in Dashboards* (Perceptual Edge, 2012). A sparkline's scale is **never visible but always
exists**, so in raw per-sparkline-scaled form they convey **pattern only, no magnitude** — the same shape
in two rows can mean wildly different values. A column of independently-scaled sparklines therefore
*invites a comparison the encoding cannot support*. Datadog ships this as an explicit option
(`y_scale: shared | independent`), which is good precedent for making it a deliberate choice rather than
a silent default.

**Recommendation:** in-cell bars only for **a single column** where relative magnitude is the point
(affinity, expression, allele frequency), **log-scaled**, **paired with the number**, and on a
**shared** scale. Never more than one such column, or the scan collapses.

Precedent is thin but non-zero: EBI's own legacy framework v1.4 carries an explicit carve-out in
`table.data-table` — `/* some images should be stretched, such as sparkline-style gifs */`. cBioPortal
does put SVG and bars in cells, but as **categorical annotation icons, not sparklines**. Tableau has no
native in-cell sparkline at all.

For our table specifically, the pChEMBL-style log transform (§5.3.4) is the better first move: it makes
the four-order affinity spread legible **as a number**, and only if that still fails should a bar be
added behind it.

---

## 6. What to change in NeoFold Edge

### 6.0 What we have now, measured

Read out of the running app at `localhost:8420`, viewport 1440 × 950, after `Run triage`:

| Thing | Measured |
|---|---|
| `main` grid | `732.281px 665.719px`, `gap: 14px` |
| Left column height | 1185 px |
| Right column height | **3590 px** |
| Document height | 3679 px |
| Candidate rows | **60**, each **121–122 px** tall |
| Table cell | 12.5 px / `padding: 7px 9px` / `line-height: 18.75px` / `ui-monospace` |
| `<th>` | 10.5 px, `text-transform: uppercase`, `letter-spacing: 0.525px`, `rgb(139,148,158)` |
| Mol\* canvas | 662 × 428 px |
| `.card h2` | 13 px / 600 / uppercase / `letter-spacing: .06em` / `--muted` |
| Card stack (right) | viewer 1097 px → validation 649 px → MD 527 px → throughput 444 px → confidence 818 px |

**Screenshot in words.** Dark GitHub-grey page. A header strip with the wordmark, two status pills
(`No external calls (0)` green, `GPU not present (local dev)` grey) and a right-aligned amber disclaimer
in ~12 px text. Below, two columns of rounded `#161b22` cards, each opening with a small grey
all-caps header. Left: a controls row, then a five-box funnel
(`50 VARIANTS · 1,890 PEPTIDES · 13 SELF — CUT · 22 PRESENTED · 5 SHORTLIST`), then a scatter plot that is
mostly 50 %-opacity grey dots, then the candidates table. Right: a four-tab strip, a large black Mol\*
canvas, a colour legend, three metric tiles reading `0.991 IPTM / 0.984 PLDDT / 0.989 PTM`, a green
pre-registered-contact panel, and a comparison table. Below the fold, four more full-width cards.

The science on this page is genuinely excellent and unusually honest. The visual problems are all
**hierarchy** problems: almost every label in the interface — section headers, field labels, column
heads, metric keys, panel titles — is rendered in the *same* treatment (10–13 px, uppercase, letter-spaced,
`--muted` grey). When nine different levels share one style, there is no hierarchy, and the eye has
nowhere to land.

---

### 6.1 Change 1 — kill the uppercase transform (it is a correctness bug)

`app/static/index.html` applies `text-transform: uppercase` in **seven** rules: `.card h2`, `label`,
`th`, `.step .l`, `.metric .k`, `.ctitle`, `.subh`.

Measured consequence:

| Authored in HTML | Rendered on screen | Where |
|---|---|---|
| `nM` | **`NM`** | candidates table `<th>` |
| `WT nM` | **`WT NM`** | candidates table `<th>` |
| `ipTM` | **`IPTM`** | `.metric .k` |
| `pLDDT` | **`PLDDT`** | `.metric .k` |
| `pTM` | **`PTM`** | `.metric .k` |
| `Per-residue confidence (pLDDT)` | **`PER-RESIDUE CONFIDENCE (PLDDT)`** | `.subh` |

(Read back off the live page with `element.innerText`, which reports post-`text-transform` text:
`"MODEL CONFIDENCE\nPER-RESIDUE CONFIDENCE (PLDDT)\n50\n70\n90\n100\npeptide…"`.)

`nM` is nanomolar. `NM` is nautical miles, or nothing. `pLDDT` is *predicted* Local Distance Difference
Test and `ipTM` is *interface* predicted TM — the lower-case prefixes are the load-bearing part. We are
one CSS declaration away from getting this right, and every reference implementation in §1 writes them
correctly.

**Do this:**

```css
/* was: 13px/600 uppercase .06em, colour --muted */
.card h2{
  font-size:15px; font-weight:600; letter-spacing:normal; text-transform:none;
  color:var(--text);                 /* full strength, not --muted */
  padding:12px 16px; border-bottom:1px solid var(--line);
}
```

Then delete `text-transform` from `label`, `th`, `.metric .k`, `.ctitle`, `.subh` and keep **one**
uppercase class for the genuinely lowest level, matching the EBI Visual Framework, which uppercases only
at `h4` (**11 px / weight 600**) and nowhere above:

```css
.eyebrow{font-size:11px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
```

Use `.eyebrow` for things that are never scientific notation — `EVIDENCE`, `MEASURED`, `PROJECTED`.
Never on a unit, a metric name, a peptide, a gene, an allele, or an accession.

Resulting scale (sentence case throughout, mirroring AFDB 19/500 and RCSB 18/500 + 16/700):

| Level | Size / weight | Example |
|---|---|---|
| Page title | 16 px / 650 | NeoFold Edge |
| Card header | **15 px / 600**, full-strength, + 1 px rule | Tumour variant triage |
| Sub-head inside a card | 13 px / 600, `--muted` | Per-residue confidence (pLDDT) |
| Eyebrow (only level allowed uppercase) | 11 px / 600 / `.04em` | EVIDENCE |
| Body / cell | 13 px / 400 | — |
| Caption | 12 px / 400, `--muted` | — |

### 6.2 Change 2 — confidence tiles become bands

Today: `0.991 / 0.984 / 0.989`, three decimals, three uppercase keys, no reference frame. Three problems.

**(a) The precision is fake.** Report **two decimals** (`0.99`). Our own `docs/SCIENCE.md` records that a
deliberately mismatched peptide/allele pair scored ipTM **0.988** — so the difference between 0.988 and
0.991 is known, in our own data, to carry no signal. Printing a third decimal invites a reader to compare
values that we have measured to be indistinguishable.

**(b) There is no reference frame.** Give ipTM the AlphaFold 3 bands from §1.3 and render it as a
mini-slider in the RCSB idiom — a banded track, a marker, the value outside the bar, poles labelled:

```
ipTM   [ likely failed │ grey zone │  confident            ]      0.99
        0            0.6         0.8                      1.0
```

Colour the three zones with the house diverging anchors (`#B2182B` / `#A8A9AC` / `#2166AC` from §2.3), or
simply grey the track and colour only the marker. The **grey zone must be labelled with those words** —
it is AlphaFold's own term, and it is the visual answer to "confidence is not accuracy".

**(c) It answers the wrong question, and we know it.** Our `structHint` copy already says the ranking
comes from the binding screen, not from ipTM. So put a one-line eyebrow directly on the tile row —
`MODEL SELF-ASSESSMENT · NOT USED FOR RANKING` — rather than leaving that qualification in a paragraph
several hundred pixels below. Attach the denial to the artefact (§1.2c).

Add the AFDB distribution idea (§1.2a): beside the mean pLDDT, four rows of
`% Very high / High / Low / Very low`, coloured with §2.1. Four lines, and the mean stops being a lie of
omission.

### 6.3 Change 3 — band the pLDDT trace with the canonical palette

`drawPlddt` draws gridlines at **50, 70, 90, 100** — the exact AlphaFold band edges — then fills the area
with flat `#3987e5` and strokes it `#3987e5`. We have drawn the convention and then declined to use it.

- Paint four horizontal background bands between those gridlines at ~10–14 % alpha, and colour the trace
  per-point by its band (or segment the stroke), so the line and the Mol\* cartoon above are the same
  colours for the same reason.
- **Which four hexes depends on the theme** (§4.2). On white use the canonical
  `#FF7D45 / #FFDB13 / #65CBF3 / #0053D6`; on our current `#0d1117` those are the set where "very high"
  drops to 2.84 : 1, so use the dark-tuned `#F2895A / #E5C33F / #7FD4F5 / #6E9BF2` instead. **Define them
  as CSS custom properties from the start** so the chart, the Mol\* colour theme and the legend all read
  from one place and switch together — this is the one change that is materially harder to retrofit.
- Put the thresholds in the legend, AFDB-style: `Very high (> 90)`, not `Very high`.
- Keep the orange peptide highlight band — `#ffa657` is a good, distinct chain accent that does not
  collide with any pLDDT band.

**PAE: keep blue, do not switch to Greens.** Tempting for recognisability, but ColorBrewer `Greens` is
built for white backgrounds — its low end (`#F7FCF5`) is essentially paper. On a `#0d1117` panel the
high-error cells would glare, and the confident bulk of the map would sit at `#00441B`, which is nearly
invisible against a dark surface. Our 13-step blue ramp already runs the correct direction (dark = low
error) and is dark-surface-native. Instead:

- Label the axes the AFDB way — **`Scored residue`** on x, **`Aligned residue`** on y — rather than
  leaving them unlabelled.
- Note asymmetry in the tooltip: say which residue is scored and which is aligned, not just `i ↔ j`.
- Keep `8+ Å` on the ramp; cite AFDB's own "arbitrary cut-off of 31 Å" in the caption so the clipping
  reads as standard practice rather than a fudge.

### 6.4 Change 4 — fix the master–detail geometry

Two measured problems:

1. **The proportions are inverted.** The scan list gets 732 px; the column holding the 3D viewer,
   confidence charts, contact panel and comparison tables gets 666 px. Our left column holds a funnel
   and a list.

   RCSB has the same crowding problem and resolves it by **separating the picture from the
   information**: the structure gets `col-lg-4` (480 px, one third) and everything explanatory gets
   `col-lg-8` (960 px, two thirds). Our 666 px column is being asked to be both at once.

   Flip the ratio to roughly **`minmax(380px, 0.85fr) minmax(560px, 1.15fr)`** (≈ `2fr 3fr`), and —
   more importantly — stop stacking the viewer and the evidence in one column. See (2).

2. **1185 px against 3590 px.** The right column is a 3.6 k-pixel scroll while the left ends a third of
   the way down, leaving a large void beside it. Two fixes, both cheap:
   - `position: sticky; top: 14px` on the left column's inner wrapper so the funnel and candidate list
     stay in view while the evidence column scrolls. This is what makes master–detail feel like one tool
     rather than two stacked pages.
   - Collapse the four standing evidence cards (`Does the screen actually work?`, `Molecular-dynamics
     stress test`, `Throughput on one Nano`, `Model confidence`) into a **tab strip** inside one card —
     the AFDB `Summary / Domains / Annotations / Similar Proteins` pattern, or PDBe's `Model Quality` tab.
     They are alternative views of the same selection, not a sequence; stacking them vertically forces a
     3.6 k-pixel scroll to compare two of them.

Also worth stealing from PDBe (§1.5): a **deferred viewer**. Our Mol\* canvas is 662 × 428 and initialises
on load. A poster frame plus `Load 3D` would make first paint immediate, and it is a one-line honesty win
on a machine with no GPU (`GPU not present (local dev)`).

And from RCSB: the **static-image-first** idea. If the demo is ever screenshotted for a slide, a
pre-rendered PNG of the complex is more reliable than a WebGL canvas.

### 6.5 Change 5 — make the candidate table scannable

Measured: **60 rows × 122 px = ~7,300 px** of table inside `.scroll{max-height:380px}`. Three rows
visible at a time. The cause is the `Assessment` column, which holds a four-line prose paragraph per row
(*"presented at 0.05 %rank (strong binder); germline counterpart is a weak binder, DAI 17.9. The mutation
is TCR-facing, so a DAI near 1 is expected and is not evidence against this candidate."*).

That sentence is good writing in the wrong place. It is **detail-panel copy living in a master-list cell**.

**Target geometry** (dense scientific table, consistent with the reference tools in §5):

| Property | Now | Target |
|---|---|---|
| Row height | 121–122 px | **30–32 px** |
| Font size | 12.5 px | 13 px |
| Cell padding | `7px 9px` | `6px 10px` |
| Visible rows in 380 px | ~3 | ~12 |

**Concretely:**

- Replace the `Assessment` prose with the existing `.tier` pill plus a short mechanism tag
  (`TCR-facing` / `anchor`). Move the sentence into the right-hand detail panel for the selected row,
  where there is room for it. This alone takes 122 px → ~32 px.
- Add `font-variant-numeric: tabular-nums` to `.num` and `.mono`. Digits currently do not align down the
  column, which is the entire point of a numeric column.
- Right-align `nM`, `WT nM`, `DAI`; keep `Peptide` monospaced and left-aligned.
- **Monospace only what benefits**: peptide sequences, HLA alleles (`HLA-C*08:02`), accessions, and
  numeric columns. **Not** the `Variant` column (`KRAS G12D` is a name, not a code) and not prose.
- **`nM` spans four orders of magnitude (39 → 11,616). Use the domain's own fix: a log transform, not a
  bar.** `pChEMBL = −log₁₀(molar affinity)` turns 1 nM into 9.0 and 10 µM into 5.0 — a 5-point linear
  range that sorts correctly, right-aligns cleanly and needs no new visual vocabulary (§5.3.4). Show the
  log value as the sortable column and keep the raw `nM` as a secondary line or on hover.

  An in-cell bar is the fallback, not the first move: **no surveyed tool puts a quantitative bar in a
  data cell** (§3.7.7), and Few's scaling caveat (§5.5) means it must be log-scaled, shared-scale,
  paired with the number and confined to one column. Do the transform first and see whether a bar is
  still needed.

  Independently useful, with real precedent: CELLxGENE's move (§3.2) of putting the **distribution** next
  to the *threshold control* rather than a bar in every row.
- Selected row: replace the `background:#132b47` fill with **`border-left: 4px solid`** plus a
  1-step-lighter background — this is exactly Galaxy's selection treatment (§3.6g). A full-bleed blue
  fill fights the tier pills inside the row.
- Adopt Galaxy's `.help-text` vocabulary (§3.6a) for defined terms — `DAI`, `ipTM`, `%rank`, `anchor`,
  `TCR-facing` get a dashed underline, `cursor: help` and `opacity: .6`. Several of our grey prose
  blocks could then shrink to a sentence plus hover.
- Truncate-plus-tooltip should be the default for long cells, not wrap (Terra, §3.5f). That is what keeps
  a 30 px row 30 px tall.
- Make the header sticky (it already is) but drop the uppercase per §6.1 — `nM` must read `nM`.
- **The list is silently truncated.** `renderRows` does `rows.slice(0,60)` with no "showing 60 of N"
  caption and no sort controls, so a reader cannot tell whether they are looking at the whole screen or
  the top of it, nor re-rank by a different column. Add a count line above the table
  (`60 of 1,890 screened · ranked by predicted affinity`) and make `nM` / `WT nM` / `DAI` sortable. A
  ranked candidate list whose ranking key is implicit is the one thing every tool in §3 gets right.

### 6.6 Smaller things, worth doing while in there

- **The funnel does not look like a funnel.** Five equal-width boxes showing `50 / 1,890 / 13 / 22 / 5`,
  every one at the same weight. Attrition from 1,890 → 22 is 98.8 % and nothing on screen encodes it.
  Apply cBioPortal's three-altitude rule (§3.1a): make **one** number loud — the shortlist — and demote
  the journey to quiet 13 px text. Then either scale each step's inline bar to its count on a log axis,
  or print the `−98.8 %` delta between steps. Also, `13 SELF — CUT` is a **subtraction sitting in a row
  of survivor counts**; without a distinct (inset/negative) treatment the row reads `1,890 → 13 → 22`,
  which is incoherent.
- **Put a histogram behind every threshold control** (CELLxGENE, §3.2). Our two gates — `500 nM` and
  `DAI ≥ 10` — are currently dashed lines on the scatter and nothing else. A 340 × 135-ish mini-histogram
  of the actual screened distribution behind each cutoff shows *where the threshold falls in the data we
  just computed*, which is the difference between a defensible gate and a magic number. We already have
  the distribution in hand at render time.
- **Colour card headers by data provenance** (UCSC, §3.4). Our cards mix three fundamentally different
  epistemic classes and look identical: measured reference (`PDB 8ULN`, GTEx, the crystal contact),
  patient input (the VCF, the HLA allele), and model output (Boltz-2, MHCflurry, the LLM summary). A
  2–3 px coloured rule on the card header — one hue per class, with the key stated once — separates
  "this was measured" from "this was predicted" **structurally**, rather than relying on readers to parse
  every caption. This is the cheapest available fix for the single most important message the app has.
- **Zebra, not borders.** Every reference tool replaces per-row borders with a ~2.4 % luminance step
  (`#ffffff` / `#f9f9f9` on light). Our `td{border-bottom:1px solid #21262d}` is heavier than anything
  measured. On our dark surface the equivalent is `--panel #161b22` against roughly `#1a2029`.
- **Make the state a URL** (§3.5). Dataset + allele + selected candidate + active tab in the query
  string, with a copy-link button. For a demo that has to be repeatable on stage, this is worth more than
  it looks.
- **The scatter is washed out.** Deprioritised points at `opacity .5` in `#6e7681` on `#161b22` are close
  to invisible, so the plot reads as empty. Raise the muted points' contrast or reduce their radius and
  raise opacity — a dense fog of small, visible dots beats a sparse scatter of grey smudges, and the
  point of the chart is that the shortlist is a tiny corner of a crowded field.
- **The amber header disclaimer** (`--warn`, 12 px, right-aligned, 520 px) is doing the work of a legal
  notice in the position of a status bar. **Not one of the four reference tools in §1 runs a persistent
  coloured disclaimer banner** — checked directly, including <https://alphafold.ebi.ac.uk/about>. AFDB
  puts its caveats in the `Model Confidence` panel next to the thing being qualified and in a long-form
  `Help` accordion at the foot of the entry page; RCSB puts them in the validation panel and the linked
  report. The pattern is *caveat adjacent to the artefact*, plus *one expandable for the full text* —
  never a standing banner, because a banner that is always present is read once and then never again.
  Demote ours to `--muted`, keep the warning colour for a single icon, and link it to a `Help`-style
  expandable. Keep the wording — it is better than anything on the reference sites.
- **Round the `±` values consistently.** `2.58 Å predicted / 2.73 Å crystal / ±0.15 Å agreement` is good;
  keep everything in the panel to the same number of decimals.

---

## 7. Sources

**AlphaFold / PDB interfaces**
- AlphaFold DB entry page — <https://alphafold.ebi.ac.uk/entry/AF-P01116-F1>
- AlphaFold DB PAE colour bar asset — <https://alphafold.ebi.ac.uk/assets/img/horizontal_colorbar.png>
- AlphaFold Server — <https://alphafoldserver.com/>
- Mol\* pLDDT colour theme — <https://github.com/molstar/molstar/blob/master/src/extensions/model-archive/quality-assessment/color/plddt.ts>
- RCSB PDB entry 6VXX — <https://www.rcsb.org/structure/6VXX>
- wwPDB validation slider asset — <https://files.rcsb.org/validation/view/6vxx_multipercentile_validation.png>
- RCSB, *Assessing the Quality of 3D Structures* — <https://www.rcsb.org/docs/general-help/assessing-the-quality-of-3d-structures>
- RCSB, *Structure Summary Page* — <https://www.rcsb.org/docs/exploring-a-3d-structure/structure-summary-page>
- PDBe entry 6vxx — <https://www.ebi.ac.uk/pdbe/entry/pdb/6vxx>

**Design systems**
- EMBL-EBI Visual Framework, design tokens — <https://stable.visual-framework.dev/design-tokens/>
- EMBL-EBI Visual Framework, typography — <https://stable.visual-framework.dev/design-tokens/typography/>
- EMBL-EBI colour patterns — <https://www.ebi.ac.uk/style-lab/websites/patterns/colors.html>
- EBI-Framework source — <https://github.com/ebiwd/EBI-Framework>

**Dashboards and design systems surveyed**
- cBioPortal — <https://www.cbioportal.org/> · [`variables.scss`](https://raw.githubusercontent.com/cBioPortal/cbioportal-frontend/master/src/globalStyles/variables.scss) · [`AlterationColors.ts`](https://raw.githubusercontent.com/cBioPortal/cbioportal-frontend/master/packages/cbioportal-frontend-commons/src/lib/AlterationColors.ts) · dark-mode rejection: <https://github.com/cBioPortal/cbioportal/issues/11815>
- CZ CELLxGENE — <https://cellxgene.cziscience.com/collections>
- IGV / igv.js — [`_variables.scss`](https://raw.githubusercontent.com/igvteam/igv.js/master/css/_variables.scss) · [`_color.scss`](https://raw.githubusercontent.com/igvteam/igv.js/master/css/_color.scss)
- UCSC Genome Browser — <https://genome.ucsc.edu/style/HGStyle.css>
- Terra — [`colors.js`](https://raw.githubusercontent.com/DataBiosphere/terra-ui/dev/src/libs/colors.js) · [`table.js`](https://github.com/DataBiosphere/terra-ui/blob/dev/src/components/table.js) · [`job-common.js`](https://github.com/DataBiosphere/terra-ui/blob/dev/src/components/job-common.js) · [`FileProvenance.js`](https://github.com/DataBiosphere/terra-ui/blob/dev/src/workspace-data/provenance/FileProvenance.js)
- Galaxy — [`blue.scss`](https://github.com/galaxyproject/galaxy/blob/dev/client/src/style/scss/theme/blue.scss) · [`states.ts`](https://github.com/galaxyproject/galaxy/blob/dev/client/src/components/History/Content/model/states.ts)
- Mol\* — [`_vars.scss`](https://raw.githubusercontent.com/molstar/molstar/master/src/mol-plugin-ui/skin/base/_vars.scss) · `src/mol-gl/renderer.ts` · <https://molstar.org/viewer/>
- Grafana — `packages/grafana-data/src/themes/createColors.ts` · <https://play.grafana.org>
- Observable Framework — `src/style/abstract-dark.css`, `src/style/plot.css`
- GitHub Primer — <https://primer.style/foundations/color/overview/>
- GOV.UK Design System (the only normative numeric-table guidance found) — `.govuk-table__cell--numeric`
- IBM Carbon data-table — numeric-guidance gap: issue #3831

**Colour, contrast and legibility**
- Piepenbrock et al. 2014, *Human Factors* 56(5):942–51 — doi:10.1177/0018720813515509 (positive-polarity advantage grows as type shrinks)
- Legge et al. 1985, *Vision Research* 25(2):253–65 (the negative-polarity counter-case: cloudy ocular media)
- Longitudinal chromatic aberration / halation — <https://pmc.ncbi.nlm.nih.gov/articles/PMC12962248/>
- *Combining IC50 or Ki Values from Different Sources Is a Source of Significant Noise*, *JCIM* — doi:10.1021/acs.jcim.4c00049

**Uncertainty communication and sparklines**
- Padilla, Kay & Hullman, *Uncertainty Visualization* (2020) — <https://friendly.github.io/6135/papers/Uncertainty_Visualization_Padilla_Kay_Hullman_2020.pdf>
- *Uncertainty in Science is Malleable*, CHI 2025 — <https://dl.acm.org/doi/10.1145/3706598.3713972>
- *Enhancing Uncertainty Communication in Time Series Predictions* — <https://arxiv.org/pdf/2408.12365>
- Tufte, sparkline definition — <https://www.edwardtufte.com/bboard/q-and-a-fetch-msg?msg_id=0001OR> (27 May 2004); *Beautiful Evidence* (2006); *The Visual Display of Quantitative Information* (1983)
- Stephen Few, *Best Practices for Scaling Sparklines in Dashboards* (Perceptual Edge, 2012)

---

## 8. Limits of this research

Stated so nobody over-trusts a number in here.

- **No screenshots exist for §3.** The dashboard survey is DOM geometry and source values, gathered with
  `getComputedStyle` / `getBoundingClientRect` in a headless tab. The measurements are reliable; the
  *feel* of those interfaces is not captured. §1, §4 and §6 were observed visually as well.
- **Two tools are stylesheet-only.** UCSC hgTracks sits behind a Cloudflare Turnstile challenge, which
  was not circumvented; IGV's web app never instantiated its track DOM. Both sets of values come from
  served CSS/SCSS — authoritative, but not confirmed against a rendered page.
- **Benchling, Schrödinger LiveDesign/Maestro and Dotmatics are absent.** None has a login-free demo and
  the agent tasked with their documentation did not return. Nothing in this document describes them.
  This leaves one question genuinely unanswered, and it is a relevant one: **how does a commercial
  discovery platform distinguish a *predicted* property column from a *measured* one, and does it
  surface model version or applicability-domain warnings at the cell level?** Every tool surveyed here
  shows confidence in *observed* data or in a single model's output; none shows "this column came from
  model v3.2, which was not trained on peptides like this one." Worth a separate pass.
- **Some values are flagged unverified by the researchers who gathered them**: Datadog / Tableau /
  Figma UI3 dark-theme hexes (no published values exist — do not invent them); Linear's `#08090a`,
  `#0f1011`, `#161718` are verified from shipped CSS but the widely-circulated `#191a1b` / `#28282c` are
  community reconstructions; Material's 15.8 : 1 figure is from a secondary source; Tufte page numbers
  (pp. 46–63, p. 93) are secondary and unconfirmed against the books; four Terra *docs* pages are cited
  from search summaries because `support.terra.bio` returned 403.
- **No survey exists** on dark-vs-light preference specifically among scientists or bioinformaticians.
  That is a real gap in the literature, not a failed search — the §4 recommendation rests on measured
  contrast, published polarity research, and what peer tools actually ship.
- **`#6E9BF2 / #7FD4F5 / #E5C33F / #F2895A`** (the dark-mode pLDDT overrides) are *derived*, not a
  published standard. They preserve hue order and land in a 7–11 : 1 band; they are not what anyone else
  ships, because nobody else ships this palette on dark. Treat them as a starting point and check them
  against the real viewer.
</content>
</invoke>
