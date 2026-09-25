# NeoFold Edge — Verified Build Guide (HP ZGX Nano / GB10)

**Status:** Phase 0 viability gate **PASSED**. Boltz-2 runs end-to-end on the Nano, offline, producing real 3D structures in under a minute.
**Verified:** 2026-09-22/23 on `zgx-81a8` by direct SSH execution. Everything in §1–§5 was *run*, not looked up.
**Hackathon:** Edge AI Hack 2026, final Sat Sept 26.

---

## 0. TL;DR

| Question | Answer |
|---|---|
| Does Boltz-2 run on the GB10? | **Yes.** 383-residue peptide–HLA complex in **58 s wall / 27 s inference**. |
| Does it run offline? | **Yes** — single-sequence mode (`msa: empty`), no MSA server, no cloud. |
| Real GPU work? | **Yes** — peak **96% GPU util, 38 W**, 2.3 GB GPU memory. |
| Do I need the community GB10 fork? | **No.** Stock `pip install boltz==2.2.1` + 4 fixes below. |
| Do I need sudo? | **No** — I found a no-sudo workaround for the one blocker that needs root. |
| Can Boltz confidence rank candidates? | **No.** See §6 — this is the single most important finding. |
| **How accurate is it, really?** | **0.32 Å** (A\*02:01 vs 3GSO) and **0.51 Å** (C\*08:02 vs 6ULN) peptide backbone RMSD. See §6A. |
| Does the screen work? | **Yes.** MHCflurry ranks both published KRAS G12D epitopes **#1 and #2 of 38**. See §6B. |

---

## 1. Verified machine state

```
host      zgx-81a8        Ubuntu 24.04.5 LTS, aarch64 (ARM64)
GPU       NVIDIA GB10     compute capability 12.1 (sm_121), driver 580.173.02
CUDA      13.0            /usr/local/cuda/bin (NOT on PATH by default)
memory    121 GB unified  ~116 GB free
disk      3.6 TB          3.4 TB free
CPU       20 cores
python    3.12.3          system, PEP-668 managed -> venv required
docker    available       hp1 now in docker group (works)
sudo      PASSWORD REQUIRED  <- constrains everything; see §3.4
```

Measured raw throughput, torch 2.14.0+cu132: **43.4 TFLOPS bf16** (8192³ matmul).

---

## 2. The install that works

Copy-paste verbatim. Takes ~15 min, ~10 GB download.

```bash
# 1. venv (PEP-668 means you cannot pip install to system python)
mkdir -p ~/neofold && cd ~/neofold
python3 -m venv .venv-boltz
. .venv-boltz/bin/activate
pip install --upgrade pip wheel setuptools

# 2. PyTorch for ARM64 + CUDA 13. cu132 is the newest stable and works on the 13.0 driver.
pip install "numpy<2.0" torch==2.14.0+cu132 \
  --index-url https://download.pytorch.org/whl/cu132 \
  --extra-index-url https://pypi.org/simple

# 3. gemmi: Boltz pins ==0.6.5, which has NO aarch64 wheel and needs python3-dev to
#    compile. 0.7.5 HAS a prebuilt aarch64 wheel. Install it first, then Boltz --no-deps.
pip install gemmi==0.7.5
pip install boltz==2.2.1 --no-deps
pip install hydra-core==1.3.2 pytorch-lightning==2.5.0 "rdkit>=2024.3.2" dm-tree==0.1.8 \
  requests==2.32.3 "pandas>=2.2.2" types-requests einops==0.8.0 einx==0.3.0 \
  fairscale==0.4.13 mashumaro==3.14 modelcif==1.2 wandb==0.18.7 click==8.1.7 \
  pyyaml==6.0.2 biopython==1.84 scipy==1.13.1 numba==0.61.0 scikit-learn==1.6.1 \
  chembl_structure_pipeline==1.2.2

# 4. cuEquivariance for CUDA 13 (Boltz's [cuda] extra pins the CUDA-12 build, which
#    is wrong for this machine). cp312 aarch64 wheels exist.
pip install "cuequivariance-torch>=0.9.1" "cuequivariance-ops-torch-cu13>=0.9.1"

# 5. Python headers WITHOUT sudo (Triton needs Python.h to build its CUDA shim)
cd ~ && mkdir -p pkgtmp pylocal && cd pkgtmp
apt-get download libpython3.12-dev python3.12-dev     # no root needed to DOWNLOAD
for d in *.deb; do dpkg-deb -x "$d" ~/pylocal; done
```

Then **every** Boltz run needs these three lines:

```bash
. ~/neofold/.venv-boltz/bin/activate
export PATH=/usr/local/cuda/bin:$PATH
export CPATH=$HOME/pylocal/usr/include/python3.12:$HOME/pylocal/usr/include
```

And **always** pass `--num_workers 0` (see §3.1).

> If you can get the root password, `sudo apt install python3.12-dev build-essential` replaces
> step 5 and also lets you use the correct `gemmi==0.6.5` pin. Cleaner, but not required.

---

## 3. The four bugs I hit, and the fixes

### 3.1 Silent dataloader deadlock — the dangerous one
**Symptom:** `Predicting: 0/? [00:00<?, ?it/s]` forever. 0% GPU, 0% CPU, process alive, **no error, no timeout**. I lost 25 minutes to this twice.
**Cause:** PyTorch Lightning's default multiprocess dataloader deadlocks on this ARM64 setup.
**Fix:** `--num_workers 0`.
**Why it matters:** this fails *silently and forever*. On stage it looks like your demo froze. Bake `--num_workers 0` into every call path.

### 3.2 `gemmi==0.6.5` won't build
**Symptom:** `Failed building wheel for gemmi` → `Could NOT find Python (missing: Interpreter Development.Module)`.
**Cause:** no aarch64 wheel at that version + no Python headers.
**Fix:** `gemmi==0.7.5` (prebuilt aarch64 wheel) + `boltz --no-deps`. pip prints a version-conflict warning; it is cosmetic, Boltz runs fine.

### 3.3 `ModuleNotFoundError: cuequivariance_torch`
**Cause:** Boltz's `[cuda]` extra pins `cuequivariance_ops_cu12` — CUDA **12** — on a CUDA **13** machine. Installing the extra actively breaks it.
**Fix:** skip the extra, install the `-cu13` packages (step 4). Verified: recognizes GB10 as cc 12.1, 128 SMs.

### 3.4 Triton can't compile: `Python.h: No such file`
**Cause:** Triton builds a small CUDA shim at runtime and needs Python dev headers. `sudo` needs a password here.
**Fix:** step 5 above — `apt-get download` needs no root, `dpkg-deb -x` unpacks into `$HOME`, `CPATH` makes gcc find them. Verified compiling.

### Non-issues (so you don't waste time)
- **sm_121 support:** a non-problem. `sm_120` SASS is valid on cc ≥ 12.0. No custom wheel, no fork needed.
- **Triton ptxas:** triton 3.8.0 ships both a CUDA 12.9 `ptxas` and a 13.3 `ptxas-blackwell`, and picks correctly.
- **`fairscale`/`modelcif`** have no ARM wheels but build from source fine.

---

## 4. Measured results (1 Nano, single-sequence mode)

Four cases, `--recycling_steps 3 --diffusion_samples 1 --sampling_steps 200`:

| Case | Chains | Residues | Wall | Exit |
|---|---|---|---|---|
| `kras_g12d_c0802_gdom` | α1α2 + peptide | 189 | **44 s** | 0 |
| `kras_g12d_c0802` | α1α2α3 + B2M + peptide | 383 | **58 s** | 0 |
| `cmv_a0201_correct` | α1α2α3 + B2M + peptide | 383 | **58 s** | 0 |
| `cmv_a0301_wrong` | α1α2α3 + B2M + peptide | 383 | **58 s** | 0 |

Of the 58 s, **~27 s is GPU inference**; the rest is process start + model load (amortizable across a batch).

**GPU telemetry during inference:** peak **96% utilization**, **38 W**, 46 °C, 2,304 MiB process memory.
Idle baseline ~3.5 W. That power delta is a clean, honest "real work is happening" signal.

**Telemetry gotcha:** `nvidia-smi --query-gpu=memory.total` returns `[N/A]` on GB10 (unified memory, no discrete VRAM). But these **do** work: `utilization.gpu`, `power.draw`, `temperature.gpu`, and `--query-compute-apps=pid,used_memory` for per-process memory. `dmon`/`pmon` report memory as `0` — silently wrong, don't use them.

---

## 5. Demo case: use this one

**KRAS G12D → HLA-C\*08:02**, ground truth **PDB 6ULN**.

- Variant: GRCh38 `chr12:25,245,350 C>T` (minus strand; genomic C>T, not G>A), MANE `NM_004985.5`
- Peptide: **`GADGVGKSA`** (published epitope: Tran *NEJM* 2016; Sim *PNAS* 2020)
- Reference protein: UniProt **P01116 canonical = KRAS4A (189 aa)**, not 4B. The isoforms are identical over residues 1–150, so peptides at codon 12 are unaffected — but the label matters if anyone checks.
- HLA-C\*08:02 ectodomain: IMGT/HLA `HLA:HLA00446`, mature residues 1–275
- B2M: UniProt `P61769` mature 99-mer (use 99, not the 100 in crystals — that Met is an artifact)

All three chains are **byte-identical to the corresponding chains in PDB 6ULN**. That is a strong, true stage claim: *"our pipeline reconstructed a known experimentally-solved complex end-to-end on-device in 58 seconds, and the peptide was derived from a VCF row, not typed in."*

Be honest that this is **retrospective** — 6ULN may be in Boltz-2's training data.

> ⚠️ **Bug I made, don't repeat it:** UniProt **P04439 is HLA-A\*03:01, not A\*02:01** (byte-identical to `HLA:HLA00037`; 19 mismatches vs A\*02:01 across the ectodomain, 14 inside the binding groove). For A\*02:01 use IMGT `HLA:HLA00005`.

---

## 6. ⚠️ The finding that changes the architecture

I ran a deliberate negative control: the CMV epitope `NLVPMVATV` on its **correct** allele (A\*02:01) and on the **wrong** allele (A\*03:01, whose F-pocket chemistry rejects that peptide's anchor).

| Case | ipTM | pLDDT | peptide–HLA ipTM |
|---|---|---|---|
| Correct allele (A\*02:01) | 0.987 | 0.986 | 0.996 |
| **Wrong allele (A\*03:01)** | **0.988** | 0.986 | 0.994 |

**The wrong pairing scored marginally *higher*.** Boltz returns a confident-looking pose for a complex that should not form.

**Consequences, and they are not optional:**
1. **Never rank or filter candidates by Boltz confidence.** It does not discriminate binders from non-binders here.
2. **MHCflurry does the discrimination.** Boltz is the *explanation and visualization* layer.
3. **Say this out loud in the pitch.** It is a credibility asset: it shows you validated your own tool. A sharp judge may probe exactly here, and "we tested that and here are the numbers" is a much better answer than being surprised.

> ⚠️ **Word this carefully.** Say confidence is **"weak and unreliable for this purpose"**, *not* "meaningless". Our negative control is n=1, and the published position (Motmaen et al.) is that confidence gives *some* discrimination. The true, narrow claim is damning enough, and the overclaim is the one thing here a sharp judge could actually break.

Supporting context from the research: the best published pro-structure neoantigen result drops from AUC 0.73 in-sample to **0.60 held-out**; the TESLA consortium found only **37/608 (6%)** predicted neoantigens were immunogenic. Structure is not a validated discriminator, and you should not imply it is.

---

## 6A. Accuracy, measured against a crystal structure

ipTM is a self-reported score, and §6 shows it is untrustworthy here. So I measured real accuracy: superpose the predicted complex onto **PDB 6ULN** on the MHC heavy chain, then ask how close the *peptide* landed. This is the standard pMHC metric. Script: `rmsd.py` on the Nano.

| Configuration | MHC CA RMSD | **Peptide backbone RMSD** | Peptide CA | Wall time |
|---|---|---|---|---|
| Single-sequence (`msa: empty`) | 0.970 Å | **0.560 Å** | 0.464 Å | 58 s |
| **With MSA (cached, offline)** | **0.748 Å** | **0.51 Å** | **0.41 Å** | 58 s* |
| With MSA (fetching from server) | — | — | — | 132 s |

\* once the MSA is cached; the 132 s run includes the one-time online fetch.

### ⚠️ Held-out accuracy: our anchors were optimistic

Both structures we originally validated against — **6ULN (2020)** and **3GSO (2009)** — predate Boltz-2's **2023-06-01 training cutoff**, so they may be memorised. We tested that by predicting pMHC structures deposited *after* the cutoff.

| Set | n | Median peptide backbone RMSD | Range | sub-1 Å |
|---|---|---|---|---|
| Our original anchors (pre-cutoff) | 2 | **0.42 Å** | 0.32–0.51 | 2/2 |
| Other pre-cutoff structures | 3 | 1.01 Å | 0.39–1.08 | 1/3 |
| **Held out (post-cutoff)** | **9** | **1.41 Å** | 0.87–1.87 | 3/9 |

**Held-out accuracy is ~3.3× worse than the anchors we had been quoting.** Not the collapse the literature warns of across this boundary (0.92 Å → 4.59 Å) — **all 9 are under 2 Å** — but our headline was materially optimistic.

**Quote this instead:** *"Median 1.41 Å peptide backbone RMSD across nine pMHC structures deposited after the model's training cutoff, all under 2 Å."* The sub-Ångström figures are training-set results and should be labelled as such.

Two held-out cases are directly on-topic: **8VJZ** is wild-type KRAS `VVVGAGGVGK` (0.88 Å) and **8RNI** is KRAS G12V `VVVGAVGVGK` (0.98 Å) — so the model does well on this protein family even when held out.

**A fifth demonstration that confidence does not track accuracy.** Across the held-out set ipTM spans **0.978–0.988** — a range of 0.011 — while real error spans **0.87–1.87 Å**. Pearson r between them is just **−0.23**. The worst prediction (9XME, 1.87 Å) scores ipTM 0.987, *higher* than the best one (9WK0, 0.87 Å at 0.988 — statistically indistinguishable).

---

**A second, independent validation.** The CMV epitope `NLVPMVATV` on **HLA-A\*02:01** against crystal **3GSO**: MHC CA **0.33 Å**, peptide backbone **0.321 Å**. Different allele, different deposition, same sub-Ångström result — much harder to dismiss as luck than a single case.

| Case | Crystal | Peptide backbone RMSD |
|---|---|---|
| KRAS G12D `GADGVGKSA` / C\*08:02 | 6ULN | **0.509 Å** |
| CMV `NLVPMVATV` / A\*02:01 | 3GSO | **0.321 Å** |

**Sub-Ångström peptide placement.** For scale, that is within the coordinate uncertainty of many crystal structures. Per-residue deviation is **lowest at p2–p3** (0.24 Å, 0.30 Å) and highest at the termini (p1 0.51 Å, p9 0.67 Å). We previously stated this backwards. The pattern is consistent with p2 being a primary anchor buried in the B pocket, while the termini are the most mobile.

**Say this honestly:** 6ULN was published in 2020 and may well be in Boltz-2's training data. This is a **retrospective reconstruction**, not a blind prediction. The claim to make is *"our pipeline reconstructs a known complex end-to-end on-device to 0.51 Å in under a minute"* — which is true, verifiable, and still impressive.

### The MSA insight that makes accuracy free

MSAs cost 74 s extra to fetch — but **only once**. The HLA and B2M chains are *identical for every candidate peptide from the same patient*; only the 9-mer changes, and short peptides use `msa: empty` anyway.

So: **generate the HLA + B2M MSA once while online, cache it, and every subsequent candidate is both offline and MSA-accurate at no extra cost.** Cached MSAs live in `~/neofold/msa_cache/` (`hla_c0802.csv` 3.8 MB, `b2m.csv` 725 KB) and are referenced per-chain:

```yaml
  - protein: { id: A, sequence: <HLA>, msa: ./msa_cache/hla_c0802.csv }
  - protein: { id: B, sequence: <B2M>, msa: ./msa_cache/b2m.csv }
  - protein: { id: C, sequence: GADGVGKSA, msa: empty }
```

**Pre-cache one MSA per HLA allele you intend to demo, before going offline.**

---

## 6B. The screening layer works — and this is the scientific heart of the demo

MHCflurry 2.2.0 (PyTorch backend, installs clean on ARM64), `HLA-C*08:02`, 38 peptide windows spanning KRAS residue 12:

| Peptide | Affinity | Presentation | Note |
|---|---|---|---|
| `GADGVGKSAL` | **38.9 nM** | 0.950 | **rank 1/38** — published epitope (Sim *PNAS* 2020) |
| `GADGVGKSA` | **74.1 nM** | 0.570 | **rank 2/38** — published epitope (Tran *NEJM* 2016) |
| `VGADGVGKSAL` | 230 nM | 0.341 | |
| … | | | |

**Neoantigen specificity — run the wild-type as a control:**

| | Mutant (G12D) | Wild-type | Fold change |
|---|---|---|---|
| `GADGVGKSA` vs `GAGGVGKSA` | 74.1 nM | 3,656 nM | **49.4×** (DAI 23.5 damped) |
| `GADGVGKSAL` vs `GAGGVGKSAL` | 38.9 nM | 877 nM | **22.6×** (DAI 17.9 damped) |

This is the demo's real story: **a single base substitution creates a peptide presented far better than its germline counterpart**, shown with measured numbers on-device against epitopes published in *NEJM* and *PNAS*.

> ⚠️ **Do not say "the normal protein is invisible."** By percentile rank the germline 10-mer `GAGGVGKSAL` is **1.055 %rank — a weak binder** under the NetMHCpan convention, so it is predicted to be presented, just far less well. Only the germline 9-mer (2.254 %rank) falls outside the binder bands. Raw nM ratios overstate the contrast; ranks are the honest unit because affinity distributions differ by allele.

Always show the wild-type control. It is the difference between "the model gave us a number" and "the mutation is why this candidate exists."

---

## 6B-2. ⚠️ Literature audit: what we had wrong

We audited the pipeline against the primary experimental literature. Three things were wrong and are now fixed.

### 0. ⚠️ Biggest correction: DAI is an anchor detector, not a specificity gate

We first used DAI ≥ 2, then corrected it to DAI ≥ 10 (Rech 2018). **Both were wrong, because gating on DAI at all is wrong.**

The differential is largely an **anchor-creation detector**:

| Mutation position | Effect on MHC binding | Effect on the TCR-facing surface | Resulting DAI |
|---|---|---|---|
| **Anchor** (P2, PΩ) | large — sits in the B/F pocket | little | **large** |
| **TCR-facing** (middle) | little | large — this is what the receptor reads | **~1** |

So a DAI gate **promotes anchor mutants and discards TCR-facing ones** — backwards for immunogenicity. Measured on our own demo set, a `DAI ≥ 10` gate discards **35 of 36** TCR-facing binders while passing **3 of 4** anchor mutants. It excluded **EGFR L858R**, whose mutation sits at peptide position 6.

This is not our inference. Duan 2014, Ghorani 2018 and TESLA all report that essentially every extreme-DAI peptide is an anchor mutant, and **pVACtools ships an "Anchor Criteria" filter that penalises exactly what a DAI gate rewards** — the two pull in opposite directions on the same peptides.

**Now:** presentation is the *only* gate. DAI is reported alongside a **mutation-site annotation** (anchor / TCR-facing / P1), because the number is uninterpretable without it. The UI says so on the row.

### 1. The 2× threshold was invented (superseded by §0, kept for the record)

**No published source supports a 2× cutoff.** The field is bimodal — either no threshold at all (Łuksza 2017/2022, MuPeXI, Neopepsee, antigen.garnish all use it as a *continuous* feature), or **~10×**. Rech *et al.* (*Cancer Immunol Res* 2018) derived **DAI > 10** as the first percentile of the empirical distribution, and measured the **median DAI of ordinary neoantigens as 1.183** — so our 2× cut sat near the middle of the null distribution and enriched for almost nothing.

**Fixed:** threshold is now **DAI ≥ 10**, cited to Rech 2018.

### 2. We applied the differential as a standalone gate

TESLA (Wells *et al.*, *Cell* 2020; 608 peptides, 25 pipelines, **37 immunogenic = 6%**) is explicit: *"submissions that explicitly prioritized peptide foreignness, agretopicity, or both, **without accounting for presentation**, either had no difference in performance or performed worse."*

**Fixed:** presentation is now a hard gate applied *first*; the differential only ranks peptides that already clear it.

### 3. The denominator was undamped

The wild-type peptide is by construction usually a weak binder — exactly the regime where predictors are least reliable and a small denominator inflates the ratio arbitrarily. Łuksza *et al.* (*Nature* 2017) damp it with ε = 0.0003 (1/3687 nM, "the outer range of predictability for the assays upon which NetMHC is trained"); antigen.garnish adopts this verbatim.

**Fixed:** `damped_dai()` applies the Łuksza correction. Raw and damped values are both reported.

### A trap we avoided by testing

**TESLA's "agretopicity" is the reciprocal of everyone else's DAI.** `agretopicity < 0.1` and `DAI > 10` are the same filter. Worse, the **pVACtools documentation states the direction backwards** relative to its own source code. A sign error here silently inverts the filter, so `tests/test_dai.py` asserts the convention rather than assuming it.

### One overreach we caught in ourselves

We briefly implemented TESLA's recognition rule as a disjunction — *low agretopicity OR high foreignness* — using our self-similarity search as the foreignness term. **That was wrong.** TESLA's foreignness is similarity to *known pathogen epitopes* (the Łuksza IEDB term); our search measures *distance from the human proteome* (closer to Richman *et al.*, *Cell Syst* 2019 "dissimilarity"). They are different quantities. Substituting one for the other admitted candidates at DAI 0.9 that the differential had correctly rejected. Dissimilarity-to-self is now reported as a **flag** and never qualifies a candidate on its own.

### Resulting funnel

| Stage | Count |
|---|---|
| Variants | 50 |
| Candidate peptides | 1,890 |
| **Self peptides cut** (exact proteome match) | **13** |
| **Presented** (the only gate) | **22** |

Ranked by presentation. `GADGVGKSAL` leads at 0.051 %rank; `ITDFGRAKL` (EGFR L858R) is retained at 0.037 %rank and annotated *TCR-facing, DAI 0.9 — expected*.

**QC invariant, now a test:** all 1,890 wild-type windows are found verbatim in the human proteome. They must be, by construction — so a single miss would indicate a bug in the reference sequence, codon numbering or window arithmetic. It tests variant mapping end-to-end.

### Ranked omissions, with measured effect sizes

A reviewer will ask what we are not modelling. In priority order:

| Omission | Measured effect | Source |
|---|---|---|
| **RNA expression** | **+11 to +13 PPV points**; orthogonal to affinity; in TESLA, 50% of lost immunogenic peptides were lost to low abundance | Abelin *Immunity* 2017; Sarkizova *Nat Biotechnol* 2020 |
| Clonality / VAF | 12/13 vs 2/18 benefit on anti-PD-1; **zero** T-cell responses across >250 subclonal peptides | McGranahan *Science* 2016 |
| pMHC stability | TESLA > 1.4 h; two peptides with *identical* affinity had half-lives of 22.3 h and 1.3 h | Harndahl 2012; Blaha 2019 |
| TAP transport | AUC 0.919 → 0.932; NetCTL weights it 0.05 | Peters *J Immunol* 2003 |
| Proteasomal cleavage | Adds ~1.5–3 PPV points; in Peters 2003 combining it actively *hurt* | Peters 2003; Sarkizova 2020 |

**Expression is the most serious.** A gene that is not transcribed cannot produce a presented peptide at any affinity, so an affinity-only pipeline nominates epitopes that are physically impossible, not merely improbable.

**The honest framing of our hit rate:** affinity-based selection is *necessary but wildly under-specific*. Across 1,948 neopeptide-HLA combinations in the literature, **53 (2.7%)** elicited a T-cell response, and 96% of those shared very strong predicted binding — so binding prediction is informative, just nowhere near sufficient (Bjerregaard *Front Immunol* 2017).

---

## 6B-3. ✅ The screen, validated against measured T-cell responses

Structure accuracy was always measured against crystals. The **screen** — the layer that actually decides what gets shortlisted — had never been validated at all. Now it has.

**Benchmark:** Bjerregaard *et al.*, *Front Immunol* 2017 — **1,947 neopeptide/HLA pairs** from 13 published studies, each with an experimental T-cell assay outcome and its wild-type counterpart. **53 responders, base rate 2.72%.**

### Rules, ranked by enrichment over random

| Rule | Recall | Precision | Enrichment |
|---|---|---|---|
| **affinity ≤ 50 nM** | 62.3% | 6.1% | **2.22×** |
| DAI ≥ 10 alone | 18.9% | 4.9% | 1.80× |
| %rank < 0.5 | 86.8% | 4.7% | 1.73× |
| presentation ≥ 0.50 | 86.8% | 4.3% | 1.59× |
| **ours** (presentation ≥ 0.10 ∧ ≤ 500 nM) | **92.5%** | 3.6% | 1.31× |
| affinity ≤ 500 ∧ DAI ≥ 2 | 24.5% | 2.9% | 1.07× |
| **DAI ≥ 2 alone** (our first shipped rule) | 24.5% | 2.6% | **0.96× — below random** |

**Our original DAI ≥ 2 gate performed worse than chance**, on 1,947 experimentally-tested pairs. That is the empirical confirmation of §0.

### Precision at shortlist size — the number that matters

We do not apply a single cut; we rank and take a top-N for structure prediction. So:

| Ranking strategy | P@10 | P@25 | P@50 | P@100 |
|---|---|---|---|---|
| **presentation score** | 10% | **16%** | **14%** | **14%** |
| %rank | **30%** | 16% | 10% | 7% |
| raw affinity (nM) | 0% | 4% | 4% | 9% |
| DAI | 10% | 8% | 8% | 4% |

**Ranking by presentation score gives ~5× enrichment** over the 2.72% base rate at realistic shortlist sizes. Ranking by raw nM is markedly worse, and DAI decays with depth — consistent with it being an anchor detector.

### Discrimination (AUC), and the anchor hypothesis confirmed by measurement

| Score | Overall AUC | On anchor mutations | On TCR-facing mutations |
|---|---|---|---|
| **presentation score** | **0.777** | 0.719 | **0.801** |
| affinity (nM) | 0.755 | — | — |
| %rank | 0.744 | — | — |
| **DAI** | **0.592** | **0.660** | **0.577** |
| wild-type affinity alone | 0.678 | — | — |

DAI is close to uninformative overall (0.592 against 0.5 for no information), and it performs **better on anchor mutations than on TCR-facing ones**, while presentation shows the **opposite** pattern. That is the anchor-detector claim confirmed by measurement rather than by citation.

Per-allele: HLA-B\*35:01 0.806, A\*02:01 0.773, A\*11:01 0.741, A\*01:01 0.722. Strata with fewer than ~5 responders (B\*15:01, B\*07:02, all 11-mers) are noise and are labelled as such — the 11-mer AUC of 0.233 rests on a single positive.

**What to claim:** *"On 1,947 experimentally-tested neopeptides, ranking by our screen puts a true T-cell responder in the top 25 at 16%, against a 2.7% base rate (AUC 0.777)."* That is a measured, held-out, immunogenicity-grounded claim — considerably stronger than any picture of a structure.

**What not to claim:** this is not a held-out test of a *trained* model — MHCflurry may have seen some of these peptides in training. It measures whether the ranking is useful, not whether it generalises to unseen chemistry.

---

## 6B-4. ✅ Independent validation on TESLA

Bjerregaard was the development benchmark. **TESLA** (Wells *et al.*, *Cell* 2020) is reported as-is, with nothing tuned on it. It is the harder test: its 571 negatives are **same-patient hard negatives** — peptides a real pipeline nominated and a real assay rejected — at a realistic **6.09%** prevalence.

| Score | AUC | n |
|---|---|---|
| **our %rank** | **0.762** | 608 |
| **our presentation score** | **0.759** | 608 |
| our predicted affinity (nM) | 0.755 | 608 |
| TESLA's **experimentally measured** affinity | 0.747 | 503 |
| TESLA's NetMHCpan affinity | 0.747 | 608 |
| binding stability (h) | 0.685 | 608 |
| tumour abundance (TPM) | 0.643 | 404 |
| foreignness | 0.529 | 535 |
| **agretopicity** | **0.412** | 568 |

**Two results worth stating plainly.**

**1. Our predictions match or slightly exceed the laboratory measurement.** Predicted presentation scores 0.759 against 0.747 for TESLA's *measured* binding affinity from a competitive binding assay. The honest reading is not "prediction beats experiment" — it is that **binding affinity, however obtained, is simply not a strong discriminator of immunogenicity**. The ceiling here is the biology, not the predictor.

**2. Agretopicity scores 0.412 — below random — on TESLA's own data, using TESLA's own column.** This is the third independent confirmation, after the Bjerregaard enrichment (0.96×) and the anchor/TCR-facing AUC split, that the mutant-versus-wildtype differential is not a useful standalone discriminator. It is also the clearest possible vindication of removing it as a gate.

**Precision at depth**, ranked by our screen, against a 6.09% base rate:

| Depth | Hits | Precision | Enrichment |
|---|---|---|---|
| P@25 | 8/25 | **32.0%** | **5.26×** |
| P@50 | 13/50 | 26.0% | 4.27× |
| P@100 | 18/100 | 18.0% | 2.96× |

**The claim this supports:** *"On two independent benchmarks totalling 2,555 experimentally-tested peptides, our screen reaches AUC 0.76–0.78 and places a true T-cell responder in the top 25 at 16% and 32% respectively — 5× the base rate in both."*

**Caveat to state:** MHCflurry may have trained on some of these peptides. But TESLA's *measured* affinity achieves a comparable AUC, which indicates the ranking signal is real rather than an artefact of memorised labels.

---

## 6C. The proposed additions, assessed

Three additions were proposed on top of the working pipeline. Two are worth building, one is not.

### ❌ Multi-seed Boltz ensembles — TESTED AND REJECTED

**We ran the experiment rather than arguing from architecture.** A 2×2 allele swap: two well-characterised CMV epitopes, each folded on its correct restricting allele and on the wrong one, 5 diffusion samples each (20 structures, 334 s batched).

| Complex | Pairing | Ensemble spread | ipTM |
|---|---|---|---|
| `NLVPMVATV` on A\*03:01 | **swapped** | **0.118 Å** | 0.9876 |
| `NLVPMVATV` on A\*02:01 | cognate | 0.207 Å | 0.9880 |
| `KLGGALQAK` on A\*02:01 | **swapped** | 0.656 Å | 0.9816 |
| `KLGGALQAK` on A\*03:01 | cognate | **0.930 Å** | 0.9882 |

**Ranked by self-consistency, the wrong pairing comes first and a correct pairing comes last.** Spread here is not merely uninformative — it is actively misleading. Cognate spread spans 0.207–0.930 Å and swapped spans 0.118–0.656 Å; the ranges overlap almost completely.

All four complexes scored ipTM > 0.98 regardless of whether the pairing was biologically possible, which reproduces the earlier wrong-allele control a third time.

**This is a good slide, not a gap.** "We proposed ensemble consistency, predicted from the architecture that it could not work, tested it with a pre-registered 2×2 design, and confirmed it does not" is a stronger story than a chart that means nothing. Four tests pin the result so the feature cannot be quietly revived.

#### Why it cannot work (the architectural reason, now confirmed)

The idea was to run Boltz several times per candidate and use the spread between predictions as an uncertainty signal. **Reading the Boltz source kills it:**

- In `boltz2.py` the **trunk runs once**; `s_trunk`/`s_inputs` are `repeat_interleave`d across diffusion samples. The only difference between samples is `torch.randn` noise in `diffusionv2.py`.
- `inferencev2.py` **hard-codes `seed = 42`** for the featurizer RNG, so `--seed` never reaches MSA subsampling — it only touches the torch RNG.
- Therefore **`--seed S` and `--diffusion_samples N` vary the identical quantity**, and multi-seed is strictly dominated at N× the cost.

The AF2 multi-seed folklore does not transfer: AF2 pairs seeds with MSA subsampling and inference dropout, and Boltz-2 does neither.

Critically, **ensemble spread would almost certainly NOT have caught our wrong-allele error** — that failure lives in the trunk, and the samples do not sample the trunk. Spread measures *where atoms land given the model already decided the peptide is in the groove*. Presenting it as uncertainty about *whether the peptide binds* would be the single biggest honesty trap in this project.

**Ship it as a pre-registered negative result instead.** "We tested whether ensemble spread adds information, read the architecture, and concluded it cannot — here's why" is a better slide than a chart that means nothing. If you want the empirical version, a 2×2 allele swap (`NLVPMVATV` and `KLGGALQAK`, each on A\*02:01 and A\*03:01) settles it in ~25 minutes.

### ✅ Tumour vs normal side-by-side — build it, but let chemistry carry it

The naive version is false: Boltz will produce a confident, plausible pose for the wild-type peptide too, so "mutant looks good / wild-type looks bad" would not survive scrutiny.

**This case has a real discriminator, and I verified it.** HLA-C\*08:02 prefers **Asp at peptide position 3** (Rasmussen, *J Immunol* 2014). G12D is precisely what puts Asp at p3 in `GADGVGKSA`, and crystal structure 6ULN shows that p3 Asp making charge contacts to **Arg156** (2.73 Å) and also **Arg97** (3.71 Å). Measured with `neofold/contacts.py`:

| Structure | p3 residue | Distance to Arg156 | Salt bridge |
|---|---|---|---|
| Crystal 6ULN | ASP3 | **2.73 Å** | yes |
| Boltz prediction | ASP3 | **2.52 Å** | yes |
| Wild-type (`GAGGVGKSA`) | **Gly** | — | **impossible** |

Two things make this honest rather than fishing: the contact was **specified in advance from an experimental structure**, and the wild-type failure is **chemical, not predictive** — glycine has no side chain, so the interaction cannot exist at any confidence level.

This is not our inference. Sim *et al.* (*PNAS* 2020) report that "only mutant G12D but not the wild-type peptides stabilized HLA-C\*08:02", with the most peptide side-chain contacts at p3 where the Asp salt-bridges Arg156; Mariuzza *et al.* (*Front Immunol* 2023) state plainly that "this salt bridge cannot form with P3 Gly, which probably explains the instability of wild-type KRAS–HLA-C complexes."

**Caption to use:** *"The G12D substitution places an aspartate at peptide position 3, where HLA-C\*08:02 has a charged pocket. In the crystal structure that aspartate forms a 2.7 Å salt bridge to Arg156; our local prediction reproduces it at 2.5 Å. The normal protein has glycine here — no side chain, no contact possible."*

> ⚠️ **The structure adds geometry, not the verdict.** Whether this contact *can* form is a deterministic
> function of the peptide sequence — position 3 is aspartate or it is not — so the structure prediction
> contributes **no information** on that point. What it contributes is the *geometry*: 2.58 Å against the
> crystal's 2.73 Å. Present it as "our local model reproduces the known contact geometry", never as
> "our model discovered why this peptide binds."
>
> ⚠️ **Molecular dynamics cannot corroborate this contact.** Generalised-Born implicit solvent
> over-stabilises salt bridges by 3–4 kcal/mol, with the error concentrated on hydrogens bonded to
> charged nitrogens — precisely Arg156's guanidinium — and OpenMM's GB defaults to zero ionic strength.
> The crystal and the prediction already make the case; adding MD to it would be circular.
>
> ⚠️ **The caveat that must accompany the panel.** Do not let anyone read binding strength off the picture. For a published wild-type/mutant pair on HLA-A\*03:01 (PDB **7L1B** / **7L1C**, Chandran *et al.*, *Nat Med* 2022), a **70× difference in complex half-life** (0.078 h vs 5.497 h) corresponds to just **0.73 Å** of peptide backbone RMSD. Almost none of the binding signal is visible as geometry. Say so — it is why the panel measures one named contact and takes its ranking from the sequence-based screen.
>
> Two further honest limits: modelling protocols such as PANDORA and APE-Gen place anchors in pockets **by construction**, so burial depth in a model is an artifact, not evidence. And non-binders do not crystallise, so the PDB contains **no control group** for any "non-binder geometry" claim.

### ✅ OpenMM stability test — BUILT AND MEASURED

**OpenMM 8.6.1 runs on the GB10.** `python -m openmm.testInstallation` reports *"3 CUDA — Successfully computed forces"*, all platforms within tolerance. First-party PyPI aarch64 wheels, no conda, no sudo. sm_121 is fine because OpenMM compiles kernels at runtime via NVRTC.

**Measured throughput: ~1,000 ns/day** (6,088 atoms, amber14 + OBC2 implicit solvent, 4 fs with HMR, 1.8 nm cutoff) — far above the 150 ns/day kill threshold. ~1 ns per 90 s run.

**Result, n=3 per condition, KRAS G12D mutant vs wild-type:**

| Metric | Tumour | Wild-type | Separates? |
|---|---|---|---|
| **Contact persistence** | 0.765 [0.760–0.769] | 0.670 [0.601–0.711] | **Yes — ranges disjoint** |
| Final peptide RMSD (Å) | 1.58 [1.19–2.13] | 2.48 [1.99–3.38] | No — ranges overlap |
| Runs flagged unstable | 0 / 3 | 1 / 3 | directional only |

**Neither peptide was rejected.** MD filtered nothing here, which is the honest outcome. Contact persistence did separate the pair with non-overlapping ranges, but that is **n=3 on one peptide pair over ~1 ns** — suggestive, not a validated discriminator. The largest published study moved AUC only 0.80 → 0.81 using 200 ns runs.

> **One bug worth recording.** Peptide RMSD must be computed **after superposing on the MHC**. Without it, rigid-body tumbling of the whole complex inflates RMSD to ~7 Å even for a crystallographically-validated pose, and the crystal-matched mutant gets falsely "REJECTED". A test now guards against that regression.

**Defensible:** "physics immediately rejects this pose." **Not defensible:** anything about stability, affinity or immunogenicity.

---

### Original assessment (kept for the reasoning)

Verdict: **GO**, with a downgraded timescale.

- OpenMM now publishes **first-party PyPI aarch64 wheels** (`openmm-8.6.1-cp312-...-aarch64`, plus `openmm_cuda_13`). No conda, no sudo, no compiling — this inverts the usual "OpenMM is conda-only" assumption.
- **sm_121 should work** for a structural reason: OpenMM generates kernels at runtime via NVRTC rather than shipping pre-compiled fatbins, which is the root cause of every other sm_121 failure.
- **Install into a separate venv** — `openmm[cuda13]` drags in its own `nvidia-*` stack that would fight the Boltz environment's.
- **Pin `nvidia-cuda-nvrtc==13.0.88`.** CUDA minor-version compatibility explicitly excludes PTX JIT, and the default pull (13.4.x) can emit PTX a 13.0 driver rejects.
- **Budget ~0.5 ns, not 1–3 ns**, plus 20–65 s fixed NVRTC compilation overhead — so batch all candidates in one process.

**The honesty limit is severe and must be stated.** The largest relevant study (2,883 HLA-A2 peptides, 200 ns each) got AUC 0.81 from MD features versus 0.80 from sequence alone — and discarded its first 30 ns as equilibration, roughly 60× your entire production run. Measured pMHC half-lives are in *hours*; you would sample ~10⁻¹³ of that.

**Defensible:** "physics immediately rejects this pose." **Not defensible:** any claim about stability, affinity or immunogenicity.

**Kill criterion:** if a calibration run reports under 150 ns/day, cut MD and spend the time on the demo.

---

## 6D. ⚠️ The hardware fault, and the fix

The Nano powered itself off ~11 times during development. Diagnosis, because it cost hours:

**It is a GPU boost-clock fault.** Capping the maximum SM clock at **2,500 MHz** stops it.

```bash
sudo nvidia-smi -lgc 300,2500      # does NOT survive a reboot -- re-apply after every boot
sudo nvidia-smi -rgc               # reset
```

**Evidence trail**, in case it recurs:

| Test | Result |
|---|---|
| 20-core CPU stress, 60 s | ✅ survived, 50–53 °C |
| `nvidia-smi` polling | ✅ survived |
| Sustained bf16 matmul, **53.4 TFLOPS** | ✅ survived, 42 W |
| 16 GB unified allocation | ✅ survived |
| Boltz-2 real workload | ❌ powered off |
| Boltz with `--no_kernels` | ❌ powered off (so **not** cuEquivariance) |

Never an Xid, thermal event, OOM or kernel panic — journald is persistent, so a panic would have been captured. Temps stayed 34–46 °C. The tell was in the telemetry: the GPU **auto-boosts to 2,522 MHz** at stock settings, just above 2,500. Note also that **GB10 exposes no software power cap** (`Power Limit: N/A`), so clock capping is the only software lever.

Two false leads worth recording so nobody re-runs them: it is *not* cuEquivariance (`--no_kernels` still died), and it is *not* concurrent load from another user (that only happened once, late).

**Also**: a reboot leaves **zero-byte JSON** in Boltz's `records/` cache, and every later run then dies in `Record.load` with a bare `JSONDecodeError`. Always run this before resuming:

```bash
find ~/neofold -name "*.json" -size 0 -delete
```

---

## 6E. Next process: the recognition step (pMHC:TCR)

The pipeline so far answers *"can this peptide be presented?"* It does not answer *"can a T-cell see it?"* Those differ, and the gap is where real pipelines lose nearly everything — TESLA found **37 of 608** predicted neoantigens immunogenic.

**Measured on the Nano.** Full 5-chain, **812-residue** complex: HLA-C\*08:02 + β2m + KRAS G12D peptide + TCR9d from patient 3995 (Sim *et al.*, *PNAS* 2020 — **not** Tran *NEJM* 2016, which reported the TIL therapy but not this receptor).

| | Result |
|---|---|
| Wall time | **133 s** (against 64 s for 383 residues — 2.1× residues, 2.1× time) |
| GPU | 95% peak, **42.2 W** |
| ipTM / pLDDT | 0.9468 / 0.9687 |

**Accuracy vs crystal 6ULN, superposed on the MHC:**

| Chain | CA RMSD |
|---|---|
| KRAS peptide | **0.32 Å** |
| β2-microglobulin | 0.46 Å |
| **TCR alpha** | **1.42 Å** |
| **TCR beta** | **1.50 Å** |

Adding 429 residues of TCR did not degrade the pMHC core — the peptide is *more* accurate here than in the pMHC-only run. The model also correctly reports lower confidence at the TCR interfaces (0.88) than the pMHC core (0.99): it knows which part is harder.

> ⚠️ **A trap that nearly produced a false headline.** PDB 6ULN applies **different symmetry operators** to the pMHC chains (A,B,C) and the TCR chains (D,E). Compared against the raw asymmetric-unit coordinates the TCR looks **72 Å misplaced** — a catastrophic-looking failure that is purely an artifact of not building the biological assembly. Always `gemmi.make_assembly` before scoring. A regression test asserts both numbers so the mistake cannot recur silently.

**What this does and does not license.** It shows the Nano can run the recognition-step complex locally at crystal-comparable accuracy. It says **nothing** about immunogenicity: predicting where a *known* TCR docks is not the same as knowing whether a patient's repertoire contains one. And 6ULN is retrospective.

---

## 6E-2. The local LLM summary — and why it needs two guardrails

A language model is used for exactly one thing: turning a row of numbers into a paragraph. It computes nothing and decides nothing. It runs on the Nano via Ollama (qwen3:8b, 100% GPU), in about **5–8 seconds** per candidate.

**Guardrail 1 — numeric verification.** Every numeric token in the output is checked against the facts that went in. A model that invents an affinity fails and the summary is rejected.

**Guardrail 2 — claim verification, which we added only after the first run failed.** The first summary passed numeric verification and still asserted three things the evidence does not license:

| What it wrote | Why it is wrong |
|---|---|
| "a differential index of 23.5, **enhancing its immunogenic potential**" | DAI does not do that — we measured AUC 0.592 and 0.412 |
| "the percentile rank highlights its **rarity within the human proteome**" | percentile rank has nothing to do with proteome rarity; it conflated two facts |
| "ipTM of 0.991 **supports the reliability** of the interaction" | contradicted by our own five demonstrations |

Every number was correct. Every interpretation was wrong. So there is now a banned-claims check, and the three phrases above are regression tests quoted verbatim.

**The disclaimer is concatenated by code, never generated**, so it cannot drift or be paraphrased away — and a deterministic template fallback means the demo does not depend on the model being up.

This is worth showing rather than hiding: *"we don't trust the language model either, and here is the check that caught it."*

---

## 6F. The next step: polyepitope construct assembly

Selecting epitopes is not the end of the workflow. The next step in the real clinical pipeline is assembling them into a construct — what BioNTech's BNT122 and Moderna's mRNA-4157 actually do.

**Architecture (BioNTech "pentatope", published in the BNT122 phase 1 Methods, *Nat Med* 2025):**

```
sec signal (26 aa)  →  N × 27-aa epitope stretches  →  MITD anchor (55 aa)
```

The sec and MITD sequences are published verbatim and cross-check exactly against independent patent base counts. Epitopes are **27-residue stretches with the mutation at position 14**, not minimal 9-mers — this lets the proteasome choose the register rather than committing to a predicted one.

### The real engineering problem: junctional epitopes

Joining two epitopes creates a new sequence across the seam, and that seam can encode an epitope nobody intended. This is demonstrated, not hypothetical:

- **Livingston *et al.*, *J Immunol* 2002** — a complete causal loop. The arrangement created a high-affinity class II junction epitope; that epitope raised its own response; **all four intended responses were lost**; adding a spacer restored them.
- **Cornet *et al.*, *Vaccine* 2006** — across **all six** orderings of three epitopes, **only one** produced the intended responses.

**Measured on our own shortlist** (7 distinct stretches, HLA-C\*08:02):

| Ordering | Junctional binders created |
|---|---|
| Naive — shortlist order | **6** |
| Worst possible | 16 |
| **Ours — exhaustive search** | **1** |

**5,040 orderings evaluated in 3.2 s.** At this size the search is *exhaustive*, so the result is provably optimal; pvacvector must use simulated annealing because it targets larger sets. This is a genuine use of local compute with a checkable answer.

### Linkers are not free, and are not our default

**Do not reach for AAY.** No primary study establishes it — its citation chain runs through a review containing no AAY data, and Schubert & Kohlbacher (2016) scored it **below using no spacer at all**. Gurung *et al.* (2024) compared linker against no-linker with mass-spec readout across 47 antigens: **no-linker recovered more epitopes**, and glycine/serine linkers caused translation to collapse past roughly twenty antigens.

So we join directly by default and insert a spacer only at a junction that no reordering can clean. On our shortlist, that was **zero junctions**.

### ⚠️ What this must not claim

**We emit amino acids only, never nucleotides** — a nucleotide sequence implies a manufacturing artefact and this is not one. A test asserts it.

**The modality is not established, and the recent evidence has worsened:**

- **August 2026: BioNTech terminated** the randomised Phase 2 of autogene cevumeran in resected ctDNA+ colorectal cancer. The futility boundary was crossed in October 2025, with a **numerical overall-survival imbalance between arms**.
- **KEYNOTE-942** (mRNA-4157 + pembrolizumab) reported two-sided **p = 0.053**, CI 0.309–1.017 — **crossing 1.0**. It met only the trial's own one-sided α = 0.10.
- **Rojas 2023** (pancreatic) is an **8-vs-8 responder split inside a single arm**.

**And assembly cannot improve a shortlist — only avoid damaging it.** Per our own benchmarks, a 20-epitope construct should be expected to yield roughly **2–3 responding epitopes**. The value of this step is entirely in *not* creating junction artefacts.

Between this output and a medicine sit GMP manufacture, release testing, toxicology, an IND and dose-finding.

---

## 7. Recommended stack for the remaining build

| Layer | Choice | Note |
|---|---|---|
| Fast screen | **MHCflurry 2.2.0** ✅ **installed & validated** | PyTorch backend, no TensorFlow. In `~/neofold/.venv-mhc` on **CPU-only torch** — deliberately, so the GPU stays free for Boltz. Models fetched: 198 MB in `~/.local/share/mhcflurry`. 14,884 alleles. |
| Structure | **Boltz-2** | Installed and verified. MIT licensed — a real advantage over AlphaFold 3, whose weights are non-commercial. |
| 3D viewer | **Mol\* 5.11.0** vendored from npm | Zero external URLs in the CSS; verified offline-safe. Has a `plddt-confidence` theme that reads the B-factor column. |
| Local LLM | **Ollama** (arm64 build), `qwen3:8b` | Unload with `keep_alive: 0` before folding so it doesn't hold memory. **Verify `ollama ps` says `100% GPU`** — it can silently fall back to CPU on sm_121. |
| API | **FastAPI + single asyncio worker** | One worker serializes GPU access for free. Set `docs_url=None` — `/docs` pulls Swagger from jsDelivr at runtime. |

**Offline traps to disable:** Streamlit phones `api.segment.io` even with `gatherUsageStats=false`; Gradio *hangs* on blocked `fonts.googleapis.com`. Prefer plain HTML/JS.

**pLDDT scale trap:** the confidence JSON reports pLDDT on **0–1**, but the CIF B-factor column is **0–100**. Mol\*'s AlphaFold color bands expect 0–100. Use the B-factor column and your colors are correct for free.

---

## 8. Scaling story — what's true

- HP's datasheet says **1,000 TOPS FP4**, not "1 PFLOP". NVIDIA's petaFLOP figure carries a hidden *"with sparsity"* qualifier. Don't quote the PFLOP number unqualified.
- **NVIDIA's DGX Spark clustering exists to run models too big for one device — capacity, not throughput.** Your workload is independent jobs, so it needs none of that: a work queue and an SSH key. Say this crisply; it is a likely judge question.
- **The cloud-egress cost argument does not survive scrutiny** — a WES pair costs ~$5.40 to move. Lead with *governance* instead: local compute removes a data-use-agreement / institutional-certification step rather than merely satisfying one.
- **⛔ DNA is NOT one of HIPAA's 18 Safe Harbor identifiers.** Do not claim it is; it's checkable in the CFR and would damage credibility.
- Label every multi-node number **"projected from measured single-node throughput"**. You have one Nano.

---

## 9. What's left

**Done:**
- Phase 0 gate — Boltz-2 installed, offline prediction verified, 4-case benchmark, GPU telemetry
- Demo case chosen and validated to **0.51 Å** against crystal structure 6ULN
- MSAs generated, cached, and shown to improve accuracy at zero marginal cost
- MHCflurry installed, models fetched, and **validated against two published epitopes with a wild-type control**

**Next, in order:**
1. ~~MHCflurry~~ ✅ done
2. VCF → peptide windows (`research/neopep.py` is a starting point; the window logic in `screen_test.py` on the Nano already works)
3. FastAPI + job queue wrapping the verified Boltz call
4. Vendor Mol\*, render `cached_out/.../*.cif`
5. Ollama + local summary, with the `ollama ps` → `100% GPU` check
6. **Full offline rehearsal with the cable physically out**
7. Benchmark at 5 / 20 / 50 candidates for the scaling chart

**Unfinished:** the offline-with-dead-proxy verification run was interrupted when the Nano dropped off the network. Re-run `~/neofold/run_cached.sh` — it is written and ready.

**Pre-offline download checklist:** Boltz weights (~6.2 GB, cached in `~/.boltz`) ✅, MHCflurry models (198 MB) ✅, **MSA cache per HLA allele** ✅ for C\*08:02 — add any other allele you plan to demo, Ollama model ⬜, Mol\* bundle ⬜.

**Venue network warning:** the Nano dropped off Tailscale mid-session, along with several other machines on that tailnet simultaneously. Assume the venue network is unreliable — which is an argument *for* the project's premise, and a reason to have everything cached locally well before Saturday.

---

## 10. Research appendix

Four deep-dive documents in `research/`, ~4,200 lines, sourced:

| File | Contents |
|---|---|
| `research-boltz-gb10.md` | Boltz/GB10 install paths, MSA strategy, fallback models |
| `research-screen-and-data.md` | MHCflurry, 13 verified hotspot variants w/ GRCh38 coords, IMGT sequences, licensing, metric glosses |
| `research-app-stack.md` | Mol\* offline, Ollama on GB10, NVML telemetry code, offline traps |
| `research-scaling-and-pitch.md` | HP/NVIDIA spec verification, scaling math, 28-question judge Q&A bank |

Artifacts on the Nano: `~/neofold/` — `cases/*.yaml`, `bench/timings.csv`, `bench/gpu_trace.csv`, `bench/*/…/*.cif`.
