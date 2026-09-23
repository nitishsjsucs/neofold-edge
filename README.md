# NeoFold Edge

A private, on-premise research-triage workstation for tumour neoantigen prioritisation,
built for the HP ZGX Nano (NVIDIA GB10). It turns a tumour variant file into a ranked,
explained shortlist of candidate peptides, and predicts the 3D peptide–HLA complex
locally — no cloud inference, no external APIs.

**Research prioritisation only.** Predicted values are hypotheses, not measurements.
Not a diagnostic, treatment recommendation, or vaccine design.

## Quick start (local, no GPU)

```bash
uv venv --python 3.12 .venv-local && . .venv-local/bin/activate
uv pip install mhcflurry fastapi uvicorn pytest
mhcflurry-downloads fetch models_class1_presentation
python -m uvicorn app.main:app --port 8420
```

## Layout

| Path | What it is |
|---|---|
| `neofold/variants.py` | variant file -> mutated protein -> candidate peptide windows |
| `neofold/screen.py`   | MHCflurry binding screen + mutant/wild-type triage rules |
| `neofold/pipeline.py` | the funnel: VCF -> ranked shortlist |
| `neofold/telemetry.py`| GB10-aware GPU telemetry |
| `app/`                | FastAPI server + offline UI with a vendored Mol* viewer |
| `scripts/`            | Nano-side runners (structure prediction, validation, benchmarks) |
| `research/`           | sourced research notes |
| `BUILD-GUIDE.md`      | **verified** install + measured results on the Nano |

## Key measured results

- Boltz-2 on GB10: 383-residue peptide–HLA complex in **58 s**, peak 96% GPU / 38 W
- Accuracy vs crystal structure 6ULN: **0.486 Å** peptide backbone RMSD (with MSA)
- Screen: 1,890 peptides in ~9 s; both published KRAS G12D epitopes rank #1 and #2
- ⚠️ Boltz confidence does **not** discriminate binders — see BUILD-GUIDE §6
