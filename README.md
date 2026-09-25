# NeoFold Edge

**A private, on-premise AI workstation that turns a tumour genome into a small, ranked, explained shortlist of neoantigen research candidates — and tells you how often it is wrong.**

Built for the HP ZGX Nano (NVIDIA GB10 Grace Blackwell). Runs entirely offline: no cloud inference, no external APIs, no data leaving the building.

> **Research prioritisation only.** Every value this produces is a prediction, not a measurement. This is not a diagnostic, a treatment recommendation, or a vaccine design. Expert review and laboratory validation are required.

---

## The one-paragraph version

Cancer mutations create peptides the immune system can, in principle, recognise. Finding which ones is a prediction problem, and most predictions are wrong — in the largest prospective test ever run, **608 carefully-chosen candidates were tested in the laboratory and 37 worked**. NeoFold Edge screens thousands of candidate peptides in seconds on CPU, predicts 3D peptide–HLA structures in about a minute on the GB10, measures a contact specified in advance from a crystal structure, and writes a plain-language evidence summary with a local language model. Every number it reports has been validated against experimental data, and the failures are documented alongside the successes.

---

## The three numbers that matter

| Claim | Measured | How |
|---|---|---|
| **The screen ranks usefully** | **AUC 0.777 / 0.759** | 2,555 peptides with experimental T-cell assay outcomes, across two independent benchmarks |
| **The structures are accurate** | **1.41 Å median** | 9 crystal structures deposited *after* the model's training cutoff |
| **It runs on one Nano, offline** | **8.8 s + 64 s** | 1,890 candidates screened, then one structure folded, with all network egress blocked |

Every one of these is reproducible from this repository. See [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

---

## Table of contents

| Document | What it covers |
|---|---|
| **README.md** (this file) | The problem, the approach, the headline results |
| [docs/PROBLEM.md](docs/PROBLEM.md) | The biology, why this is hard, what the field actually achieves |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Pipeline design, module map, data flow, why each layer exists |
| [docs/HARDWARE.md](docs/HARDWARE.md) | The GB10, why edge compute, measured telemetry, scaling, the power fault |
| [docs/BENCHMARKS.md](docs/BENCHMARKS.md) | Every measurement, with methodology and caveats |
| [docs/SCIENCE.md](docs/SCIENCE.md) | What we can and cannot claim, and the errors we found in our own work |
| [BUILD-GUIDE.md](BUILD-GUIDE.md) | Verified install on the Nano, every bug and its fix |
| [PITCH.md](PITCH.md) | The 4-minute demo script |

---

## The problem

A tumour accumulates mutations. Some produce altered proteins; some of those are chopped up and displayed on the cell surface by HLA molecules; a few of those displayed fragments look foreign enough that a T-cell can recognise them. Those few are **neoantigens**, and they are what a personalised cancer immunotherapy would target.

The difficulty is arithmetic. A single tumour yields hundreds to thousands of candidate peptides. Laboratory validation of one candidate costs weeks. So the entire field runs on prediction — and prediction here is genuinely hard:

- **Base rate is brutal.** TESLA (Wells *et al.*, *Cell* 2020) tested 608 top-ranked candidates from 25 pipelines. **37 were immunogenic — 6%.**
- Across 1,948 published neopeptide–HLA pairs, **53 (2.7%)** elicited a T-cell response.
- And 96% of those failures had *excellent* predicted binding. Binding prediction is necessary and nowhere near sufficient.

So the honest goal is not "find the neoantigen". It is: **take a thousand candidates down to a handful a researcher can afford to test, be several times better than chance while doing it, and be explicit about the residual error.**

That is what this system is built and measured to do.

---

## How it works

```mermaid
flowchart TD
    A["Tumour variant file<br/><i>VCF, 50 variants</i>"] --> B["Peptide windows<br/><i>1,890 candidates</i>"]
    B --> C["Self-similarity filter<br/><i>CPU · exact proteome match</i>"]
    C -->|"13 cut — normal human peptides"| X1[ ]
    C --> D["MHC binding screen<br/><i>CPU · MHCflurry · 0.8 s</i>"]
    D -->|"22 presented"| E["Structure prediction<br/><i>GB10 GPU · Boltz-2 · 64 s</i>"]
    E --> F["Evidence layer<br/><i>contact · dynamics · TCR complex</i>"]
    F --> G["Local LLM summary<br/><i>GB10 GPU · qwen3:8b · 4 s</i>"]
    G --> H["Construct assembly<br/><i>exhaustive junction search</i>"]

    style X1 fill:none,stroke:none
    style A fill:#e8e8e6,stroke:#888780,color:#2c2c2a
    style B fill:#e8e8e6,stroke:#888780,color:#2c2c2a
    style C fill:#e1f5ee,stroke:#1d9e75,color:#04342c
    style D fill:#e1f5ee,stroke:#1d9e75,color:#04342c
    style E fill:#eeedfe,stroke:#7f77dd,color:#26215c
    style F fill:#eeedfe,stroke:#7f77dd,color:#26215c
    style G fill:#eeedfe,stroke:#7f77dd,color:#26215c
    style H fill:#faece7,stroke:#d85a30,color:#4a1b0c
```

**Teal = local CPU. Purple = GB10 GPU. Grey = data. Coral = output.**

Each stage is a separate module with its own tests. The full design rationale — including why the cheap filters run first and why structure prediction is deliberately *not* used for ranking — is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Why the edge, specifically

This is not a latency story. Nobody needs a neoantigen shortlist in 50 milliseconds. The argument is narrower and more defensible:

| | Cloud workflow | NeoFold Edge |
|---|---|---|
| **Raw genomic data** | must leave the institution | stays on the local network |
| **Governance** | data-use agreement, institutional certification, an external processor in scope | none of those steps exist |
| **Internet outage** | work stops | work continues — proven with egress blocked |
| **Cost model** | variable GPU + egress | owned hardware |

**A correction we insist on:** the cost argument is weak and we do not make it. Moving a whole-exome tumour/normal pair costs roughly **$5** in egress. And **DNA is not one of HIPAA's 18 Safe Harbor identifiers** — a claim that circulates widely and is checkable in the CFR. The real argument is that local compute *removes* a governance step rather than satisfying one.

Full treatment, with the genomic re-identification literature, in [docs/HARDWARE.md](docs/HARDWARE.md).

---

## Results

### The screen, against experimental T-cell data

Two independent benchmarks. Every peptide has a real assay outcome.

| | Bjerregaard 2017 | TESLA 2020 |
|---|---|---|
| Peptides | 1,947 | 608 |
| True responders | 53 (2.72%) | 37 (6.09%) |
| Negatives | pooled, 13 studies | **same-patient hard negatives** |
| **Our AUC** | **0.777** | **0.759** |
| **Precision @ top 25** | **16%** | **32%** |
| **Enrichment** | **5.9×** | **5.3×** |

Two observations worth stating plainly:

1. **Our predicted score matches TESLA's *experimentally measured* binding affinity** (0.759 vs 0.747). The honest reading is not that prediction beats experiment — it is that **binding affinity, however obtained, is not a strong discriminator of immunogenicity**. The ceiling is the biology.
2. **The mutant-versus-germline differential scores 0.412 on TESLA — below random.** We shipped it as a filter early on. The data says it was worse than chance, so it is an annotation now, not a gate.

### Structure prediction, held out

| Set | n | Median peptide backbone RMSD |
|---|---|---|
| Pre-cutoff, possibly memorised | 3 | 1.01 Å |
| **Post-cutoff, held out** | **9** | **1.41 Å** (all under 2 Å) |
| Full pMHC:TCR complex, 812 residues | 1 | TCR α 1.42 Å, TCR β 1.50 Å |

We quote **1.41 Å**, the held-out figure. Our two original validation anchors gave 0.42 Å — but both predate the model's training cutoff, so that number is a training-set result and labelled as one.

### On the Nano

| | Measured |
|---|---|
| Structure prediction | 64 s / candidate (383 residues, cached MSA) |
| Batched throughput | **100 candidates/hour** (36 s each — the checkpoint loads once) |
| Peak GPU | **96% utilisation, 38 W**, 46 °C |
| Raw compute | 53.4 TFLOPS bf16 sustained |
| Local LLM | qwen3:8b, 100% GPU, 5.7 tok/s |
| Full offline pipeline | screen 8.8 s → structure 64 s → summary 4 s |

---

## What we got wrong

This section exists deliberately. A tool that reports only its successes has not been tested.

| # | Error | How it was caught | Fix |
|---|---|---|---|
| 1 | Shipped a filter **worse than random** (DAI ≥ 2, enrichment 0.96×) | Validation against 1,947 assay outcomes | Demoted to an annotation — the differential detects *anchor* mutations, which are the ones T-cells are least likely to see |
| 2 | Accuracy claim **3× optimistic** | Both validation crystals predate the training cutoff | Re-measured on 9 held-out structures: 1.41 Å |
| 3 | Labelled **a normal human peptide** a tumour target | Self-similarity filter added afterwards | `ICDFGLARV` occurs verbatim in ERK2 — the DFG motif is conserved across the kinome |
| 4 | Our **near-self metric was vacuous** | Every candidate trivially flagged | Every missense neoepitope is 1 mismatch from its own germline peptide; now excluded |
| 5 | A **test asserted a conclusion our own data refuted** | Wild-type TCR control | "The model knows recognition is harder" holds equally for a complex the TCR does *not* recognise |
| 6 | The **LLM asserted three unsupported claims** | Added a claim checker after the first run | Including that ipTM "supports reliability" — which we had already disproved five times |

Those are six of **twelve**. The rest — including citing the wrong paper for our own TCR, diagnosing a hardware fault wrongly twice, and shipping demo input files with a mixed genome build — are in [docs/SCIENCE.md](docs/SCIENCE.md) §3, each with the mechanism that caused it.

Two constraints we place on our own headline results are worth knowing before you read the rest:

- **The molecular dynamics run must not be used to support the salt-bridge claim.** Generalised-Born implicit solvent over-stabilises salt bridges by 3–4 kcal/mol, and the failure is specifically in guanidinium groups — Arg156 is exactly the atom type at fault. That caveat is in the tool's own output, not just the documentation.
- **Our three MD replicates agree closely, and that is not good news.** Knapp *et al.* (2018) show that sub-10 ns agreement is the signature of undersampling, not stability. We are 100× below the field's state of the art for this system class.

---

## Quick start

```bash
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install mhcflurry fastapi uvicorn gemmi pytest
mhcflurry-downloads fetch models_class1_presentation
python -m uvicorn app.main:app --port 8420
```

Open <http://127.0.0.1:8420>. The app needs no GPU — structure prediction is the only GPU stage, and precomputed structures ship with the repo.

For the full Nano install including Boltz-2, OpenMM and Ollama, see [BUILD-GUIDE.md](BUILD-GUIDE.md) — every step was executed, not looked up.

```bash
pytest -q        # 101 tests
```

---

## Repository layout

```
neofold-edge/
├── neofold/              # the pipeline, one module per stage
│   ├── variants.py       #   variant file → mutated protein → peptide windows
│   ├── screen.py         #   MHCflurry binding screen, DAI, triage rules
│   ├── selfsim.py        #   human proteome search (is this actually a neoantigen?)
│   ├── expression.py     #   normal-tissue expression as an off-tumour safety flag
│   ├── pipeline.py       #   the funnel
│   ├── structure.py      #   Boltz-2 invocation with the settings that work on GB10
│   ├── validate.py       #   RMSD against crystal structures; ensemble spread
│   ├── contacts.py       #   pre-registered contact measurement
│   ├── md.py             #   OpenMM stability check
│   ├── report.py         #   local LLM summary + two guardrails
│   ├── construct.py      #   polyepitope assembly, exhaustive junction search
│   └── telemetry.py      #   GB10-aware GPU telemetry
├── app/                  # FastAPI server + offline UI (vendored Mol*)
├── tests/                # 101 tests
├── benchmarks/           # every measurement as JSON
├── data/                 # demo variants, reference sequences, proteome, GTEx
├── results/              # predicted structures, MD traces, holdout set
├── scripts/              # Nano setup, offline proof, benchmark runners
└── research/             # 11,000 lines of sourced research notes
```

---

## Licence and provenance

The pipeline code is ours. The components it orchestrates are not:

| Component | Licence | Role |
|---|---|---|
| [Boltz-2](https://github.com/jwohlwend/boltz) | MIT | biomolecular structure prediction |
| [MHCflurry](https://github.com/openvax/mhcflurry) | Apache 2.0 | peptide–MHC binding prediction |
| [OpenMM](https://openmm.org) | MIT / LGPL | molecular dynamics |
| [Mol*](https://molstar.org) | MIT | 3D molecular viewer |
| [gemmi](https://gemmi.readthedocs.io) | MPL 2.0 | structural file handling |

Boltz-2 being **MIT with open weights** is what makes this possible at all — AlphaFold 3's weights are non-commercial and not approved for clinical use.

Benchmark data: Bjerregaard *et al.* 2017 (CC BY), Wells *et al.* 2020 (TESLA), UniProt, GTEx v10, RCSB PDB.
