# Benchmarks

*Every measurement, with methodology and caveats. Raw JSON in [`benchmarks/`](../benchmarks/).*

Two rules govern this document:

1. **Measured and projected are never mixed.** Anything not measured is labelled.
2. **Failures are reported alongside successes.** Three metrics below perform at or below chance. They are in the tables.

---

## 1. Does the screen actually rank usefully?

Two independent benchmarks, 2,555 peptides, every one with a real experimental T-cell assay outcome.

### 1.1 Bjerregaard 2017

**What it is.** A meta-analysis pooling 13 published neoantigen studies: 1,947 neopeptide–HLA pairs with T-cell response data. **53 responders — a 2.72% base rate.**

**Method.** Score every pair with our screen, without tuning anything. Compute AUC against the assay outcome. Source: `scripts/validate_screen.py`.

#### AUC by metric

| Metric | AUC | Reading |
|---|---:|---|
| **Presentation score** | **0.777** | our primary ranker |
| Predicted affinity (nM) | 0.755 | |
| Predicted %rank | 0.744 | |
| Wild-type affinity (nM) | 0.678 | interesting — the *germline* peptide alone carries signal |
| **DAI (differential)** | **0.592** | **near chance** |

#### The stratification that killed DAI

| Mutation position | n | Responders | Presentation AUC | DAI AUC |
|---|---:|---:|---:|---:|
| **Anchor** (P2 / PΩ) | 481 | 15 | 0.719 | **0.660** |
| **TCR-facing** (middle) | 1,466 | 38 | **0.801** | 0.577 |

The two metrics have **opposite** stratification. DAI does better where the T-cell cannot see the mutated residue and worse where it can. That is the signature of an anchor detector, established by measurement rather than argument. Full reasoning in [PROBLEM.md](PROBLEM.md) §3.1.

#### By peptide length

| Length | n | Responders | Presentation AUC |
|---|---:|---:|---:|
| 9 | 775 | 33 | 0.710 |
| 10 | 738 | 18 | 0.752 |
| 11 | 409 | **1** | 0.233 ⚠️ |

⚠️ **The 11-mer number rests on a single positive and is not interpretable.** Printing it anyway is the point: a stratum with one responder produces a number that looks like a finding and is noise.

#### By allele

| Allele | n | Responders | Presentation AUC |
|---|---:|---:|---:|
| HLA-B\*35:01 | 134 | 4 | 0.806 |
| **HLA-A\*02:01** | **640** | **25** | **0.773** |
| HLA-A\*11:01 | 410 | 9 | 0.741 |
| HLA-A\*01:01 | 146 | 4 | 0.722 |
| HLA-B\*07:02 | 125 | 1 | 0.581 ⚠️ |
| HLA-B\*15:01 | 133 | 1 | 0.356 ⚠️ |

**Performance is allele-dependent**, and best on HLA-A\*02:01 — which is also the best-represented allele in the training data of every class I predictor ever published. That is a real limitation of the whole field, not a quirk of ours. Strata with fewer than ~5 responders are noise.

#### Filter rules, as enrichment over the 2.72% base rate

| Rule | Kept | Found | Recall | Precision | **Enrichment** |
|---|---:|---:|---:|---:|---:|
| random (base rate) | 1,947 | 53 | 1.000 | 2.72% | 1.000× |
| **affinity ≤ 50 nM** | 545 | 33 | 0.623 | 6.06% | **2.224×** |
| DAI ≥ 10 alone | 204 | 10 | 0.189 | 4.90% | 1.801× |
| affinity ≤ 500 **and** DAI ≥ 10 | 204 | 10 | 0.189 | 4.90% | 1.801× |
| %rank < 0.5 | 978 | 46 | 0.868 | 4.70% | 1.728× |
| presentation ≥ 0.50 | 1,061 | 46 | 0.868 | 4.34% | 1.593× |
| **OURS: presentation ≥ 0.10 and ≤ 500 nM** | 1,370 | 49 | **0.925** | 3.58% | 1.314× |
| presentation ≥ 0.10 | 1,560 | 50 | 0.943 | 3.21% | 1.177× |
| %rank < 2.0 | 1,598 | 51 | 0.962 | 3.19% | 1.172× |
| affinity ≤ 500 **and** DAI ≥ 2 | 446 | 13 | 0.245 | 2.91% | 1.071× |
| **DAI ≥ 2 alone** | 495 | 13 | 0.245 | 2.63% | **0.965×** ❌ |

Three things to read here, including one against ourselves:

**❌ DAI ≥ 2 is worse than random.** 0.965×. We shipped it. The data says it was a coin flip with extra steps.

**Our rule is deliberately loose.** 1.314× enrichment is *lower* than a 50 nM cut — but it retains **92.5% of responders** against 62.3%. This is a recall-first choice, and correct for the job: the funnel is a triage stage, and a candidate discarded here can never be recovered by any downstream evidence. Precision comes from ranking, which is what §1.3 measures.

**The germline peptide's own affinity scores 0.678.** Not nothing. Probably an artefact of how neoepitope candidates get nominated in the first place — worth flagging as a confound in any benchmark built this way.

### 1.2 TESLA 2020 — the harder test

**What it is.** The TESLA consortium (Wells *et al.*, *Cell* 2020): 25 independent pipelines nominated candidates, 608 were tested in the laboratory, **37 were immunogenic — a 6.09% base rate.**

**Why it is harder than Bjerregaard.** The negatives are **same-patient hard negatives** — peptides from the same tumours, nominated by expert pipelines, that failed. Bjerregaard's negatives are pooled across 13 studies. Discriminating within one patient's candidate set is the task a real pipeline actually faces.

**Why it is the most valuable dataset available.** TESLA also published **experimentally measured** binding affinity, stability and abundance for the same peptides. So our predictions can be compared against measurements of the same quantity, on the same peptides, against the same outcome.

| Metric | AUC | n | Positives |
|---|---:|---:|---:|
| **OUR %rank** | **0.7624** | 608 | 37 |
| **OUR presentation score** | **0.7592** | 608 | 37 |
| **OUR predicted affinity** | **0.7547** | 608 | 37 |
| TESLA: **measured** affinity (nM) | 0.7473 | 503 | 30 |
| TESLA: NetMHCpan affinity | 0.7473 | 608 | 37 |
| TESLA: measured binding stability (h) | 0.6855 | 608 | 37 |
| TESLA: measured tumour abundance (TPM) | 0.6428 | 404 | 29 |
| TESLA: foreignness | 0.5293 | 535 | 36 | 
| **TESLA: agretopicity** | **0.4117** ❌ | 568 | 37 |

#### Read this table carefully, because the obvious reading is wrong

**Our predicted score (0.759) matches TESLA's experimentally measured affinity (0.747).**

The tempting conclusion — *prediction beats experiment* — is not what this says. The correct reading:

> **Binding affinity, however you obtain it, is not a strong discriminator of immunogenicity. The ceiling is the biology, not the predictor.**

A wet-lab measurement of the right quantity gets ~0.75. A neural network estimate of the same quantity gets ~0.76. Both are near the ceiling of what that quantity can tell you. Improving affinity prediction further buys almost nothing; the missing information is in the T-cell repertoire, which nobody measures at scale.

**❌ Agretopicity scores 0.4117 — below random.** TESLA's agretopicity is mutant/wild-type, the reciprocal of DAI. Two independent datasets, two different parameterisations, same verdict. Our DAI ≥ 2 filter was not unlucky; it was wrong.

**Foreignness at 0.5293 is essentially chance** on this dataset. Note that TESLA foreignness (similarity to a pathogen epitope database) is **not** the same quantity as our self-similarity filter (identity to the human proteome). We briefly conflated the two during development, which let DAI-0.9 candidates through; it was reverted. They answer different questions and 0.5293 is not evidence against ours.

### 1.3 Precision at k — the number that matters for a shortlist

AUC measures ranking across a whole dataset. A researcher does not test a whole dataset; they test the top 25. So this is the operationally meaningful metric.

#### TESLA (base rate 6.09%)

| k | Hits | Precision | Enrichment |
|---:|---:|---:|---:|
| 10 | 1 | 10% | 1.64× |
| **25** | **8** | **32%** | **5.26×** |
| 50 | 13 | 26% | 4.27× |
| 100 | 18 | 18% | 2.96× |

#### Bjerregaard (base rate 2.72%), by ranker

| k | Presentation | %rank | Affinity | DAI |
|---:|---:|---:|---:|---:|
| 10 | 10% (3.7×) | 30% (11×) ⚠️ | 0% | 10% |
| **25** | **16% (5.9×)** | 16% (5.9×) | 4% | 8% |
| 50 | 14% (5.2×) | 10% | 4% | 8% |
| 100 | 14% (5.2×) | 7% | 9% | 8% |
| 200 | 10.5% (3.9×) | 8.5% | 8% | 4.5% |

⚠️ The 30% at k=10 for %rank is 3 hits out of 53 responders. Do not build a claim on it — presentation is the more stable ranker across every other k, which is why it is the default.

**The honest summary of both tables:**

> At k=25 we are right **16–32%** of the time against a base rate of **2.7–6.1%**. That is **5–6× better than chance.** It also means **68–84% of our top candidates are still wrong.**

Both halves of that sentence are in the UI.

---

## 2. Is the structure prediction accurate?

### 2.1 The memorisation problem, and how we got caught by it

Our first two validations looked superb:

| Case | Crystal | Peptide backbone RMSD |
|---|---|---:|
| KRAS G12D `GADGVGKSA` on HLA-C\*08:02 | 6ULN (2020) | **0.509 Å** |
| CMV pp65 `NLVPMVATV` on HLA-A\*02:01 | 3GSO (2009) | **0.321 Å** |

Sub-Ångström. We had "0.42 Å median" on a slide.

**Boltz-2's training cutoff is 2023-06-01.** Both structures predate it by years. They may be in the training set. That is not a blind prediction — it is reconstruction of something the model has likely seen, and the number it produces is a training-set number.

### 2.2 The held-out set

So we assembled 12 peptide–HLA class I crystal structures and split them on the cutoff.

| PDB | Deposited | Resolution | Peptide | **Backbone RMSD** | Cα RMSD | ipTM |
|---|---|---:|---|---:|---:|---:|
| 8SBK | 2023-04-03 | 1.80 Å | LYLPVRVLI | 0.395 | 0.371 | 0.978 |
| 8FU4 | 2023-01-16 | 1.60 Å | TLFDEPPPL | 1.008 | 0.988 | 0.988 |
| 8I5E | 2023-01-25 | 2.20 Å | VVGAGGVGK | 1.079 | 0.844 | 0.983 |
| | | | | | | |
| 9WK0 | 2025-08-31 | 1.80 Å | FSGEYIPTV | **0.875** | 0.877 | 0.988 |
| 8VJZ | 2024-01-08 | 1.90 Å | VVVGAGGVGK | **0.882** | 0.682 | 0.985 |
| 8RNI | 2024-01-10 | 2.49 Å | VVVGAVGVGK | **0.980** | 1.171 | 0.986 |
| 9EK4 | 2024-11-30 | 2.05 Å | MPILTIITL | **1.231** | 1.147 | 0.978 |
| **8TBW** | **2023-06-29** | 2.08 Å | KLSHQPVLL | **1.406** ← median | 1.569 | 0.981 |
| 8YZR | 2024-04-08 | 1.80 Å | NYNYLYRLL | **1.479** | 1.463 | 0.982 |
| 9SKO | 2025-09-02 | 1.49 Å | LLWNGPMAVS | **1.522** | 1.605 | 0.985 |
| 9X7U | 2025-10-17 | 1.59 Å | AMDLGIHKV | **1.720** | 1.813 | 0.980 |
| 9XME | 2025-11-10 | 2.04 Å | AMDLGIDKV | **1.869** | 1.882 | 0.987 |

| Set | n | Median backbone RMSD |
|---|---:|---:|
| Pre-cutoff, possibly memorised | 3 | **1.01 Å** |
| **Post-cutoff, held out** | **9** | **1.41 Å** |

**Every held-out structure is under 2 Å.** For reference, several of these crystals were solved at 1.8–2.5 Å resolution, so the prediction error is comparable to the experimental uncertainty of the reference.

**We quote 1.41 Å.** Our best number is 0.42 Å and we do not use it.

### 2.3 The ipTM column is the real finding

Look down it. Held-out ipTM spans **0.9776 to 0.9880 — a range of 0.011.** Over the same rows, actual error spans **0.875 Å to 1.869 Å — a range of 1 Å.**

**Correlation between ipTM and measured error: r = −0.23.**

The worst prediction in the set (9XME, 1.869 Å) has ipTM 0.987 — **higher** than the best one (9WK0, 0.875 Å, ipTM 0.988 — statistically the same). The confidence score cannot tell them apart.

And note the last two rows: `AMDLGIHKV` and `AMDLGIDKV` differ at one position. 1.720 Å and 1.869 Å, ipTM 0.980 and 0.987. **The model is more confident about the worse one.**

### 2.4 Four more demonstrations of the same thing

| Test | Result |
|---|---|
| Correct allele (HLA-A\*02:01) vs. **wrong** allele (HLA-A\*03:01), same peptide | ipTM 0.987 vs **0.988** — the wrong allele scored **higher** |
| Three mutant / germline pairs | differences in the third decimal place; KRAS mutant 0.991 vs germline 0.987 |
| Full pMHC:TCR complex, receptor known to recognise | ipTM 0.947 — *lower* than peptide-only |
| Wild-type TCR control, receptor known **not** to recognise | indistinguishable |

The wrong-allele test came from a research agent catching an error in my own smoke test: **UniProt P04439 is HLA-A\*03:01, not A\*02:01.** The mistake turned into the cleanest single demonstration in the project — a deliberately mismatched peptide–HLA pair that the model was *more* confident about than the correct one.

> **Five independent demonstrations. Boltz confidence reports familiarity with a structural motif, not correctness, and not biology.** This is why the pipeline does not rank on it.

### 2.5 The ternary complex

Full pMHC:TCR recognition complex — the step after presentation. KRAS G12D `GADGVGKSA` / HLA-C\*08:02 / **TCR9d** from patient 3995, characterised in Sim *et al.* (*PNAS* 2020).

*Attribution note, because we got this wrong once: 6ULN's receptor is **TCR9d**, not the receptor from Tran* et al. *(*NEJM* 2016). Tran reported the TIL therapy and identified the epitopes; the TCR structures are Sim* et al. *2020. We confirmed it by extracting the CDR3β from our own predicted chain E — `CASSLGQTNYGYTF`, which is TCR9d, patient 3995. Tran's patient was 4095.*

| | |
|---|---|
| Residues / chains | **812 / 5** |
| Wall time | **133 s** |
| GPU peak | 95%, 42.2 W |
| ipTM / pLDDT | 0.9468 / 0.9687 |

| Chain | Cα RMSD | Centre-of-mass displacement |
|---|---:|---:|
| Peptide | **0.32 Å** | |
| β2-microglobulin | 0.46 Å | |
| TCR α | **1.42 Å** | 1.10 Å |
| TCR β | **1.50 Å** | 1.37 Å |

**Caveats, both of which matter:**

1. **Retrospective.** 6ULN was published in 2020 and may be in the training data.
2. **Structural accuracy is not immunogenicity.** Predicting where a *known* TCR docks says nothing about whether a given person's repertoire contains one. This is the single most important caveat in the project and it is in the UI text.

*The bug worth recording: the TCR initially appeared 72 Å out of place. 6ULN's biological assembly applies operator 1 to the pMHC chains and operator 2 to the TCR chains — comparing against the asymmetric unit compares against the wrong thing. After `gemmi.make_assembly`: 1.42 / 1.50 Å.*

---

## 3. Performance on the Nano

Full detail in [HARDWARE.md](HARDWARE.md) §2. Headlines:

| | Measured |
|---|---|
| Structure prediction, 383 residues, cached MSA | **64.3 s** mean (n=7, range 62–66) |
| **Batched, 5 in one process** | **36.0 s each → 100/hour, 1.79× speedup** |
| Ternary complex, 812 residues | 133 s |
| Screen, 1,890 candidates | **8.8 s** (~430 peptides/s, CPU) |
| LLM summary | ~4 s (qwen3:8b, 5.7 tok/s, 100% GPU) |
| Peak GPU / power / temperature | **96% / 38 W / 46 °C** |
| Sustained BF16 | **53.4 TFLOPS** |
| Full offline pipeline | screen 8.8 s → structure 64 s → summary 4 s |

Multi-node figures are **projections** and labelled as such everywhere they appear.

---

## 4. Reproducing these

```bash
pytest -q                          # 101 tests

python scripts/validate_screen.py  # → benchmarks/auc.json
                                   #   benchmarks/screen_validation.json
                                   #   benchmarks/precision_at_k.json
python scripts/validate_tesla.py   # → benchmarks/tesla_validation.json
```

Structure benchmarks need a GPU and Boltz-2 — see [BUILD-GUIDE.md](../BUILD-GUIDE.md). Predicted structures and `benchmarks/holdout_structures.json` ship with the repo so the numbers can be checked without one.

| File | Contents |
|---|---|
| `benchmarks/auc.json` | Bjerregaard AUC, all strata |
| `benchmarks/screen_validation.json` | filter-rule enrichment table |
| `benchmarks/precision_at_k.json` | precision@k by ranker |
| `benchmarks/tesla_validation.json` | TESLA AUC and precision@k |
| `benchmarks/holdout_structures.json` | 12 crystals with RMSD and ipTM |
| `benchmarks/measured.json` | every Nano timing and telemetry reading |

---

## 5. The summary table

| Question | Answer | Basis |
|---|---|---|
| Does the screen rank usefully? | **Yes — AUC 0.777 / 0.759** | 2,555 lab-tested peptides |
| How good is a top-25 shortlist? | **16–32% precision, 5–6× enrichment** | both benchmarks |
| How often are top candidates wrong? | **68–84%** | same data |
| Are the structures accurate? | **1.41 Å median**, all under 2 Å | 9 post-cutoff crystals |
| Can confidence scores rank candidates? | **No** | 5 independent demonstrations, r = −0.23 |
| Does the mutant/germline differential work? | **No — 0.592 and 0.412** | both benchmarks; 0.412 is below random |
| Does it run offline on one Nano? | **Yes** | egress blocked, 64 s |
| How fast? | **100 candidates/hour batched** | measured, single node |
| Does it scale to more nodes? | **Projection only** | we had one Nano |
