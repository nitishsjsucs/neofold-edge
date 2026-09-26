# NeoFold Edge — agent briefing

**Audience: an AI agent asked to produce something about this project** — a slide deck, a
one-pager, a script, a poster, a written summary. This document exists so you never have to guess
a number, infer a claim, or reach for a phrase the project has deliberately rejected.

**Read the constraints in §1 before writing a single slide.** They are the part most likely to be
got wrong, and getting them wrong is worse than being vague.

---

## 0. How to use this document

| If you are… | Read |
|---|---|
| Writing a deck or script | §1 constraints → §2 what it is → §3 narrative → §5 numbers |
| Making a claim about performance | §5 only. Every figure there carries its provenance. |
| Choosing images | §8 asset inventory |
| Anticipating questions | §7 prepared answers |
| Tempted to write a tagline | §9 forbidden phrasings, first |

**Three rules that override everything else:**

1. **Never invent a number.** Every quantitative claim in §5 is traceable to a file in this repo.
   If a figure you want is not in §5, it does not exist — say less instead.
2. **Never upgrade a hedge.** "Predicted" does not become "shown". "Shortlist" does not become
   "vaccine". "Research candidate" does not become "target". The hedges are load-bearing.
3. **Volunteer the failures.** This project's differentiator is that it measured itself and
   published what did not work. A deck that hides §6 is a worse deck, not a safer one.

---

## 1. Hard constraints

### 1.1 What this project is NOT

| Do not say | Because |
|---|---|
| "designs cancer vaccines" | It produces a ranked shortlist of research candidates. `construct.py` emits amino acids only, never nucleotides. |
| "finds neoantigens" | No neoantigen has ever been demonstrated by this system. It concentrates candidates; laboratory work identifies. |
| "diagnoses" / "treats" / "patient outcome" | It is research prioritisation software. Not a diagnostic, not a device, not a therapy. |
| "cures" anything | See above, and see §7 on the clinical context. |
| "validated" (unqualified) | The *screen* is validated against assay data. The *structures* are validated against crystals. The *pipeline end to end* is not validated against anything. |
| "AI cured a dog" | See §3.2. |

### 1.2 Precision rules

- **Structure accuracy is 1.41 Å.** There is a 0.42 Å figure in the project's history. It is a
  training-set number and must never be quoted as the accuracy.
- **Confidence scores are never a ranking signal.** Any slide implying ipTM/pLDDT indicates
  correctness contradicts the project's central finding.
- **Multi-node throughput is a projection.** One Nano existed. Label it.
- **The MD run cannot support the salt-bridge claim.** See §6.
- Say **"the Nano"**, not "the box".

---

## 2. What it is, in one paragraph

NeoFold Edge is a private, on-premise AI workstation that turns a tumour variant file into a small,
ranked, explained shortlist of neoantigen research candidates. It runs entirely offline on one
HP ZGX Nano (NVIDIA GB10 Grace Blackwell): a CPU screening stage narrows roughly 1,890 candidate
peptides to a couple of dozen in seconds, a GPU stage predicts 3D peptide–HLA structures and
measures an atomic contact specified in advance from a published crystal structure, and a local
language model writes a plain-language evidence summary that is machine-checked against the facts
it was given. Nothing leaves the machine.

**The one-liner for a slide:** *takes a tumour's DNA and picks the targets a cancer vaccine should
aim at — on one small computer, completely offline.*

---

## 3. The narrative that works

### 3.1 Open with the product, then the story

A viewer who leaves after 45 seconds should be able to say what the project is. Lead with the
one-liner, *then* tell the Rosie story. Leading with Rosie alone means the audience has watched a
dog-cancer documentary and does not know what was built.

### 3.2 The Rosie case — verified details only

- **Paul Conyngham**, Australian data analyst / ML engineer, **no biology background**.
- Dog **Rosie**, five-year-old rescue, **mast cell tumour** on her leg, tennis-ball sized,
  diagnosed 2024. Chemotherapy slowed but did not shrink it.
- He paid several thousand AUD out of pocket to sequence her tumour at the
  **UNSW Ramaciotti Centre for Genomics** (computational biologist Martin Smith).
- Used **ChatGPT** to identify neoantigens and generate the RNA sequence, **AlphaFold** to predict
  protein structures.
- **UNSW RNA Institute** (Pall Thordarson) for the chemistry; **University of Queensland** for
  veterinary administration.
- Personalised **mRNA vaccine in lipid nanoparticles**. First injection **December 2025**. By
  **mid-March 2026** the largest tumour had shrunk **~75%**.

**The caveats are mandatory, not optional.** State them:
- One dog, not a controlled study.
- Mast cell tumours behave unpredictably.
- **Given alongside an immune checkpoint inhibitor**, so the response cannot be cleanly attributed.
- An oncologist (Justin Stebbing) publicly urged exactly this caution.

**The transferable point:** the workflow is now within reach of someone outside the field, and it
failed to generalise for reasons that are fixable — expertise, speed, and the fact that the cloud
tools he used for a *dog* become a regulated disclosure the moment the patient is human.

Sources: [The Scientist](https://www.the-scientist.com/chatgpt-and-alphafold-help-design-personalized-vaccine-for-dog-with-cancer-74227),
[The Conversation](https://theconversation.com/a-man-used-ai-to-help-make-a-cancer-vaccine-for-his-dog-an-oncologist-urges-caution-278735).

### 3.3 Analogies that carry weight

| Concept | Analogy |
|---|---|
| The shortlist problem | A library of 1,890 identical-looking books; ~51 are worth reading; you may take five; reading one takes three weeks. |
| Anchor vs TCR-facing | The peptide sits in the HLA groove like a hot dog in a bun. Anchor residues point *down into the bun* — the immune cell, looking from above, never sees them. |
| Why glycine cannot bind | It is not a weaker grip. Glycine has **no side chain** — there is no hand to grip with. |
| Confidence ≠ correctness | A tour guide who has walked the same route ten thousand times, asked about a street they have never seen. Same confident tone. |
| The self-peptide catch | Looking for a suspect with a distinctive tattoo, and finding one — but the tattoo is a wedding ring. It is on everyone. |

---

## 4. Where to find things

| File | What it holds |
|---|---|
| `README.md` | Public front door; the Rosie framing, headline results, screenshots |
| `docs/PROBLEM.md` | The biology, base rates, why the obvious filters fail |
| `docs/ARCHITECTURE.md` | Pipeline, module map, API, interface-design provenance |
| `docs/HARDWARE.md` | GB10 spec, the edge argument in full, the power fault, scaling |
| `docs/BENCHMARKS.md` | Every measurement with methodology |
| `docs/SCIENCE.md` | Claim boundaries and all twelve documented errors |
| `BUILD-GUIDE.md` | Verified Nano install, every bug and fix |
| `PITCH.md` | 4-minute demo script, choreography, judge Q&A |
| `benchmarks/*.json` | The raw measurements |
| `video/narration.txt` | The demo-video script |
| `docs/img/` | 28 visual assets — see §8 |

---

## 5. Every number, with provenance

> Provenance tags: **[M]** measured on our hardware · **[C]** cited from a publication ·
> **[P]** projected, never observed. If a figure you want is not here, it does not exist.

### 5.1 The three headline figures

| Claim | Figure | Tag | Source |
|---|---|---|---|
| The screen ranks usefully | **AUC 0.777** (Bjerregaard) / **0.759** (TESLA) | [M] | `benchmarks/auc.json`, `benchmarks/tesla_validation.json` |
| Structures are accurate | **1.41 Å** median, held out | [M] | `benchmarks/holdout_structures.json` |
| Runs offline on one Nano | screen **8.8 s** → fold **64 s** → explain **4 s** | [M] | `benchmarks/measured.json` |

### 5.2 Screen validation — Bjerregaard 2017

n = **1,947** neopeptide–HLA pairs · **53** responders · base rate **2.72%** · 13 pooled studies.

| Metric | AUC |
|---|---|
| Presentation score | **0.777** |
| Predicted affinity (nM) | 0.755 |
| Predicted %rank | 0.744 |
| Wild-type affinity | 0.678 |
| **DAI (differential)** | **0.592** — near chance |

Stratified by mutation position — **this is the argument that killed DAI**:

| Position | n | Responders | Presentation AUC | DAI AUC |
|---|---|---|---|---|
| Anchor (P2/PΩ) | 481 | 15 | 0.719 | **0.660** |
| TCR-facing | 1,466 | 38 | **0.801** | 0.577 |

Strata with <5 responders are noise — the 11-mer AUC of 0.233 rests on **one** positive. Do not
put it on a slide without that caveat.

### 5.3 Screen validation — TESLA 2020 (the harder test)

n = **608** · **37** immunogenic · base rate **6.09%** · negatives are **same-patient hard
negatives** nominated by 25 expert pipelines.

| Metric | AUC |
|---|---|
| OUR %rank | **0.7624** |
| OUR presentation score | **0.7592** |
| OUR predicted affinity | 0.7547 |
| TESLA **measured** affinity (n=503) | 0.7473 |
| TESLA NetMHCpan affinity | 0.7473 |
| TESLA binding stability | 0.6855 |
| TESLA tumour abundance | 0.6428 |
| TESLA foreignness | 0.5293 |
| **TESLA agretopicity** | **0.4117 — below random** |

**The reading that matters:** our *predicted* score (0.759) matches TESLA's *experimentally
measured* affinity (0.747). This does **not** mean prediction beats experiment. It means binding
affinity, however obtained, is not a strong discriminator — the ceiling is the biology.

Precision at depth (TESLA, ranked by our presentation score):

| k | Hits | Precision | Enrichment |
|---|---|---|---|
| 10 | 1 | 10% | 1.64× |
| **25** | **8** | **32%** | **5.26×** |
| 50 | 13 | 26% | 4.27× |
| 100 | 18 | 18% | 2.96× |

Bjerregaard, same ranker: k=25 → **16%** (5.9×); k=50 → 14%; k=100 → 14%.

### 5.4 Filter rules as enrichment over base rate

| Rule | Kept | Found | Recall | Enrichment |
|---|---|---|---|---|
| affinity ≤ 50 nM | 545 | 33 | 62.3% | **2.224×** |
| DAI ≥ 10 alone | 204 | 10 | 18.9% | 1.801× |
| %rank < 0.5 | 978 | 46 | 86.8% | 1.728× |
| presentation ≥ 0.50 | 1,061 | 46 | 86.8% | 1.593× |
| **OURS** (presentation ≥ 0.10 AND ≤ 500 nM) | 1,370 | 49 | **92.5%** | 1.314× |
| **DAI ≥ 2 alone** | 495 | 13 | 24.5% | **0.965× — worse than random** |

**⚠ Say "as a standalone gate" every time you say this.** [M] Conditional on presentation
(within the 1,370 our rule keeps, 3.58% baseline), a strict **DAI ≥ 10** reaches **4.90%**
precision on 204 candidates — the differential is a weak *re-ranker*, and our mistake was the
role and the threshold, not the whole idea. **And** anchor mutations out-precision TCR-facing
ones there (**4.23%** vs **3.37%**), which contradicts the mechanism in §5.4. Small *n*; we
claim nothing from it. If a slide says "DAI does not work" with no qualifier, it overstates
what we measured — fix the slide. Source: `benchmarks/screen_validation.json` →
`conditional_on_presentation`.

Our rule is deliberately loose: lower enrichment, but it keeps **92.5%** of responders against
62.3% for a 50 nM cut. A triage stage should be recall-first — a candidate discarded there cannot
be recovered by any downstream evidence.

### 5.5 Structure accuracy

12 peptide–HLA crystals, split on **Boltz-2's 2023-06-01 training cutoff**.

| Set | n | Median peptide backbone RMSD |
|---|---|---|
| Pre-cutoff (possibly memorised) | 3 | 1.01 Å |
| **Post-cutoff (held out)** | **9** | **1.41 Å** — all under 2 Å |

Held-out spread: best **0.87 Å** (9WK0), worst **1.87 Å** (9XME). Crystals themselves were solved
at 1.49–2.49 Å, so our error is comparable to the reference's own uncertainty.

**The central finding:** across those nine, ipTM spans **0.011** (0.9776–0.9880) while real error
spans **0.99 Å**. Correlation **r = −0.23**. The worst prediction scores *higher* than the best.

Four further demonstrations that confidence does not discriminate:
- Deliberately **wrong allele** scored ipTM **0.988** vs the correct allele's 0.987
- Three mutant/germline pairs differ in the third decimal
- Full pMHC:TCR complex scored **0.947** — *lower* than peptide-only
- Wild-type TCR control (receptor does **not** recognise it) was indistinguishable

Original anchors, both **pre-cutoff, do not quote as accuracy**: 6ULN 0.509 Å, 3GSO 0.321 Å.

### 5.6 Ternary pMHC:TCR complex

812 residues, 5 chains, **133 s** [M]. ipTM 0.9468, pLDDT 0.9687.
Cα RMSD: peptide **0.32 Å**, β2m 0.46 Å, TCR α **1.42 Å**, TCR β **1.50 Å**.

The receptor is **TCR9d**, patient 3995, from **Sim et al., PNAS 2020** — *not* Tran *NEJM* 2016,
which reported the TIL therapy and the epitopes but not this receptor. Retrospective: 6ULN (2020)
may be in training data.

### 5.7 The pre-registered contact

KRAS G12D `GADGVGKSA` on HLA-C\*08:02. Asp at peptide position 3 → Arg156.

| | |
|---|---|
| Predicted | **2.58 Å** |
| Crystal (6ULN) | **2.73 Å** |
| Agreement | **±0.15 Å** |

The germline peptide has **glycine** there — no side chain, so the contact is chemically
impossible, not merely weaker. The contact was specified **before** prediction.

### 5.8 Hardware and performance

| | Value | Tag |
|---|---|---|
| Device | NVIDIA GB10 Grace Blackwell, HP ZGX Nano | — |
| CPU | 20-core Arm (10× Cortex-X925, 10× Cortex-A725) | vendor |
| Memory | 128 GB LPDDR5x unified (**121 GB** visible) | vendor / [M] |
| Memory bandwidth | up to 273 GB/s | vendor |
| Vendor AI rating | **1,000 TOPS FP4** (HP never says "1 PFLOP") | vendor |
| **Sustained BF16** | **53.4 TFLOPS** | [M] |
| OS / driver / CUDA | Ubuntu 24.04.5 aarch64 / 580.173.02 / 13.0 | [M] |
| Peak GPU utilisation | **96%** | [M] |
| Peak power | **38 W** (42.2 W on the 812-residue complex) | [M] |
| Idle power | 3.5 W | [M] |
| Peak temperature | **46 °C** | [M] |
| Process GPU memory | 2,304 MiB | [M] |

**Timings [M]:**

| Job | Time |
|---|---|
| Structure, 383 residues, cached MSA | **64.3 s** mean (n=7, range 62–66) |
| Same, single-sequence | 55 s |
| Same, MSA generated online | 132 s |
| G-domain crop, 189 residues | 44 s |
| Ternary complex, 812 residues | 133 s |
| **Batched: 5 in one process** | **180 s total = 36.0 s each → 100/hour, 1.79×** |
| Screen 1,890 candidates | **8.8 s** (~430 peptides/s, CPU, Apple M-series) |
| Same on the Nano | 2.5–5.7 s observed |
| Offline proof (egress blocked) | 64 s |

Half of each structure job is **fixed overhead** (~32 s: process start, 2.3 GB checkpoint load,
output writing). That is what batching amortises.

**Local LLM [M]:** qwen3:8b via Ollama CUDA, **100% GPU**, 5.7 tok/s, 91% utilisation, 29.3 W,
2,411 MHz. `keep_alive: 0` frees the GPU in ~3 s.

**Scaling:** 1 Nano = 100 candidates/hour batched [M] (56/hour one at a time [M]).
2 → **200** (100% efficient), 4 → **367** (92%) — **[P], never observed.** Four nodes is 367 and
not 400 because a 22-candidate shortlist divides into ⌈22/4⌉ = 6 rounds with the last one half
idle: 22/24 = 92% before any network effect. Quote 367. The dashboard computes the same number.
Published DGX Spark cluster work measures NCCL all-reduce at ~10.2 GB/s (≈40% of raw RDMA), which
matters for distributed training and little for a queue of independent jobs.

### 5.9 The demo funnel

| Stage | Count |
|---|---|
| Somatic variants in | 50 |
| Candidate peptides (8–11-mers) | **1,890** |
| Cut as verbatim self peptides | **13** |
| Predicted presented | **22** |
| Shortlisted for structure | **5** |

MHCflurry scores mutant **and** germline, so 1,890 candidates = **3,780** predictions.
Self-similarity searches **20,431** reviewed human proteins.

### 5.10 Clinical context (for honesty, not promotion)

| | |
|---|---|
| KEYNOTE-942 (mRNA-4157 + pembrolizumab) | improved RFS at **two-sided p = 0.053**, CI crossing 1.0 |
| BioNTech randomised Phase 2, this modality | **terminated on futility, August 2026** |
| Autogene cevumeran (pancreatic) | median **9.4 weeks** surgery → first dose (range 7.4–11.0) |
| Same trial | **only 1 of 19 patients** had too few neoantigens to manufacture |

That last row is the best argument for the project: candidate *generation* is almost never the
failure point. **Prioritisation is.**

### 5.11 Codebase

125 tests passing · 12 modules, 2,493 lines · 16 API endpoints · ~12,700 lines of sourced research
notes · 25 visual assets.

---

## 6. The twelve documented errors

**Do not hide these — they are the strongest material in the project.** A judge who catches a
hidden flaw is fatal; one who hears you volunteer it is convinced. The four marked ★ are the ones
to say out loud in a short talk.

| # | Error | How it was caught | Resolution |
|---|---|---|---|
| ★1 | Shipped a filter **worse than random as a standalone gate** — DAI ≥ 2, enrichment **0.965×** | Validation against 1,947 assay outcomes | Demoted to an annotation. The differential mostly detects *anchor* mutations, which are the ones T-cells are least likely to see. **Qualify it:** conditional on presentation, DAI ≥ 10 does lift precision 3.58% → 4.90% (n=204). Wrong role and threshold, not zero signal. |
| ★2 | Accuracy claim was **3× optimistic** — we quoted 0.42 Å, which must **never** be used as the accuracy | Both validation crystals predate the training cutoff, so that is a training-set figure | Re-measured on 9 held-out structures: **1.41 Å** |
| ★3 | Labelled **a normal human peptide** a tumour target | Built the self-similarity filter afterwards | `ICDFGLARV` (KIT D816V) is verbatim ERK2; the DFG motif is conserved across the kinome. **Kept in the demo as a negative control.** |
| 4 | Near-self metric was **vacuous** | It flagged everything | Every missense neoepitope is one mismatch from its own germline peptide. Now excluded. |
| ★5 | A **test asserted a conclusion our own data refuted** | The wild-type TCR control | "The model knows recognition is harder" held equally for a complex the receptor does *not* recognise. Test **deleted**, not repaired. |
| 6 | The **LLM asserted three unsupported claims** | Added a claim checker after the first run | It passed numeric verification while writing that ipTM "supports reliability" — already disproved five times. All three phrases are regression tests. |
| 7 | MD **"rejected" a validated epitope** at 7 Å | — | Implicit solvent has no periodic box, so the complex tumbles; naive RMSD measured the tumbling. Fixed with Kabsch superposition. **Same bug class found twice, in two modules.** |
| 8 | TCR appeared **72 Å out of place** | — | 6ULN's biological assembly applies operator 1 to pMHC and operator 2 to the TCR. Fixed with `gemmi.make_assembly`. |
| 9 | **Cited the wrong paper** for our own TCR | Extracted CDR3β from our own predicted chain | 6ULN's receptor is TCR9d (Sim 2020, patient 3995), not Tran 2016 (patient 4095). |
| 10 | **Misdiagnosed a hardware fault twice** | The user asked the question that solved it | Blamed cuEquivariance, then a teammate's benchmark. Actual cause: GPU auto-boosts to 2,522 MHz and browns out. Fix: `sudo nvidia-smi -lgc 0,2450` (does **not** survive reboot). |
| 11 | Conflated **two different "foreignness" metrics** | — | TESLA foreignness (pathogen similarity) ≠ our self-similarity (human proteome identity). Reverted. |
| 12 | Demo inputs had **defects** | Auditing our own data | A GRCh37 coordinate in a file declaring GRCh38; 13 synthetic rows with impossible chromosome positions. No effect on results — which itself reveals the coordinates are decorative. |

### 6.1 Two limits we place on our own headline results

**The MD run must not be used to support the salt-bridge claim.** Generalised-Born implicit solvent
over-stabilises salt bridges by **3–4 kcal/mol**, and the documented failure is specifically in
hydrogens on charged nitrogens — Arg156's guanidinium is exactly the atom type at fault. At 310 K
that is a ~130× population over-weighting. OpenMM's `GBSAOBC2Force` also defaults to zero ionic
strength. This caveat is in the tool's own output.

**Our three MD replicates agree closely, and that is not reassuring.** Sub-10 ns agreement is the
published signature of *undersampling*. Knapp *et al.* 2018 put 100 ns as the state of the art for
this system class; we run ~1 ns, **100× below the floor**, against measured complex half-lives of
10³–10⁵ seconds.

---

## 7. Prepared answers

| Question | Answer |
|---|---|
| **Does this make a vaccine?** | No. A ranked, explained shortlist for a researcher. A construct is assembled — amino acids only, never nucleotides — and the honest context is that BioNTech terminated a randomised Phase 2 of this modality in August 2026. |
| **Isn't Boltz just AlphaFold?** | Same family of problem. Boltz-2 is **MIT-licensed with open weights**, which is why it runs on this device at all — AlphaFold 3's weights are non-commercial and not approved for clinical use. |
| **How do you know the HLA type?** | We don't, and you cannot get it from a VCF. We take it as input. Real pipelines type it from sequencing reads; that is out of scope and we say so. |
| **What's your false-positive rate?** | At the top 25 we are right **16–32%** of the time against a base rate of 2.7–6.1%. So **68–84% of our top candidates are still wrong.** Five times better than chance, not correct. |
| **Why not the cloud?** | Not cost — moving a whole-exome pair is about **$5**. It is governance: local compute *removes* a data-use agreement and an institutional certification step rather than satisfying one. |
| **Isn't 1.41 Å just memorisation?** | That is specifically the **held-out** figure — everything deposited after the June 2023 cutoff. Our memorised-set number is 0.42 Å and we quote the worse one. |
| **What aren't you modelling?** | Tumour RNA expression (worth 11–13 precision points — the most serious omission), clonality/VAF, pMHC stability, TAP transport, multiple HLA alleles, class II. Ranked by measured effect size. |
| **Rosie's owner used the cloud and it was fine.** | For a dog, yes — that is the point. Animal genomes are not controlled-access human data. Run the same workflow on a person and those tools become an external processor holding an identifiable genome. |
| **Are you claiming AI cured that dog?** | No. One dog, not a controlled study, and given alongside a checkpoint inhibitor, so the response cannot be cleanly attributed. What it proves is that the *workflow* is within reach of someone outside the field. |
| **Is "edge" doing real work here?** | Not latency — this is batch, and any edge pitch claiming real-time for a batch workload deserves suspicion. It buys **locality**: the computation happens where the controlled-access data already sits, in a 38 W box that fits in a cupboard. |

---

## 8. Visual assets

All in `docs/img/`. **Prefer these over generating new artwork** — they are real output.

### Screenshots (PNG, 1600px wide unless noted)

| File | Shows |
|---|---|
| `app-full.png` | **3000×6738** full-page capture of the whole dashboard. Use with `video/app-regions.json`, which gives measured fractional coordinates for 16 named elements (funnel, table, flagged row, ROC curves, enrichment bars…). Best source for cropping any panel precisely. |
| `dashboard.png` | Dashboard overview |
| `candidates.png` | Funnel, screening landscape, and the candidate table — **includes the `ICDFGLARV` row flagged `self peptide`** |
| `structure.png` | 3D peptide–HLA complex, ipTM band, and the 2.58/2.73 Å contact panel |
| `evidence-roc.png` | ROC curves for both benchmarks, precision@k, and the enrichment bars with the below-random rule in red |
| `evidence-holdout.png` | Confidence vs measured error — the flat cloud, r = −0.23 |
| `evidence-plddt.png` | pLDDT trace with AlphaFold bands, plus the PAE matrix |
| `evidence-md.png` | MD contact-persistence traces |
| `evidence-scaling.png` | Measured vs projected throughput |

### Diagrams (SVG, light + dark variants via `<picture>`)

`diagram-{overview,gates,governance,pipeline,timeline,hardware,scaling}.{light,dark}.svg`

Regenerate any of them with `python3 scripts/diagrams.py`. Regenerate screenshots with
`./scripts/screenshots.sh` (needs the app running) regenerates **8 of the 16** PNGs:
`dashboard`, `candidates`, `structure`, and the five `evidence-*`. Each is driven by a deep-link
URL, so they are reproducible without hand-driving the UI.

The other three — `app-full`, `app-holdout`, `app-summary`, which the **video** uses — are *not*
in that script. They are full-page captures taken at **1500 CSS px wide, device scale 2**, and the
element positions inside them are recorded in `video/app-regions.json` (measured with
`getBoundingClientRect`, see `scripts/measure_regions.md`). The video build asserts every cue's
region exists there, so if you re-capture at a different viewport the regions must be re-measured
or the build fails loudly. **Do not re-capture these casually.**

---

## 9. Forbidden phrasings

Copy this list into any review pass.

- ❌ "The normal protein is invisible" — it is a weak binder at 1.055 %rank
- ❌ "Sub-Ångström accuracy" — that is the training-set number
- ❌ "The model is confident, so it's right" — disproved five times
- ❌ "49× stronger" without saying it is the 9-mer; the 10-mer is 22.6×
- ❌ "Cloud egress is prohibitively expensive" — it is ~$5; a judge with an AWS bill will laugh
- ❌ "DNA is one of HIPAA's 18 identifiers" — flatly false; item (P) is fingerprints and voice prints
- ❌ "Regulations prohibit genomic data in the cloud" — false; NIH contemplates cloud use, and all three hyperscalers host dbGaP-authorised workloads
- ❌ "Gymrek showed any genome can be re-identified" — overstated; male subjects, Y-STRs, genealogy-database dependent
- ❌ "1 PFLOP" as our capability — HP says 1,000 TOPS FP4; the petaFLOP figure is NVIDIA's and carries a *"with sparsity"* qualifier. Our workload is BF16. **53.4 TFLOPS is our number.**
- ❌ Anything with *cure*, *treat*, *patient outcome*, *breakthrough*
- ❌ "the box" — say **"the Nano"**

---

## 10. Context

| | |
|---|---|
| Event | **Edge AI Hack 2026**, San José State University, sponsored by HP |
| Final | Saturday **26 September 2026** |
| Format | 3–4 minute live demo + judge questions |
| Hardware | HP ZGX Nano (NVIDIA GB10), accessed over SSH |
| Repository | <https://github.com/nitishsjsucs/neofold-edge> (public) |
| Scope | Hackathon showcase of the Nano's compute capability. **Not used in any biological trial.** |

### Licensing of components

| Component | Licence | Role |
|---|---|---|
| Boltz-2 | MIT | structure prediction |
| MHCflurry 2.2.1 | Apache 2.0 | peptide–MHC binding |
| OpenMM | MIT / LGPL | molecular dynamics |
| Mol\* 5.11.0 | MIT | 3D viewer (vendored, offline) |
| gemmi | MPL 2.0 | structural file handling |
| qwen3:8b via Ollama | Apache 2.0 | local summaries |

Benchmark data: Bjerregaard *et al.* 2017 (CC BY), Wells *et al.* 2020 (TESLA), UniProt, GTEx v10,
RCSB PDB.
