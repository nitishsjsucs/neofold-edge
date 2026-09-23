# GPU Molecular Dynamics "Stability Stress Test" on HP ZGX Nano (GB10, sm_121, ARM64)

**Research date:** 2026-09-23 · **Demo deadline:** 2026-09-26
**Target machine:** Ubuntu 24.04.5 · aarch64 · NVIDIA GB10 Grace Blackwell · CC 12.1 (sm_121) · CUDA 13.0 / driver 580.173.02 · 121 GB unified · 20 CPU cores · Python 3.12.3

---

## 0. VERDICT (read this first)

**GO on OpenMM.** Confidence: high on install, medium-high on CUDA-platform runtime.

The single fact that decides this: **OpenMM ships first-party PyPI wheels for `manylinux_2_34_aarch64` + `cp312`, plus a matching CUDA 13 plugin wheel, as of 8.6.1.** No conda, no compiling, no sudo.

Verified from the PyPI JSON API (2026-09-23):

- `openmm-8.6.1-cp312-cp312-manylinux_2_34_aarch64.whl` — exists
  ([pypi.org/pypi/openmm/8.6.1/json](https://pypi.org/pypi/openmm/8.6.1/json))
- `openmm_cuda_13-8.6.1-py3-none-manylinux_2_34_aarch64.whl` — exists
  ([pypi.org/pypi/openmm-cuda-13/json](https://pypi.org/pypi/openmm-cuda-13/json))
- Its deps `nvidia-cuda-runtime`, `nvidia-cuda-nvcc`, `nvidia-cuda-nvrtc`, `nvidia-cuda-cupti` (all `>=13,<14`) and `nvidia-cufft` (`>=12,<13`) all publish `manylinux2014_aarch64` wheels
  ([pypi.org/pypi/nvidia-cuda-nvrtc/json](https://pypi.org/pypi/nvidia-cuda-nvrtc/json))
- `manylinux_2_34` needs glibc ≥ 2.34; Ubuntu 24.04 ships glibc 2.39. Fine.
- aarch64 wheels first appeared in the 8.5.0b0 series, so this is new-ish but has had several releases to settle.

**GO on the MD stage as a demo feature** — but at a *smaller simulated timescale than you asked for*. Realistic expectation is **~0.3–1.5 ns per candidate in 1–3 minutes wall clock**, not 1–3 ns. See §6.

**NO-GO on presenting it as evidence of immunogenicity or binding affinity.** See §8. The literature is unambiguous that the published pMHC-MD work that correlates with immunology uses **200 ns to 1 µs per system in explicit solvent** — 200× to 3000× your budget — and even then buys ~**+0.01 AUC** over a sequence-only baseline. Frame it as a *physics sanity check / structural plausibility filter*, never as a stability or immunogenicity predictor.

---

## 1. Can OpenMM run here, and how do I install it without sudo?

### 1.1 Is there a PyPI wheel for linux-aarch64 / cp312?

**Yes.** This is the key finding and it inverts the received wisdom ("OpenMM is conda-forge only"). OpenMM began publishing official PyPI wheels via the [openmm/openmm-wheels](https://github.com/openmm/openmm-wheels) repo, and the official Getting Started guide now lists `pip install openmm` and `pip install openmm[cuda13]` as first-class installation routes ([docs.openmm.org getting started](https://docs.openmm.org/latest/userguide/application/01_getting_started.html)).

Full aarch64 wheel set for 8.6.1 (from the PyPI JSON API):

| Package | aarch64 wheel | Python tags |
|---|---|---|
| `openmm` 8.6.1 | `manylinux_2_34_aarch64` | cp310, cp311, **cp312**, cp313, cp314 |
| `openmm-cuda-13` 8.6.1 | `manylinux_2_34_aarch64` | `py3-none` (arch-specific, Python-agnostic) |
| `openmm-cuda-12` 8.6.1 | `manylinux_2_34_aarch64` | `py3-none` |
| `openmm-hip-6/7` | **x86_64 only** | n/a (irrelevant here) |

Extras defined on the `openmm` metapackage: `cuda12`, `cuda13`, `hip6`, `hip7`.

> Note: an early web summary claimed "no aarch64 Linux wheels." That was wrong — it came from a truncated read of the PyPI simple index. The per-version JSON API is authoritative and lists them explicitly. **Verify on-machine in 5 seconds** with `pip index versions openmm` / `pip download --no-deps openmm==8.6.1 -d /tmp/x`.

### 1.2 conda-forge for linux-aarch64?

conda-forge does build `openmm` for `linux-aarch64` ([anaconda.org/conda-forge/openmm](https://anaconda.org/conda-forge/openmm)), and CUDA variants are selected with `cuda-version=`. conda-forge builds CUDA 12+ variants. **However, for this machine conda-forge is now the *worse* option**, because:

- You'd need micromamba + a second environment, then bridge Boltz-2 outputs across environments.
- conda-forge's CUDA-13 aarch64 coverage for openmm is *not confirmed* (⚠️ unverified) — you may land on a CUDA-12 build, which then has to run against a CUDA-13 driver.
- The pip route is one command inside a plain venv.

Keep it as **fallback #2** (§1.6).

### 1.3 Will the CUDA platform work on sm_121?

**Very likely yes**, and for a structural reason that distinguishes OpenMM from the sea of PyTorch/vLLM "no kernel image is available" reports you'll find when you search Blackwell + sm_121.

**Why the usual sm_121 breakage does not apply.** Every sm_121 horror story in the wild ([vLLM #36821](https://github.com/vllm-project/vllm/issues/36821), [vLLM #31128](https://github.com/vllm-project/vllm/issues/31128), [PyTorch #159207](https://github.com/pytorch/pytorch/issues/159207), [CUTLASS #2947](https://github.com/NVIDIA/cutlass/issues/2947)) has the same root cause: **shipped `.so` / fatbin files contain pre-compiled SASS for sm_90 or sm_120 and no PTX fallback for sm_121**. It is a *build-time* problem in libraries that AOT-compile kernels.

OpenMM does not do that. **OpenMM's CUDA platform compiles essentially all of its compute kernels at runtime**, from CUDA C source shipped as text, via NVRTC, targeting whatever compute capability the device reports ([OpenMM Dev Guide — The CUDA Platform](https://docs.openmm.org/8.0.0/developerguide/07_cuda_platform.html); the NVRTC move is discussed in [openmm#4105](https://github.com/openmm/openmm/issues/4105)). A new `sm_121` device therefore gets `sm_121` kernels generated on the spot, provided NVRTC understands the target — and CUDA 13.x NVRTC does.

**Positive precedent on the previous Blackwell step:** OpenMM's CUDA platform was benchmarked successfully end-to-end on an RTX 5090 (sm_120) with CUDA 12.8, across GBSA, PME, AMOEBA and all AMBER20 tests, with **no sm_120-related errors reported** ([openmm#4854](https://github.com/openmm/openmm/issues/4854)). ⚠️ *No sm_121 / GB10 / DGX Spark OpenMM report was found anywhere.* You would be first, or near it. sm_120 → sm_121 is a minor-revision step within consumer/GB10 Blackwell, and OpenMM uses no arch-conditional MMA/tcgen05 instructions (the thing that actually breaks between sm_120 and sm_121 in CUTLASS-based stacks).

**The one real risk: PTX version vs driver.** NVRTC emits PTX; the driver JIT-compiles PTX → SASS. CUDA's *minor version compatibility* guarantee **explicitly excludes PTX JIT**: a newer toolkit's PTX ISA can be rejected by an older driver with `CUDA_ERROR_UNSUPPORTED_PTX_VERSION` (218) — exactly the failure mode in [openmm#3474](https://github.com/openmm/openmm/issues/3474). Your driver is 580.173.02 = **CUDA 13.0**, but `pip install openmm[cuda13]` will pull the newest `nvidia-cuda-nvrtc` in the 13.x line (currently **13.4.92**), which can emit PTX newer than a 13.0 driver accepts.

**Mitigation (do this — it costs nothing):** pin NVRTC to the 13.0 series. Both `13.0.48` and `13.0.88` publish aarch64 wheels.

### 1.4 If CUDA fails — OpenCL or CPU?

- **OpenCL:** ⚠️ unverified whether the aarch64 `openmm` wheel bundles the OpenCL platform, and whether the GB10 driver exposes an ICD on ARM. If it does, expect ~0.6–0.9× CUDA. Test with `python -m openmm.testInstallation`, which enumerates every available platform.
- **CPU on 20 ARM cores:** **not viable.** OpenMM's CPU platform implements GB solvation as an O(N²) pairwise loop with no GPU-style parallelism; for ~6,000 atoms expect single-digit to low-tens ns/day. In a 3-minute window that is **~0.01–0.03 ns** — i.e. roughly a long energy minimization, not a simulation. If CUDA fails, **do not fall back to CPU MD.** Fall back to the non-MD proxy in §8.4.

### 1.5 EXACT INSTALL COMMANDS (recommended path)

**Install into a SEPARATE venv.** Do not touch the working Boltz-2 environment. `openmm[cuda13]` drags in `nvidia-cuda-runtime`, `nvidia-cuda-nvrtc`, `nvidia-cufft` etc.; your Boltz venv already has `torch 2.14.0+cu132` with its own pinned `nvidia-*` stack. A version fight there costs you the demo. Two venvs, one CIF file passed between them, zero risk.

```bash
# ---- 1. Create an isolated MD venv (no sudo, no conda) -------------------
python3.12 -m venv "$HOME/.venvs/md"
source "$HOME/.venvs/md/bin/activate"
python -m pip install -U pip wheel

# ---- 2. OpenMM + CUDA 13 plugin, with NVRTC pinned to the 13.0 series ----
#    The pin keeps emitted PTX within what driver 580.173.02 (CUDA 13.0) accepts.
python -m pip install \
  "openmm[cuda13]==8.6.1" \
  "nvidia-cuda-nvrtc==13.0.88" \
  "nvidia-cuda-runtime==13.0.88"

# ---- 3. Structure prep + analysis (both work on aarch64) ----------------
#    pdbfixer is sdist-only but PURE PYTHON -> builds anywhere, no compiler needed.
python -m pip install "pdbfixer==1.12.0" "mdtraj==1.11.1.post2" numpy

# ---- 4. SMOKE TEST — do this before anything else -----------------------
python -m openmm.testInstallation
```

`python -m openmm.testInstallation` is the documented verification step; it lists every registered platform and cross-checks forces between them ([OpenMM Getting Started](https://docs.openmm.org/latest/userguide/application/01_getting_started.html)). **You want to see `CUDA` in the platform list and a small force-comparison error against `Reference`.** If CUDA is missing or errors, go to §1.6.

**If the NVRTC pin causes a resolver conflict**, install unpinned first, confirm it works, and only downgrade NVRTC if you hit `CUDA_ERROR_UNSUPPORTED_PTX_VERSION`:

```bash
python -m pip install "openmm[cuda13]==8.6.1"
python -m openmm.testInstallation
# only if it fails with error 218 / unsupported PTX:
python -m pip install --force-reinstall "nvidia-cuda-nvrtc==13.0.88"
```

**If `openmm[cuda13]` resolves badly, try CUDA 12** — CUDA 13 drivers run CUDA 12 userspace libraries:

```bash
python -m pip install "openmm[cuda12]==8.6.1"
```

### 1.6 Fallback ranking (in order — do not skip down the list)

| # | Option | Cost to try | Verdict |
|---|---|---|---|
| **1** | `pip install openmm[cuda13]` into a fresh venv | 5 min | **Do this.** Highest probability, lowest blast radius. |
| **2** | `pip install openmm[cuda12]` (CUDA-12 plugin on a CUDA-13 driver) | 3 min | Good second try if 13 misbehaves. |
| **3** | OpenCL platform (already in the same wheel — just select it) | 0 min | Free to test; ⚠️ availability on aarch64 unverified. |
| **4** | micromamba + conda-forge (§1.7) | 20–40 min | Only if pip is genuinely broken. |
| **5** | NGC container (§2.2) | 30–60 min + huge pull | ⚠️ No ARM64 OpenMM container confirmed to exist. Do not bet the demo on this. |
| **6** | **Drop MD; ship the non-MD proxy (§8.4)** | 1–2 h to build | **This is your real safety net.** Decide by Thursday noon. |

### 1.7 Fallback #4: micromamba into $HOME (no root)

```bash
cd "$HOME"
mkdir -p "$HOME/micromamba" && cd "$HOME/micromamba"
curl -Ls https://micro.mamba.pm/api/micromamba/linux-aarch64/latest | tar -xvj bin/micromamba
export MAMBA_ROOT_PREFIX="$HOME/micromamba"
eval "$("$HOME/micromamba/bin/micromamba" shell hook -s bash)"

micromamba create -y -n md -c conda-forge \
    python=3.12 openmm pdbfixer mdtraj numpy
micromamba activate md
python -m openmm.testInstallation
```

Add `cuda-version=12` (or `13`) to pin the CUDA variant ([conda-forge openmm](https://anaconda.org/conda-forge/openmm)). ⚠️ **Verify `linux-aarch64` + CUDA-13 build availability before relying on this** — `micromamba search -c conda-forge --platform linux-aarch64 openmm`.

### 1.8 Offline pre-fetch (the demo has no internet)

Do this **today**, on the target machine, while it still has network:

```bash
source "$HOME/.venvs/md/bin/activate"
mkdir -p "$HOME/wheelhouse"
python -m pip download \
  "openmm[cuda13]==8.6.1" "nvidia-cuda-nvrtc==13.0.88" "nvidia-cuda-runtime==13.0.88" \
  "pdbfixer==1.12.0" "mdtraj==1.11.1.post2" numpy \
  -d "$HOME/wheelhouse"

# Reinstall test, fully offline:
python -m pip install --no-index --find-links "$HOME/wheelhouse" \
  "openmm[cuda13]==8.6.1" pdbfixer mdtraj
```

**Nothing else needs downloading.** The AMBER/CHARMM force-field XMLs (`amber14-all.xml`, `implicit/obc2.xml`, …) ship *inside* the `openmm` wheel under `openmm/app/data/`. There is no runtime parameter download. This is a genuine advantage of OpenMM over GROMACS/AMBER setups for an offline demo.

**Also pre-warm the driver's PTX→SASS JIT cache** by running the real pipeline once end-to-end before you unplug:

```bash
export CUDA_CACHE_MAXSIZE=4294967296   # 4 GB; default is small and evicts
export CUDA_CACHE_PATH="$HOME/.nv/ComputeCache"
```

⚠️ OpenMM itself does **not** appear to persistently cache NVRTC output across processes (no documented `OPENMM_CACHE_DIR`), so expect a **fixed per-process startup cost for kernel compilation**. Measure it (§6.3) — on a small ARM core it can be 10–40 s and it comes straight out of your 1–3 minute budget. Budget it, or amortize by simulating all candidates in **one** process.

---

## 2. Alternatives if OpenMM dies

### 2.1 GROMACS
- ARM64 builds exist and GROMACS compiles cleanly for `aarch64` with SVE/NEON SIMD, **but you must compile it yourself** (CMake + a CUDA-13-capable nvcc). That is a multi-hour job with real failure modes, on a deadline. ⚠️ No pre-built aarch64+CUDA GROMACS wheel or no-root binary distribution found.
- GROMACS also needs `pdb2gmx` topology generation, `.mdp` files, and box/solvation setup — substantially more moving parts than OpenMM's 30-line script.
- **Verdict: no.** Not by Saturday.

### 2.2 NGC / Docker container
Docker works on this machine, but: ⚠️ **I found no NVIDIA NGC container publishing an `linux/arm64` OpenMM image.** NGC's HPC catalog (GROMACS, NAMD, LAMMPS) is overwhelmingly `linux/amd64`. Pulling a multi-GB image with an unknown arch tag two days before demo is a bad trade when `pip install` takes 5 minutes. Also: the container would still hit the *same* sm_121 question, with less visibility. **Verdict: no.**

### 2.3 ASE / TorchMD / torch-native MD
Tempting because `torch 2.14.0+cu132` already runs on this machine, so sm_121 is already proven working in your existing venv.

- **TorchMD / TorchMD-NET:** needs an AMBER/CHARMM parameter pipeline anyway (it reads prmtop/psf), so you gain nothing on the setup side and lose OpenMM's maturity. Also ⚠️ aarch64 wheel status unverified.
- **A hand-rolled torch MD:** you would be writing a force field from scratch. Do not.
- **The honest torch-native option that *does* work:** skip the force field entirely and do §8.4's Boltz-ensemble proxy, which reuses the model you already have.

**Verdict: no MD alternative beats OpenMM here.** The realistic fork is OpenMM vs. no-MD.

### 2.4 The non-MD proxy
See **§8.4**. Short version: a multi-seed Boltz-2 ensemble-spread metric is cheaper, more honest, uses hardware you've already proven, and is arguably a *stronger* signal than 1 ns of implicit-solvent MD. **Build this regardless of whether OpenMM works** — it is both your fallback and a better headline number.

---

## 3. The minimal pMHC protocol

### 3.1 System

| Component | Residues |
|---|---|
| HLA class I heavy chain (α1/α2/α3 ectodomain) | ~275 |
| β2-microglobulin | 99 |
| Peptide (9-mer) | 9 |
| **Total** | **~383** |

**Atom counts (estimates, ±10%):**

| Configuration | Atoms |
|---|---|
| Boltz-2 output as-is (heavy atoms only, no H, no solvent) | ~2,950 |
| + hydrogens (PDBFixer, pH 7) | **~6,000** |
| + explicit TIP3P, 1.0 nm padding, neutralized | **~62,000–70,000** (~19k waters) |

### 3.2 Solvation: implicit, and here is why

**Use implicit solvent (GB). Explicit water is not an option at a 1–3 minute total budget.** Not primarily because of ns/day, but because of *fixed wall-clock overhead*:

| Stage | Explicit TIP3P | Implicit OBC2 |
|---|---|---|
| Solvate + neutralize (~65k atoms) | 5–20 s | 0 s |
| Minimization | 10–30 s (more atoms) | 3–10 s |
| NVT heating | 50–100 ps needed | 10–20 ps |
| **NPT box equilibration** | **100–500 ps, mandatory** | **not applicable** |
| Usable production in what's left of 3 min | ≈ 0 | most of it |

The NPT step is the killer. Without it your box density is wrong and the first several hundred ps are unphysical — which in a 3-minute run is *the entire run*. Implicit solvent has no box, no density, no pressure coupling, and equilibrates in ~10 ps.

**Caveat, to state out loud:** implicit solvent has no water viscosity, so **dynamics are artificially accelerated** — typically quoted as several-fold faster diffusion/conformational sampling than explicit water. For a "does it fall out of the groove" screen this cuts both ways: you see instability sooner (useful), but the effective timescale is not comparable to experiment (a caveat, not a fix). Say this in the demo.

**GB model choice: `implicit/obc2.xml`, not `implicit/gbn2.xml`.**
Both are implemented as `CustomGBForce` in OpenMM (verified from `openmm/app/data/implicit/*.xml` — `obc2.xml` → `GBSAOBC2Force`, `gbn2.xml` → `GBSAGBn2Force`, both from `openmm.app.internal.customgbforces`). GBn2 is the more accurate model but adds an extra "neck" correction pass, i.e. **another O(N²) sweep per step**. For a coarse stability screen, OBC2's accuracy is ample and it is materially faster. ⚠️ I did not find a head-to-head OBC2-vs-GBn2 ns/day number; measure it (§6.3).

**The single biggest speed lever: use a cutoff.**
The docs state explicitly: *"The only nonbonded methods that are supported with implicit solvent are `NoCutoff` (the default), `CutoffNonPeriodic`, and `CutoffPeriodic`"* ([Running Simulations](https://docs.openmm.org/latest/userguide/application/02_running_sims.html)). `NoCutoff` makes GB **O(N²)** — that is precisely why [openmm#3695](https://github.com/openmm/openmm/issues/3695) reports **9,266 atoms with GBn2 at only 54 ns/day on an A4000**, while the 2,489-atom `gbsa` benchmark hits **1,977 ns/day on the same GPU** (36× slower for 3.7× the atoms). Switching to `CutoffNonPeriodic` with a 1.8–2.0 nm cutoff puts you on a neighbour list and should recover most of that. It introduces small Born-radius errors at the cutoff; irrelevant at this level of claim, and worth disclosing.

### 3.3 Force field

`amber14-all.xml` + `implicit/obc2.xml`.

- `amber14-all.xml` (ff14SB protein) is the workhorse; it is what the PMC5573614 µs-scale pMHC study used (ff14SB / AMBER14) and what the GB radii were parameterized against.
- **CHARMM36 is also defensible** (the 2,883-peptide HLA-A2 MD study used CHARMM36m, [Briefings in Bioinformatics 25(1) bbad504](https://academic.oup.com/bib/article/25/1/bbad504/7560312)), but OpenMM's implicit-solvent XMLs are Amber-radii-based. **Use Amber14.** Do not mix.

### 3.4 Restraints — the design decision that makes the signal readable

**Restrain Cα atoms of β2-microglobulin and the HLA α3 domain (~res 183+) with a weak 1.0 kcal/mol/Å² harmonic. Leave the α1/α2 groove (res 1–182) and the peptide completely free.**

Rationale, and this is defensible to a judge:
1. β2m and α3 are **>20 Å from the peptide**; their drift is physically irrelevant to groove retention but *contaminates* any global RMSD.
2. It removes whole-complex rotation/translation and domain hinging from your signal without touching the thing you are measuring.
3. It is weak enough (1 kcal/mol/Å² ≈ thermal-scale) that it does not freeze the structure.
4. **It does not restrain the groove**, so you have not rigged the answer. Say this explicitly.

### 3.5 The full protocol

| Step | Setting |
|---|---|
| Prep | PDBFixer: missing heavy atoms, `addMissingHydrogens(pH=7.0)`, `removeHeterogens(keepWater=False)`, disulfides auto-detected |
| Force field | `amber14-all.xml` + `implicit/obc2.xml` |
| Nonbonded | `CutoffNonPeriodic`, cutoff **1.8 nm** |
| Constraints | `HBonds` |
| Hydrogen mass | **4 amu** (HMR) — documented in OpenMM as the enabler for large timesteps |
| Timestep | **4 fs** |
| Integrator | `LangevinMiddleIntegrator(310 K, 2/ps, 4 fs)` |
| Precision | `mixed` (use `single` for ~1.2–1.4× more speed; fine for 1 ns) |
| Minimization | `minimizeEnergy(tolerance=10 kJ/mol/nm, maxIterations=500)` |
| Equilibration | 10 ps with restraints on **all** protein Cα (including peptide), to settle added H |
| Production | restraints released on peptide + α1/α2; β2m/α3 Cα stay at 1.0 kcal/mol/Å² |
| Length | **however many steps fit the wall-clock budget** — set by time, not by ns (see script's `--budget-seconds`) |
| Trajectory | DCD, ~100–200 frames total |

**Realistic ns achieved: 0.3–1.5 ns.** See §6.

---

## 4. COMPLETE RUNNABLE SCRIPT

Save as `md_stress.py`. Run with `$HOME/.venvs/md/bin/python md_stress.py --cif boltz_out.cif --out run1/`.

```python
#!/usr/bin/env python3
"""
md_stress.py -- short implicit-solvent MD "stability stress test" for a
Boltz-2 predicted peptide-HLA class I complex.

This is a PHYSICS SANITY CHECK, not a binding-affinity or immunogenicity
predictor. See research-md-openmm.md section 8 before making any claim.

Usage:
    python md_stress.py --cif pred.cif --out run1/
    python md_stress.py --cif pred.cif --out run1/ --budget-seconds 120
    python md_stress.py --cif pred.cif --out run1/ --calibrate   # timing only
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
from openmm import (
    CustomExternalForce,
    LangevinMiddleIntegrator,
    Platform,
    unit,
)
from openmm.app import (
    CutoffNonPeriodic,
    DCDReporter,
    ForceField,
    HBonds,
    PDBFile,
    Simulation,
    StateDataReporter,
)
from pdbfixer import PDBFixer

# --------------------------------------------------------------------------
# Tunables
# --------------------------------------------------------------------------
TEMPERATURE = 310 * unit.kelvin          # body temperature
FRICTION = 2.0 / unit.picosecond
TIMESTEP = 4.0 * unit.femtoseconds       # safe with HMR(4 amu) + HBonds
HYDROGEN_MASS = 4.0 * unit.amu
CUTOFF = 1.8 * unit.nanometer            # O(N) GB instead of O(N^2). Big win.
EQUIL_PS = 10.0                          # restrained equilibration
SCAFFOLD_K = 1.0 * unit.kilocalories_per_mole / unit.angstrom**2
EQUIL_K = 5.0 * unit.kilocalories_per_mole / unit.angstrom**2
N_FRAMES = 150                           # target frames in the trajectory

# Residue index (0-based, within the HLA heavy chain) at which the alpha3
# domain begins. alpha1+alpha2 = the groove = residues 0..181.
ALPHA3_START = 182


def log(msg):
    print(f"[md_stress] {msg}", flush=True)


# --------------------------------------------------------------------------
# 1. Structure preparation
# --------------------------------------------------------------------------
def prepare(cif_path: Path, out_dir: Path):
    """CIF -> protonated, complete, force-field-ready topology + positions."""
    t0 = time.time()
    log(f"PDBFixer: reading {cif_path}")

    # PDBFixer auto-detects .cif/.pdbx and routes through openmm.app.PDBxFile.
    fixer = PDBFixer(filename=str(cif_path))

    # Boltz-2 emits complete chains; do NOT let PDBFixer invent loops.
    fixer.findMissingResidues()
    fixer.missingResidues = {}

    fixer.findNonstandardResidues()
    fixer.replaceNonstandardResidues()

    # Strip ions/ligands/waters. Boltz-2 pMHC output normally has none, but
    # a stray HETATM will blow up ForceField template matching.
    fixer.removeHeterogens(keepWater=False)

    fixer.findMissingAtoms()
    # addMissingAtoms() internally calls topology.createDisulfideBonds(),
    # which is REQUIRED here: PDBxFile does not infer disulfides from
    # geometry (it only reads struct_conn records, which Boltz does not
    # emit). HLA a2/a3 and B2M each carry one.
    fixer.addMissingAtoms(seed=0)

    fixer.addMissingHydrogens(pH=7.0)

    topology, positions = fixer.topology, fixer.positions

    n_ss = sum(
        1
        for b in topology.bonds()
        if b[0].name == "SG" and b[1].name == "SG"
    )
    log(f"disulfide bonds detected: {n_ss}  (expect 3 for a pMHC-I complex)")
    if n_ss < 3:
        log("WARNING: fewer disulfides than expected -- check the input CIF.")

    prepared_pdb = out_dir / "prepared.pdb"
    with open(prepared_pdb, "w") as fh:
        PDBFile.writeFile(topology, positions, fh, keepIds=True)
    log(f"prepared topology written: {prepared_pdb}  "
        f"({topology.getNumAtoms()} atoms, {time.time() - t0:.1f}s)")

    return topology, positions, prepared_pdb


def identify_chains(topology):
    """Return (peptide_chain, hla_chain, b2m_chain) by residue count.

    pMHC-I: HLA heavy chain is the longest, B2M ~99 aa, peptide 8-11 aa.
    """
    chains = sorted(topology.chains(), key=lambda c: len(list(c.residues())))
    if len(chains) < 3:
        raise RuntimeError(
            f"expected >=3 chains, found {len(chains)}. "
            "Is this really a pMHC complex?"
        )
    peptide, b2m, hla = chains[0], chains[1], chains[-1]
    log(
        f"chains -> peptide={peptide.id}({len(list(peptide.residues()))}aa) "
        f"B2M={b2m.id}({len(list(b2m.residues()))}aa) "
        f"HLA={hla.id}({len(list(hla.residues()))}aa)"
    )
    if not (6 <= len(list(peptide.residues())) <= 15):
        log("WARNING: shortest chain is not peptide-length. Check chain assignment.")
    return peptide, b2m, hla


# --------------------------------------------------------------------------
# 2. System construction
# --------------------------------------------------------------------------
def build_system(topology, positions, peptide, b2m, hla):
    ff = ForceField("amber14-all.xml", "implicit/obc2.xml")
    system = ff.createSystem(
        topology,
        nonbondedMethod=CutoffNonPeriodic,
        nonbondedCutoff=CUTOFF,
        constraints=HBonds,
        hydrogenMass=HYDROGEN_MASS,
        rigidWater=False,
        soluteDielectric=1.0,
        solventDielectric=78.5,
    )

    # Two restraint forces, each with its own global force constant so we can
    # switch them independently without rebuilding the System.
    def make_restraint(name):
        f = CustomExternalForce(
            f"{name}*periodicdistance(x,y,z,x0,y0,z0)^2"
        )
        f.addGlobalParameter(name, 0.0)
        for p in ("x0", "y0", "z0"):
            f.addPerParticleParameter(p)
        return f

    equil_force = make_restraint("k_equil")      # all protein CA
    scaffold_force = make_restraint("k_scaffold")  # B2M + HLA alpha3 CA only

    pos_nm = positions.value_in_unit(unit.nanometer)
    n_equil = n_scaf = 0
    for chain in topology.chains():
        for res_i, res in enumerate(chain.residues()):
            for atom in res.atoms():
                if atom.name != "CA":
                    continue
                xyz = pos_nm[atom.index]
                equil_force.addParticle(atom.index, xyz)
                n_equil += 1
                is_scaffold = (chain is b2m) or (
                    chain is hla and res_i >= ALPHA3_START
                )
                if is_scaffold:
                    scaffold_force.addParticle(atom.index, xyz)
                    n_scaf += 1

    system.addForce(equil_force)
    system.addForce(scaffold_force)
    log(f"restraints: {n_equil} CA (equil) / {n_scaf} CA (scaffold: B2M + HLA a3)")
    log("groove (HLA a1/a2) and peptide are UNRESTRAINED throughout.")
    return system


def pick_platform(force=None):
    names = [
        Platform.getPlatform(i).getName()
        for i in range(Platform.getNumPlatforms())
    ]
    log(f"available platforms: {names}")
    order = [force] if force else ["CUDA", "OpenCL", "CPU", "Reference"]
    for want in order:
        if want in names:
            plat = Platform.getPlatformByName(want)
            props = {}
            if want in ("CUDA", "OpenCL"):
                props["Precision"] = "mixed"
            if want == "CUDA":
                props["DeterministicForces"] = "false"
            log(f"using platform: {want} {props}")
            return plat, props
    raise RuntimeError("no usable OpenMM platform")


# --------------------------------------------------------------------------
# 3. Run
# --------------------------------------------------------------------------
def run(args):
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    wall0 = time.time()

    topology, positions, prepared_pdb = prepare(Path(args.cif), out_dir)
    peptide, b2m, hla = identify_chains(topology)
    system = build_system(topology, positions, peptide, b2m, hla)

    integrator = LangevinMiddleIntegrator(TEMPERATURE, FRICTION, TIMESTEP)
    integrator.setRandomNumberSeed(args.seed)
    platform, props = pick_platform(args.platform)

    t = time.time()
    sim = Simulation(topology, system, integrator, platform, props)
    sim.context.setPositions(positions)
    ctx_seconds = time.time() - t
    log(f"context created (kernel compilation): {ctx_seconds:.1f}s")

    # --- minimize, fully restrained -------------------------------------
    sim.context.setParameter("k_equil", EQUIL_K)
    sim.context.setParameter("k_scaffold", 0.0)
    t = time.time()
    sim.minimizeEnergy(
        tolerance=10 * unit.kilojoule_per_mole / unit.nanometer,
        maxIterations=500,
    )
    log(f"minimization: {time.time() - t:.1f}s")

    # --- restrained equilibration ---------------------------------------
    sim.context.setVelocitiesToTemperature(TEMPERATURE, args.seed)
    equil_steps = int((EQUIL_PS * unit.picoseconds) / TIMESTEP)
    t = time.time()
    sim.step(equil_steps)
    equil_seconds = time.time() - t
    log(f"equilibration: {EQUIL_PS} ps in {equil_seconds:.1f}s")

    # --- release the groove; keep scaffold pinned ------------------------
    sim.context.setParameter("k_equil", 0.0)
    sim.context.setParameter("k_scaffold", SCAFFOLD_K)

    # Snapshot the post-equilibration state as the RMSD reference.
    ref_state = sim.context.getState(getPositions=True)
    ref_pdb = out_dir / "reference.pdb"
    with open(ref_pdb, "w") as fh:
        PDBFile.writeFile(topology, ref_state.getPositions(), fh, keepIds=True)

    # --- calibrate: how many steps fit the remaining budget? -------------
    probe_steps = 500
    t = time.time()
    sim.step(probe_steps)
    per_step = (time.time() - t) / probe_steps
    ns_per_day = (
        TIMESTEP.value_in_unit(unit.nanoseconds) / per_step * 86400.0
    )
    log(f"measured: {per_step * 1e3:.3f} ms/step -> {ns_per_day:.0f} ns/day")

    if args.calibrate:
        log("--calibrate: stopping after timing probe.")
        json.dump(
            {
                "atoms": topology.getNumAtoms(),
                "ns_per_day": ns_per_day,
                "ms_per_step": per_step * 1e3,
                "context_seconds": ctx_seconds,
                "prep_plus_min_seconds": time.time() - wall0,
            },
            open(out_dir / "calibration.json", "w"),
            indent=2,
        )
        return

    remaining = args.budget_seconds - (time.time() - wall0) - 5.0  # 5s slack
    prod_steps = max(2000, int(remaining / per_step))
    prod_ns = prod_steps * TIMESTEP.value_in_unit(unit.nanoseconds)
    stride = max(1, prod_steps // N_FRAMES)
    log(
        f"production: {prod_steps} steps = {prod_ns:.3f} ns "
        f"in ~{remaining:.0f}s, {prod_steps // stride} frames"
    )

    sim.reporters.append(DCDReporter(str(out_dir / "traj.dcd"), stride))
    sim.reporters.append(
        StateDataReporter(
            str(out_dir / "log.csv"),
            stride,
            step=True,
            time=True,
            potentialEnergy=True,
            temperature=True,
            speed=True,
        )
    )

    t = time.time()
    sim.step(prod_steps)
    prod_seconds = time.time() - t

    final = sim.context.getState(getPositions=True)
    with open(out_dir / "final.pdb", "w") as fh:
        PDBFile.writeFile(topology, final.getPositions(), fh, keepIds=True)

    meta = {
        "cif": str(args.cif),
        "seed": args.seed,
        "atoms": topology.getNumAtoms(),
        "peptide_chain": peptide.id,
        "peptide_length": len(list(peptide.residues())),
        "hla_chain": hla.id,
        "b2m_chain": b2m.id,
        "forcefield": ["amber14-all.xml", "implicit/obc2.xml"],
        "timestep_fs": TIMESTEP.value_in_unit(unit.femtoseconds),
        "temperature_K": TEMPERATURE.value_in_unit(unit.kelvin),
        "production_ns": prod_ns,
        "ns_per_day": ns_per_day,
        "frames": prod_steps // stride,
        "seconds": {
            "context": ctx_seconds,
            "equilibration": equil_seconds,
            "production": prod_seconds,
            "total_wall": time.time() - wall0,
        },
    }
    json.dump(meta, open(out_dir / "run.json", "w"), indent=2)
    log(f"DONE  {prod_ns:.3f} ns in {meta['seconds']['total_wall']:.1f}s wall")
    log(json.dumps(meta["seconds"], indent=2))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cif", required=True, help="Boltz-2 output mmCIF")
    p.add_argument("--out", required=True, help="output directory")
    p.add_argument("--budget-seconds", type=float, default=150.0)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--platform", default=None,
                   help="force a platform: CUDA / OpenCL / CPU")
    p.add_argument("--calibrate", action="store_true",
                   help="measure ns/day and exit")
    run(p.parse_args())


if __name__ == "__main__":
    main()
```

### Known gotchas this script already handles

1. **Disulfides.** `openmm.app.PDBxFile.__init__` calls `topology.createStandardBonds()` but **not** `createDisulfideBonds()` — it only picks up disulfides from mmCIF `struct_conn` records, which Boltz-2 does not emit. PDBFixer's `addMissingAtoms()` internally calls `newTopology.createDisulfideBonds(newPositions)`, which rescues this. The script **counts SG–SG bonds and warns** if fewer than 3 (HLA α2, HLA α3, and β2m each have one). *Verified from [pdbfixer.py](https://raw.githubusercontent.com/openmm/pdbfixer/master/pdbfixer/pdbfixer.py) and [pdbxfile.py](https://raw.githubusercontent.com/openmm/openmm/master/wrappers/python/openmm/app/pdbxfile.py).*
2. **`fixer.missingResidues = {}`** — stops PDBFixer building phantom loops at chain termini.
3. **`removeHeterogens`** — one stray HETATM = `ValueError: No template found for residue`.
4. **Two independent restraint forces with global parameters** — lets you change restraints mid-run without rebuilding the `System` (which would re-trigger kernel compilation).
5. **Time-budgeted, not ns-budgeted** — the script measures actual throughput and picks the step count. This is what makes it demo-safe: it *always* finishes in your budget, on whatever hardware.

---

## 5. What to measure and display

### 5.1 Does MDTraj install on ARM64?

**Yes.** `mdtraj-1.11.1-cp312-cp312-manylinux_2_24_aarch64.manylinux_2_28_aarch64.whl` exists on PyPI ([pypi.org/pypi/mdtraj/json](https://pypi.org/pypi/mdtraj/json)). ⚠️ MDAnalysis aarch64/cp312 wheel status could not be confirmed from the PyPI JSON API. **Use MDTraj** — it covers everything below and is verified.

### 5.2 The metrics, ranked by defensibility

| Metric | Defensible? | Notes |
|---|---|---|
| **Peptide heavy-atom RMSD vs t=0** | ★★★ Best | Direct, visual, obviously interpretable. Superpose on groove Cα *only*. |
| **Contact persistence fraction** | ★★★ Best | Fraction of the t=0 peptide–HLA contacts still present at time t. Robust and honest; less noisy than RMSD. |
| **Buried SASA of the peptide** | ★★ Good | Clean "is it still in the groove" number; easy to explain. |
| **Per-residue RMSF, esp. P2/P9** | ★★ Good | Anchors are the mechanistic story. But RMSF from <1 ns is badly under-converged — report it, caveat it. |
| **H-bond counts to A/B/F pockets** | ★ Weak at this timescale | H-bonds fluctuate on ps timescales; a sub-ns average is extremely noisy. Show the *total* count trace, don't try to resolve per-pocket. |

**My recommendation for the demo:** lead with **peptide RMSD** and **contact persistence**, show **buried SASA** as a sanity plot, put RMSF-at-anchors in a secondary panel with an explicit "under-converged" label, and **drop per-pocket H-bond analysis** — it will not survive a question from an MD-literate judge.

### 5.3 ANALYSIS CODE

Save as `md_analyze.py`.

```python
#!/usr/bin/env python3
"""
md_analyze.py -- metrics for a short implicit-solvent pMHC MD run.

    python md_analyze.py --run run1/ --peptide-chain C
"""

import argparse
import json
from pathlib import Path

import mdtraj as md
import numpy as np

CONTACT_CUTOFF = 0.45   # nm; standard heavy-atom contact definition
GROOVE_LAST_RES = 181   # 0-based; HLA alpha1+alpha2


def chain_indices(top):
    """Return (peptide, hla, b2m) mdtraj chain indices, by residue count."""
    order = sorted(top.chains, key=lambda c: c.n_residues)
    return order[0].index, order[-1].index, order[1].index


def analyze(run_dir: Path, peptide_chain=None):
    top_pdb = run_dir / "reference.pdb"
    traj = md.load(str(run_dir / "traj.dcd"), top=str(top_pdb))
    ref = md.load(str(top_pdb))
    top = traj.topology
    pep_i, hla_i, b2m_i = chain_indices(top)
    if peptide_chain is not None:
        pep_i = next(c.index for c in top.chains if c.chain_id == peptide_chain)

    meta = json.load(open(run_dir / "run.json"))
    times_ns = np.arange(traj.n_frames) * (
        meta["production_ns"] / max(1, traj.n_frames)
    )

    # ---------- alignment: superpose on the GROOVE only -----------------
    # Aligning on the whole complex lets alpha3/B2M motion leak into the
    # peptide RMSD. The groove is the only relevant frame of reference.
    groove_ca = top.select(
        f"chainid {hla_i} and name CA and resid 0 to {GROOVE_LAST_RES}"
    )
    traj.superpose(ref, atom_indices=groove_ca)

    # ---------- 1. peptide heavy-atom RMSD ------------------------------
    pep_heavy = top.select(f"chainid {pep_i} and not element H")
    d = traj.xyz[:, pep_heavy, :] - ref.xyz[0, pep_heavy, :]
    rmsd_nm = np.sqrt((d ** 2).sum(axis=2).mean(axis=1))
    rmsd_A = rmsd_nm * 10.0

    # ---------- 2. contact persistence ----------------------------------
    mhc_heavy = top.select(
        f"(chainid {hla_i} or chainid {b2m_i}) and not element H"
    )
    pairs = np.array(np.meshgrid(pep_heavy, mhc_heavy)).T.reshape(-1, 2)
    dists = md.compute_distances(traj, pairs, periodic=False)     # (T, P)
    ref_d = md.compute_distances(ref, pairs, periodic=False)[0]   # (P,)

    initial = ref_d < CONTACT_CUTOFF
    n_initial = int(initial.sum())
    kept = (dists[:, initial] < CONTACT_CUTOFF).sum(axis=1)
    persistence = kept / max(1, n_initial)
    n_contacts = (dists < CONTACT_CUTOFF).sum(axis=1)

    # ---------- 3. buried SASA of the peptide ---------------------------
    sasa_complex = md.shrake_rupley(traj, mode="residue")
    pep_res = [r.index for r in top.chain(pep_i).residues]
    pep_sasa_in_complex = sasa_complex[:, pep_res].sum(axis=1)

    pep_only = traj.atom_slice(top.select(f"chainid {pep_i}"))
    pep_sasa_free = md.shrake_rupley(pep_only, mode="residue").sum(axis=1)
    buried_nm2 = pep_sasa_free - pep_sasa_in_complex
    buried_frac = buried_nm2 / np.maximum(pep_sasa_free, 1e-9)

    # ---------- 4. per-residue RMSF of the peptide ----------------------
    rmsf_by_res = []
    for r in top.chain(pep_i).residues:
        idx = [a.index for a in r.atoms if a.element.symbol != "H"]
        xyz = traj.xyz[:, idx, :]
        mean = xyz.mean(axis=0)
        rmsf_by_res.append(
            float(np.sqrt(((xyz - mean) ** 2).sum(axis=2).mean()) * 10.0)
        )
    pep_seq = [r.name for r in top.chain(pep_i).residues]

    # ---------- 5. total peptide-MHC hydrogen bonds ---------------------
    # baker_hubbard averages over the trajectory (freq=0.1 => present >=10%).
    try:
        hb = md.baker_hubbard(traj, freq=0.1, periodic=False)
        pep_set, mhc_set = set(pep_heavy.tolist()), set(mhc_heavy.tolist())
        interface_hbonds = int(sum(
            1 for d_i, _, a_i in hb
            if (d_i in pep_set and a_i in mhc_set)
            or (d_i in mhc_set and a_i in pep_set)
        ))
    except Exception as exc:                      # noqa: BLE001
        interface_hbonds = None
        print(f"[warn] hbond analysis failed: {exc}")

    # ---------- composite, deliberately simple --------------------------
    tail = slice(max(0, traj.n_frames - traj.n_frames // 4), None)
    result = {
        "production_ns": meta["production_ns"],
        "n_frames": int(traj.n_frames),
        "peptide_sequence": pep_seq,
        "rmsd_A": {
            "series": [round(float(v), 3) for v in rmsd_A],
            "final": round(float(rmsd_A[-1]), 3),
            "mean_last_quarter": round(float(rmsd_A[tail].mean()), 3),
            "max": round(float(rmsd_A.max()), 3),
        },
        "contacts": {
            "n_initial": n_initial,
            "series": [int(v) for v in n_contacts],
            "persistence_series": [round(float(v), 4) for v in persistence],
            "persistence_mean_last_quarter": round(
                float(persistence[tail].mean()), 4
            ),
        },
        "buried_sasa": {
            "nm2_series": [round(float(v), 3) for v in buried_nm2],
            "fraction_mean_last_quarter": round(
                float(buried_frac[tail].mean()), 4
            ),
        },
        "peptide_rmsf_A": dict(zip(
            [f"P{i + 1}:{n}" for i, n in enumerate(pep_seq)],
            [round(v, 3) for v in rmsf_by_res],
        )),
        "interface_hbonds_persistent": interface_hbonds,
        "CAVEAT": (
            f"{meta['production_ns']:.2f} ns implicit-solvent MD of a "
            "PREDICTED structure. This is a structural plausibility check, "
            "NOT a measurement or prediction of binding affinity, complex "
            "half-life, or immunogenicity."
        ),
    }

    out = run_dir / "metrics.json"
    json.dump(result, open(out, "w"), indent=2)

    print(f"peptide RMSD (final)          : {result['rmsd_A']['final']:.2f} A")
    print(f"contact persistence (last 25%): "
          f"{result['contacts']['persistence_mean_last_quarter']:.1%}")
    print(f"buried fraction (last 25%)    : "
          f"{result['buried_sasa']['fraction_mean_last_quarter']:.1%}")
    print(f"anchor RMSF P2 / P9           : "
          f"{rmsf_by_res[1]:.2f} / {rmsf_by_res[-1]:.2f} A")
    print(f"-> {out}")
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--peptide-chain", default=None)
    args = p.parse_args()
    analyze(Path(args.run), args.peptide_chain)
```

### 5.4 How to display it

Three panels, one sentence each:

1. **Peptide RMSD vs time**, with a horizontal band at 2 Å ("stayed put") and 4 Å ("moved"). Overlay all candidates.
2. **Contact persistence vs time**, 0–100%. This is your money plot — it is monotone-ish, intuitive, and does not require the viewer to know what RMSD means.
3. **Anchor RMSF bar chart** (P1…P9), P2 and P9 highlighted. Label it *"under-converged at this timescale"*.

Plus a one-line verdict per candidate: `"held groove: contact persistence 91%, peptide RMSD 1.4 Å over 0.8 ns"`.

---

## 6. Timing and feasibility verdict

### 6.1 The anchor benchmarks

| Source | System | GPU | Settings | ns/day |
|---|---|---|---|---|
| [openmm#3695](https://github.com/openmm/openmm/issues/3695) | **9,266 atoms, GBn2 implicit** | A4000 | 2 fs, HBonds | **54** |
| [openmm#3695](https://github.com/openmm/openmm/issues/3695) | 2,489 atoms, `gbsa` benchmark | A4000 | 4 fs, single | 1,977 |
| [openmm#4854](https://github.com/openmm/openmm/issues/4854) | 2,489 atoms, `gbsa` benchmark | **RTX 5090 (sm_120)** | 4 fs, HMR 1.5, single, OpenMM 8.2, CUDA 12.8 | **3,599** |
| [openmm#4854](https://github.com/openmm/openmm/issues/4854) | `pme` (explicit) | RTX 5090 | 4 fs | 2,258 |
| [openmm#4854](https://github.com/openmm/openmm/issues/4854) | `apoa1pme`, 92,224 atoms explicit | RTX 5090 | 4 fs | 1,060 |
| [openmm#4854](https://github.com/openmm/openmm/issues/4854) | `amber20-stmv`, ~1.07M atoms | RTX 5090 | 4 fs | 103 |

The A4000 pair is the load-bearing datum: **36× slowdown for 3.7× the atoms**, which is the O(N²) signature of `NoCutoff` GB, compounded by GBn2's extra neck pass.

### 6.2 GB10 vs the proxies

⚠️ **No OpenMM, GROMACS, NAMD or any MD benchmark exists for GB10 / DGX Spark that I could find.** Everything below is extrapolation, clearly labelled.

| | GB10 (DGX Spark) | RTX 5090 | A4000 |
|---|---|---|---|
| FP32 | **31 TFLOPS** | ~105 TFLOPS | ~19 TFLOPS |
| Memory BW | **273 GB/s** | 1,792 GB/s | 448 GB/s |
| TDP | 180 W | 575 W | 140 W |

Sources: [Flopper GB10](https://flopper.io/gpu/nvidia-gb10-grace-blackwell), [Flopper RTX 5090](https://flopper.io/gpu/nvidia-geforce-rtx-5090-32gb).

For a ~6,000-atom system, OpenMM is **compute- and kernel-launch-bound, not bandwidth-bound** (the whole system fits in cache several times over). So the FP32 ratio (~3.4× vs 5090, ~1.6× *faster* than A4000 on paper) is the better guide than the bandwidth ratio (6.6×). Call GB10 ≈ **A4000-class to 1.5× A4000** for this workload. ⚠️ Blackwell's per-SM improvements and the ARM host's launch latency both cut in unknown directions.

### 6.3 Projection for YOUR system (~6,000 atoms)

Scaling the A4000 GBn2 datum (9,266 atoms → 54 ns/day at 2 fs, `NoCutoff`):

| Change | Multiplier | Running ns/day (A4000-class) |
|---|---|---|
| Baseline 9,266 atoms, GBn2, NoCutoff, 2 fs | — | 54 |
| → 6,000 atoms, O(N²) | ×2.4 | 130 |
| → 4 fs with HMR | ×2.0 | 260 |
| → OBC2 instead of GBn2 (no neck pass) | ×1.3–1.8 | 340–470 |
| → **`CutoffNonPeriodic` 1.8 nm (O(N²)→O(N))** | ×1.5–3 | **500–1,400** |
| → GB10 vs A4000 | ×1.0–1.5 | **500–2,000** |

**Estimate: 400–1,500 ns/day. Treat the low end as the planning number.**

| Wall clock | ns at 400 ns/day | ns at 1,000 ns/day |
|---|---|---|
| 60 s | 0.28 | 0.69 |
| 120 s | 0.56 | 1.39 |
| 180 s | 0.83 | 2.08 |

**Plus fixed overhead you must subtract from that budget:**

| Stage | Estimate |
|---|---|
| PDBFixer prep (CIF → protonated PDB) | 3–10 s |
| `createSystem` + **NVRTC kernel compilation** | ⚠️ **10–40 s** — measure it, ARM host, first context in a process |
| Minimization (500 steps) | 3–10 s |
| 10 ps restrained equilibration | 2–5 s |
| **Fixed total** | **~20–65 s** |

### 6.4 VERDICT

**Feasible, at 0.3–1.5 ns per candidate in a 1–3 minute wall-clock budget.** You asked for 1–3 ns; plan for **~0.5 ns** and be pleasantly surprised.

**Three things that make this actually work in a demo:**

1. **Amortize kernel compilation.** Run all N candidates in **one Python process**. The 10–40 s NVRTC cost is paid once, not N times. If every candidate has the same topology size the `System` still needs rebuilding, but the compiled kernel cache within the CUDA context is reused. This alone can halve your per-candidate cost.
2. **Time-budget, don't ns-budget.** The script above measures throughput and picks the step count. It cannot overrun. Never demo an MD run whose duration you haven't bounded.
3. **Run it ahead and cache.** Nothing forces a *live* MD run. Pre-compute results for the demo candidates, cache the JSON, and run *one* live for theatre. This is normal and honest as long as you say so.

### 6.5 First thing to do on the machine

```bash
source "$HOME/.venvs/md/bin/activate"
python -m openmm.testInstallation      # 1. does the CUDA platform exist?
python md_stress.py --cif your_boltz_output.cif --out /tmp/cal --calibrate
```

That last command prints your **actual ns/day** in under a minute and settles every estimate in this section. **Do it before you write any UI.**

---

## 7. Why explicit solvent is out (for completeness)

At ~65,000 atoms with PME, extrapolating `apoa1pme` (92,224 atoms → 1,060 ns/day on RTX 5090) gives ~1,500 ns/day on a 5090 and maybe **300–450 ns/day on GB10** — i.e. *comparable to or better than* the implicit-solvent estimate, because PME is O(N log N) with a neighbour list while `NoCutoff` GB is O(N²).

**That is a genuinely counter-intuitive result and worth knowing.** Explicit solvent loses anyway, on *wall clock, not throughput*:

- box construction + neutralization: 5–20 s
- minimization of 65k atoms: 20–40 s
- NVT heating: ~50 ps
- **NPT density equilibration: 100–500 ps, non-negotiable** — this alone is 30–150 s
- and only then does usable production start

With a 180-second ceiling, explicit solvent spends the whole budget getting the water to stop sloshing. **Implicit wins on total time-to-signal, not on ns/day.** If your budget were 20 minutes per candidate, explicit TIP3P would be the better science.

---

## 8. SCIENTIFIC HONESTY

This is the section that will decide whether an MD-literate judge respects the project or dismisses it. Read it before you write a single slide.

### 8.1 Does short MD of pMHC correlate with immunogenicity or affinity?

**Short answer: the published correlations are real but modest, and every single one of them uses simulations 100–3,000× longer than yours.**

**What the literature actually shows:**

**(a) The largest and most relevant study — and its sobering result.**
[*Unsupervised and supervised AI on molecular dynamics simulations reveals complex characteristics of HLA-A2-peptide immunogenicity*, Briefings in Bioinformatics 25(1), bbad504 (2024)](https://academic.oup.com/bib/article/25/1/bbad504/7560312):
- **2,883 HLA-A2-restricted 9-mers** (1,038 immunogenic / 1,845 non-immunogenic binders)
- **200 ns per system, explicit TIP3P, CHARMM36m, 310 K, 1 atm**
- **The first 30 ns of every trajectory was discarded as equilibration** — that discarded portion alone is ~30–100× your entire production run
- Features: SASA, peptide RMSD, P2/P9 anchor dynamics, backbone/sidechain flexibility — **essentially the metrics in §5**
- Result: MD-graph model **AUC 0.81**; sequence-only baseline **AUC 0.80**.

**200 ns × 2,883 systems bought +0.01 AUC over reading the sequence.** That is the honest headline. (MD did help more in the low-data regime: AUC 0.69 vs 0.61 on 100-peptide subsets — an 8-point gain. Worth knowing, but it is not a claim about a single 0.5 ns run.)

**(b) The peptide-flexibility work.**
[Ayres et al., *Modeling Sequence Dependent Peptide Fluctuations in Immunologic Recognition*, PMC5573614](https://pmc.ncbi.nlm.nih.gov/articles/PMC5573614/):
- **1 µs per simulation**, SPC/E explicit water, ff14SB, 81 usable HLA-A*0201 systems
- Metric: Cα RMSF after global superposition — again, §5's metric
- **The authors did not directly correlate their fluctuations with immunogenicity data.** They validated against NMR/crystallography and *cited prior work* linking peptide rigidity to immunogenicity.
- Their own caveat: low-frequency motions associated with TCR binding "require lengthier simulations" than even 1 µs.

**(c) MD-derived binding affinity.**
[Wan, Coveney et al., *Rapid, Precise, and Reproducible Prediction of Peptide–MHC Binding Affinities from Molecular Dynamics*, JCTC 11 (2015)](https://pubs.acs.org/doi/10.1021/acs.jctc.5b00179) reports good agreement with experiment — but via **ESMACS/MM-PBSA over ensembles of replicas**, not a single short trajectory. ⚠️ Full text paywalled (403); I could not extract the exact correlation coefficient. The method's defining feature is *ensemble averaging over many replicas* precisely because single short trajectories are irreproducible.

**(d) The one genuinely encouraging result for short MD.**
[Rognan et al. (1994), PMID 7522551](https://pubmed.ncbi.nlm.nih.gov/7522551/) found that experimentally-validated binders "remained tightly anchored to the MHC molecule, whereas nonbinders were significantly more weakly complexed and progressively dissociated at their N- and C-terminal ends." **This is exactly your signal.** Caveats: 1994, tiny peptide set, crystal-structure starting points (not predictions), and it distinguishes *binders from non-binders* — a far cruder question than ranking binders by stability.

**Conclusion: the correlation between short MD and immunogenicity is WEAK. The correlation between *sub-nanosecond* MD of a *predicted* structure and immunogenicity is UNDEMONSTRATED.** No paper I found attempts it, because no one thinks it would work.

### 8.2 The strongest TRUE claim you can make

> **"We run a short GPU molecular-dynamics stress test on each predicted complex as a structural plausibility filter. It catches cases where the predicted peptide pose is not a physically stable minimum under an AMBER force field — the peptide drifts out of the groove within picoseconds. It is a fast, local sanity check on the prediction's geometry, and it runs in 90 seconds on this box."**

Every word of that is defensible. It says: *physics disagrees with this pose*, which is a real and useful thing to detect. Predicted structures genuinely can have clashes, wrong rotamers, or anchors placed in the wrong pocket, and a force field will reject those fast.

**Strong secondary framing:**
> "It's a negative filter, not a positive score. A candidate that falls apart in 0.5 ns is almost certainly a bad prediction. A candidate that holds is *not* thereby shown to be a good epitope — it has merely failed to fail."

That asymmetry is the honest core of the whole feature, and stating it unprompted will earn you more credit than any plot.

### 8.3 What would be OVERCLAIMING

Do not say any of these:

| ❌ Overclaim | Why it's wrong |
|---|---|
| "MD predicts peptide-MHC binding affinity" | Requires MM-PBSA over replica ensembles ([JCTC 2015](https://pubs.acs.org/doi/10.1021/acs.jctc.5b00179)), not one 0.5 ns trajectory. |
| "MD predicts complex stability / half-life" | Experimental pMHC half-lives are **hours** ([Harndahl 2012](https://onlinelibrary.wiley.com/doi/full/10.1002/eji.201141774)). You are sampling 10⁻¹³ of that. Genuine dissociation is unreachable by ~10 orders of magnitude. |
| "MD predicts immunogenicity" | 200 ns × 2,883 peptides gave +0.01 AUC over sequence alone ([bbad504](https://academic.oup.com/bib/article/25/1/bbad504/7560312)). |
| "MD validates the Boltz-2 prediction" | MD started *from* that structure and restrained part of it. It cannot validate its own input. Circular. |
| "RMSF shows anchor residue P2 is well-anchored" | RMSF from <1 ns is not converged. The 1 µs study needed microseconds for exactly this. |
| "Implicit-solvent dynamics are realistic" | No water viscosity → artificially accelerated dynamics, a known and well-documented GB artifact. |
| "Low RMSD means a good epitope" | Confounds prediction confidence with biology. A confidently-wrong pose can be perfectly stable. |

### 8.4 Would a NON-MD alternative be more defensible?

**Yes — and you should build one regardless, because it doubles as your OpenMM fallback.**

#### Option A: Multi-seed Boltz-2 ensemble spread ★ RECOMMENDED

Run Boltz-2 with N different seeds (or use its diffusion samples), then measure **peptide pose agreement across the ensemble**: pairwise peptide heavy-atom RMSD after superposing on the groove — i.e. reuse `md_analyze.py`'s alignment logic verbatim.

| | Ensemble spread | 0.5 ns implicit MD |
|---|---|---|
| Uses hardware you've already proven | ✅ | ⚠️ sm_121 unproven for OpenMM |
| New dependencies | **none** | openmm + pdbfixer + mdtraj |
| Measures something real | ✅ model uncertainty | ✅ local force-field stability |
| Circular? | No — independent samples | Somewhat — MD starts from the pose |
| Literature support | ✅ ensemble spread is the standard uncertainty proxy for structure predictors; Boltz-2 also emits confidence/ipTM directly | ⚠️ Weak at this timescale |
| Honest claim | "the model is (un)certain about this pose" | "physics doesn't immediately reject this pose" |
| Cost | ~N× your existing inference | 1–3 min/candidate + 2 days of integration risk |

**Ensemble spread is the more defensible metric and the cheaper one.** Its weakness is that it measures *the model's* uncertainty, not physics — a confidently-wrong model looks confident. That weakness is exactly what MD complements.

#### Option B: NetMHCstabpan 1.0

The established empirical pMHC-I stability predictor: a neural network trained on **>25,000 quantitative stability measurements across 75 HLA molecules** ([DTU NetMHCstabpan-1.0](https://services.healthtech.dtu.dk/services/NetMHCstabpan-1.0/); [Rasmussen et al. 2016, PMID 27402703](https://pubmed.ncbi.nlm.nih.gov/27402703/)). Its predecessor NetMHCstab was trained on 5,509 stability measurements over 10 HLAs ([PMC3893846](https://pmc.ncbi.nlm.nih.gov/articles/PMC3893846/)), and combining predicted stability with predicted affinity measurably improves T-cell-epitope identification.

The underlying biology is solid: [Harndahl et al. 2012, *Eur J Immunol* 42:1405–1416](https://onlinelibrary.wiley.com/doi/full/10.1002/eji.201141774) showed pMHC-I stability beats affinity as a correlate of CTL immunogenicity — 30% of non-immunogenic vaccinia peptides had half-lives < 1 h, while **all** immunogenic peptides had longer half-lives.

**But three blockers for this specific demo:**
1. ⚠️ **Architecture.** DTU ships NetMHCstabpan as **pre-compiled Linux x86_64 binaries**. On aarch64 it will not run natively. You'd need qemu-user or box64 — ⚠️ *unverified*, and not a Friday-night project. **This is likely disqualifying.**
2. **Licensing.** Academic download form, non-commercial only, email-gated. Requires a request *now* if at all.
3. **It's sequence-based.** It ignores your structure entirely, so it doesn't showcase Boltz-2 — it competes with it.

**Verdict on B:** the right tool scientifically, wrong tool for this machine and this demo. If you have time, mention it in the talk as "the established baseline we'd validate against" — that shows you know the field, which is worth more than running it.

#### My recommendation

**Ship both, framed as orthogonal checks:**

1. **Boltz-2 multi-seed ensemble spread** → *"how sure is the model about this pose?"* (cheap, zero new risk, defensible)
2. **Short OpenMM stress test** → *"does a physics force field immediately reject this pose?"* (the cool demo, honestly framed as a negative filter)

Two independent axes, neither overclaimed, and the second degrades gracefully to nothing if OpenMM fails on sm_121. Put the honesty caveat **on the slide**, not in the Q&A. Judges reward pre-emptive honesty far more than they punish a modest claim.

### 8.5 Five hard questions from an MD-background judge

---

**Q1. "You ran 0.5 nanoseconds. pMHC complexes have half-lives of hours. What do you think you measured?"**

*Honest answer:* "Nothing about the half-life — we're ~10 orders of magnitude short of the dissociation timescale, and we know it. What we measured is whether the predicted pose sits in a local minimum of an AMBER force field. If a peptide is sliding out of the groove within 500 picoseconds, that's not slow dissociation, that's the prediction having put atoms somewhere the force field considers untenable. It's a geometry check, not a kinetics measurement. We use it as a negative filter only."

---

**Q2. "Implicit solvent with a 1.8 nm cutoff on a Generalized Born model — you've removed water viscosity and truncated the Born radii. Why should I believe anything about the dynamics?"**

*Honest answer:* "You shouldn't believe the *dynamics*. GB with no explicit water gives artificially accelerated conformational sampling because there's no solvent friction, and the cutoff introduces Born-radius error at the boundary. We chose it because the alternative — explicit TIP3P — needs 100–500 ps of NPT density equilibration before production, which is more than our entire budget. What survives those approximations is the coarse question: does the peptide stay in contact with the groove, or does it leave? Contact persistence is much more robust to these approximations than any energetic quantity would be. We don't report MM-GBSA binding energies precisely because those *would* be sensitive to all of this."

---

**Q3. "You restrained part of the complex. Doesn't that rig the result toward stability?"**

*Honest answer:* "We restrain Cα atoms of β2-microglobulin and the HLA α3 domain at 1 kcal/mol/Å². Those are more than 20 Å from the peptide. The α1/α2 groove — everything the peptide actually touches — and the peptide itself are completely free. The restraint removes global tumbling and inter-domain hinging that would otherwise contaminate the peptide RMSD, and it costs us nothing we care about. If you want, we can rerun with no restraints; the peptide RMSD gets noisier, but the contact-persistence metric is unaffected because it's a distance-based quantity that doesn't need alignment at all. That's partly why contact persistence is our headline metric and RMSD is secondary."

---

**Q4. "MD starting from a predicted structure — isn't this circular? You're validating the prediction using the prediction."**

*Honest answer:* "Partly, and it's the sharpest criticism of the approach. MD cannot tell you whether the model docked the peptide into the right pockets — if it put P2 in the wrong pocket confidently, the physics will happily keep it there. What MD *can* catch is a different failure mode: locally implausible geometry — clashes, strained rotamers, a pose that's a saddle point rather than a minimum. Those are real and common in predicted structures, and they're invisible to the predictor's own confidence score. So it's an orthogonal check on a *subset* of errors, not a validation. That's exactly why we also report multi-seed ensemble spread, which asks a different question — how reproducible is the pose across independent samples — and doesn't share the circularity."

---

**Q5. "What's your evidence this metric correlates with anything measurable? Show me the validation."**

*Honest answer:* "We have none, and I want to be direct about that rather than gesture at literature. The largest relevant study — 2,883 HLA-A2 peptides, 200 nanoseconds each in explicit solvent — got AUC 0.81 from MD-derived features versus 0.80 for sequence alone. A hundredth of an AUC point, from simulations four hundred times longer than ours. The microsecond-scale peptide-flexibility work didn't even attempt a direct immunogenicity correlation. So the honest position is: this is a structural plausibility filter that we have not validated against any experimental endpoint, and we're presenting it as a physics sanity check rather than a predictor. The validation we'd want is straightforward — take a set with measured NetMHCstabpan-style half-lives or MHC multimer data, run the same pipeline, and see whether contact persistence separates anything. That's the next experiment, not a result we're claiming today."

---

**A note on delivering these:** volunteer Q5's limitation *before* anyone asks. "Here's a thing we built, here's exactly what it can and can't tell you, here's the experiment that would validate it" is a much stronger position than defending an inflated claim. MD people have seen a lot of overclaimed short simulations; being the team that doesn't do that is genuinely memorable.

---

## 9. Concrete plan for the next 48 hours

| When | Do | Kill criterion |
|---|---|---|
| **Wed AM** | `pip install openmm[cuda13]` in a fresh venv; `python -m openmm.testInstallation` | If CUDA platform missing → try `cuda12`, then OpenCL. |
| **Wed AM** | `md_stress.py --calibrate` on a real Boltz-2 CIF | **If ns/day < 150, MD is dead — go to §8.4 Option A.** |
| **Wed PM** | `pip download` everything into `$HOME/wheelhouse`; test offline reinstall | — |
| **Wed PM** | Build Boltz multi-seed ensemble-spread metric (the fallback that ships either way) | — |
| **Thu AM** | Full pipeline on 3–5 candidates; tune `--budget-seconds` | — |
| **Thu noon** | **GO/NO-GO on MD.** | If not producing clean plots by now, cut it. |
| **Thu PM** | Pre-compute + cache results for demo candidates | — |
| **Fri** | UI, plots, slide with the honesty caveat **on it** | — |
| **Fri PM** | Full offline dry run with the network cable out | — |

---

## 10. Sources

**Install / platform (all verified 2026-09-23)**
- [pypi.org/pypi/openmm/8.6.1/json](https://pypi.org/pypi/openmm/8.6.1/json) — aarch64 cp312 wheel confirmed
- [pypi.org/pypi/openmm-cuda-13/json](https://pypi.org/pypi/openmm-cuda-13/json) — aarch64 CUDA 13 plugin + dep list
- [pypi.org/pypi/nvidia-cuda-nvrtc/json](https://pypi.org/pypi/nvidia-cuda-nvrtc/json) — aarch64 NVRTC 13.0.48 / 13.0.88 / 13.4.92
- [pypi.org/pypi/pdbfixer/json](https://pypi.org/pypi/pdbfixer/json) — 1.12.0, sdist-only, pure Python
- [pypi.org/pypi/mdtraj/json](https://pypi.org/pypi/mdtraj/json) — aarch64 cp312 wheel confirmed
- [github.com/openmm/openmm-wheels](https://github.com/openmm/openmm-wheels)
- [OpenMM Getting Started](https://docs.openmm.org/latest/userguide/application/01_getting_started.html)
- [anaconda.org/conda-forge/openmm](https://anaconda.org/conda-forge/openmm)

**Blackwell / sm_121**
- [openmm#4854 — RTX 5090 (sm_120) benchmarks](https://github.com/openmm/openmm/issues/4854)
- [openmm#4105 — nvcc vs NVRTC](https://github.com/openmm/openmm/issues/4105)
- [openmm#3474 — CUDA_ERROR_INVALID_PTX](https://github.com/openmm/openmm/issues/3474)
- [OpenMM Dev Guide — CUDA Platform](https://docs.openmm.org/8.0.0/developerguide/07_cuda_platform.html)
- [vLLM #36821 — no sm_121 on aarch64 DGX Spark](https://github.com/vllm-project/vllm/issues/36821)
- [CUTLASS #2947 — sm_121 arch-conditional instructions](https://github.com/NVIDIA/cutlass/issues/2947)
- [Flopper — GB10 specs](https://flopper.io/gpu/nvidia-gb10-grace-blackwell) · [RTX 5090 specs](https://flopper.io/gpu/nvidia-geforce-rtx-5090-32gb)

**Protocol / API**
- [OpenMM Running Simulations (implicit solvent, HMR, cutoffs)](https://docs.openmm.org/latest/userguide/application/02_running_sims.html)
- [OpenMM Platform-Specific Properties](https://docs.openmm.org/latest/userguide/library/04_platform_specifics.html)
- [pdbfixer.py source](https://raw.githubusercontent.com/openmm/pdbfixer/master/pdbfixer/pdbfixer.py)
- [openmm/app/pdbxfile.py source](https://raw.githubusercontent.com/openmm/openmm/master/wrappers/python/openmm/app/pdbxfile.py)
- [openmm/app/topology.py source](https://raw.githubusercontent.com/openmm/openmm/master/wrappers/python/openmm/app/topology.py)
- [openmm#3695 — 9,266-atom GBn2 at 54 ns/day on A4000](https://github.com/openmm/openmm/issues/3695)

**Science**
- [Briefings in Bioinformatics 25(1) bbad504 — 2,883 peptides, 200 ns each, AUC 0.81 vs 0.80](https://academic.oup.com/bib/article/25/1/bbad504/7560312)
- [PMC5573614 — Ayres et al., 1 µs pMHC fluctuation modeling](https://pmc.ncbi.nlm.nih.gov/articles/PMC5573614/)
- [JCTC 11 (2015) — Wan/Coveney ESMACS pMHC affinity](https://pubs.acs.org/doi/10.1021/acs.jctc.5b00179) ⚠️ paywalled, correlation not extracted
- [Harndahl et al. 2012, Eur J Immunol — stability > affinity for CTL immunogenicity](https://onlinelibrary.wiley.com/doi/full/10.1002/eji.201141774)
- [Rasmussen et al. 2016 — NetMHCstabpan, PMID 27402703](https://pubmed.ncbi.nlm.nih.gov/27402703/)
- [PMC3893846 — NetMHCstab](https://pmc.ncbi.nlm.nih.gov/articles/PMC3893846/)
- [DTU NetMHCstabpan-1.0](https://services.healthtech.dtu.dk/services/NetMHCstabpan-1.0/)
- [Rognan et al. 1994, PMID 7522551 — MD discriminates pMHC binders from non-binders](https://pubmed.ncbi.nlm.nih.gov/7522551/)

**⚠️ Explicitly unverified in this document:**
OpenMM on sm_121 specifically (no report exists — sm_120 is the closest evidence) · OpenCL platform presence in the aarch64 wheel · conda-forge `openmm` CUDA-13 aarch64 build availability · any MD benchmark on GB10/DGX Spark · NVRTC kernel-compilation wall time on an ARM host · OBC2-vs-GBn2 speed ratio · MDAnalysis aarch64 cp312 wheels · NetMHCstabpan aarch64 executability · `OPENMM_CACHE_DIR` (not found in docs; assume no cross-process kernel cache)
