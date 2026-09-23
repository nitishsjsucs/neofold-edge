# Boltz-2 on HP ZGX Nano (NVIDIA GB10 / sm_121, ARM64, CUDA 13.0) — offline-capable install guide

Researched 2026-09-22. Target: `zgx-81a8`, Ubuntu 24.04.5, aarch64, GB10 sm_121a, driver 580.173.02,
CUDA 13.0 toolkit at `/usr/local/cuda`, Python 3.12.3, 121 GB unified memory, 20 cores, docker available.

Everything marked **[community]** is a community report, not vendor-supported.
Everything marked **[inference]** is my reasoning from primary sources, not a measured result.

---

## 0. Executive summary — the single most important finding

**You almost certainly do NOT need a custom-built PyTorch wheel, and you do NOT need the community
GB10 fork.** The three things that broke Boltz-2 on GB10 in Dec 2025 – Mar 2026 have all been fixed
upstream since:

| Original blocker (Jan–Mar 2026) | Status as of Sept 2026 |
|---|---|
| `ptxas fatal: Value 'sm_121a' is not defined` from Triton | Fixed. Triton ≥ 3.6 ships a separate Blackwell ptxas; Triton 3.8.0 (pinned by torch 2.14) ships ptxas **13.3.33**. |
| `cuequivariance_ops_torch` had no CUDA-13 / sm_121 build | Fixed. `cuequivariance-ops-torch-cu13` has **linux aarch64 cp312 wheels from 0.8.0 onward**, and explicit sm_121 PTX handling landed after 0.9.0. |
| PyTorch wheels "don't have sm_121 kernels" | Not actually a blocker. PyTorch's own compatibility table declares **sm_120 code compatible with any device ≥ cc 12.0, including 12.1**. |

Proof for the last point, from `torch/cuda/__init__.py` on `main`
([source](https://github.com/pytorch/pytorch/blob/main/torch/cuda/__init__.py)):

```python
DEVICE_REQUIREMENT: dict[int, _CompatSet | _CompatInterval] = {
    ...
    120: _CompatInterval(start=120),
    121: _CompatInterval(start=121),
}
```

`120: _CompatInterval(start=120)` means *code compiled for sm_120 runs on devices with cc ≥ 120*,
which includes your sm_121. This matches PyTorch maintainer ptrblck on the forums: *"SM_121 is binary
compatible with SM_120"* and *"You won't see any performance benefits when building for sm_121
instead of sm_120"*
([discuss.pytorch.org/t/223744](https://discuss.pytorch.org/t/dgx-spark-gb10-cuda-13-0-python-3-12-sm-121/223744)).

And the arch list the official aarch64 CUDA-13 wheels are actually built with, from
[`.ci/wheel/linux/build_env_setup.py`](https://github.com/pytorch/pytorch/blob/main/.ci/wheel/linux/build_env_setup.py):

```python
TORCH_CUDA_ARCH_LIST_TABLE = {
    "13.0": {"x86_64": {75,80,86,90,100,120}, "aarch64": {80, 90, 100, 110, 120}},
    "13.2": {...same...},
    "13.4": {...same...},
}
_PTX_ARCHES: set[int] = {120}   # PTX emitted on nightly/dev builds only; release wheels are SASS-only
```

So: official `+cu130` aarch64 wheels contain **sm_120 SASS**, which loads directly on GB10 — no PTX
JIT, no hang. The historical hang was Triton's ptxas, not torch.

**Verify this on the box in 60 seconds before doing anything else** (step 4 below). If
`torch.cuda.get_arch_list()` contains `sm_120` and a bf16 matmul runs, you are done with the hard part.

---

## 1. Recommended install path (Path A — native venv, no container, no fork)

Run as your normal user on `zgx-81a8`. Steps 1–9 need internet; step 10 onward is fully offline.

```bash
# ---------- 1. system prerequisites ----------
# gemmi==0.6.5 (a hard Boltz pin) has NO linux-aarch64 wheel on PyPI, so it compiles from source.
sudo apt-get update
sudo apt-get install -y build-essential cmake python3.12-dev git

# ---------- 2. put nvcc/ptxas on PATH (you reported nvcc present but not on PATH) ----------
echo 'export PATH=/usr/local/cuda/bin:$PATH' >> ~/.bashrc
export PATH=/usr/local/cuda/bin:$PATH
nvcc --version            # expect: release 13.0
ptxas --help | grep -c sm_121   # expect >=1  (CUDA 13.0 ptxas knows sm_121/sm_121a)

# ---------- 3. clean venv ----------
python3.12 -m venv ~/boltz-env
source ~/boltz-env/bin/activate
python -m pip install -U pip setuptools wheel

# ---------- 4. PyTorch: official aarch64 + CUDA 13.0 wheel (NOT the PyPI default, which is x86 cu12x) ----------
pip install torch==2.14.0 --index-url https://download.pytorch.org/whl/cu130
#   -> torch-2.14.0+cu130-cp312-cp312-manylinux_2_28_aarch64.whl
#   -> pulls triton~=3.8.0 automatically (bundles ptxas-blackwell 13.3.33 => sm_121a OK)

# ---------- 5. SMOKE TEST — stop here if this fails ----------
python - <<'PY'
import torch, triton
p = torch.cuda.get_device_properties(0)
print("torch", torch.__version__, "| cuda", torch.version.cuda, "| triton", triton.__version__)
print("device", p.name, "cc", f"sm_{p.major}{p.minor}")
print("arch_list", torch.cuda.get_arch_list())        # expect [... 'sm_120'] (sm_121 NOT required)
a = torch.randn(4096, 4096, device="cuda", dtype=torch.bfloat16)
torch.cuda.synchronize(); import time; t=time.time()
for _ in range(20): b = a @ a
torch.cuda.synchronize(); print("bf16 4k matmul ok, %.1f ms/iter" % ((time.time()-t)/20*1000))
print("mem_get_info (free,total) bytes:", torch.cuda.mem_get_info())
PY

# ---------- 6. Boltz-2 from source, WITHOUT the [cuda] extra ----------
# The upstream [cuda] extra pins cuequivariance_*_cu12, which is wrong for a CUDA 13 box.
git clone https://github.com/jwohlwend/boltz.git ~/boltz
cd ~/boltz
git log -1 --oneline            # note the commit you pinned
pip install -e .                # gemmi 0.6.5 compiles here; expect ~3-6 min on 20 cores

# ---------- 7. cuEquivariance CUDA-13 kernels (the ones Boltz actually calls) ----------
pip install "cuequivariance-torch>=0.9.1" \
            "cuequivariance-ops-torch-cu13>=0.9.1" \
            "cuequivariance-ops-cu13>=0.9.1"
pip uninstall -y cuequivariance-ops-cu12 cuequivariance-ops-torch-cu12 2>/dev/null || true
python -c "import cuequivariance_ops_torch as c; print('cuEq ops OK', c.__version__)"

# ---------- 8. runtime environment ----------
cat >> ~/boltz-env/bin/activate <<'EOF'
export PATH=/usr/local/cuda/bin:$PATH
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas   # belt-and-braces: force system CUDA 13 ptxas
export BOLTZ_CACHE=$HOME/.boltz
export CUDA_MODULE_LOADING=LAZY
EOF
source ~/boltz-env/bin/activate

# ---------- 9. PREFETCH WEIGHTS AND CCD WHILE ONLINE (~6.2 GB download) ----------
python - <<'PY'
from pathlib import Path
from boltz.main import download_boltz2
p = Path.home()/".boltz"; p.mkdir(parents=True, exist_ok=True)
download_boltz2(p)          # boltz2_conf.ckpt + boltz2_aff.ckpt + mols.tar (extracted to ~/.boltz/mols)
PY
du -sh ~/.boltz ~/.boltz/*

# ---------- 9b. PRECOMPUTE MSAs WHILE ONLINE (see section 5) ----------
boltz predict inputs/hla_a0201.yaml --out_dir msa_gen --use_msa_server \
      --recycling_steps 0 --sampling_steps 10 --diffusion_samples 1 --num_workers 0
cp msa_gen/hla_a0201/msa/*.csv ~/msa_cache/     # keep these; they are your offline MSAs

# ---------- 10. OFFLINE RUN ----------
# (point the YAML's msa: fields at ~/msa_cache/*.csv, omit --use_msa_server entirely)
boltz predict inputs/hla_a0201_offline.yaml \
  --out_dir results \
  --cache ~/.boltz \
  --num_workers 0 \
  --recycling_steps 3 \
  --sampling_steps 200 \
  --diffusion_samples 1 \
  --use_potentials \
  --output_format pdb \
  --seed 42
```

### Why `--num_workers 0`
Every GB10 report of Boltz "hanging at `Predicting: | 0/? [00:00<?, ?it/s]`" traces to the Lightning
dataloader workers, not the GPU. The community fork's headline patch is exactly this — it changes the
CLI default from 2 to 0
([diff](https://github.com/sanjyotshenoy/boltz-gb10-spark/commit/5deb18d738)). Pass it explicitly.

### If step 5 or the first real prediction still hangs
In order, try:
1. `boltz predict ... --no_kernels` — disables the cuEquivariance triangle kernels entirely and falls
   back to pure-PyTorch einsum. **This is the single most reliable "make it run" switch on an
   unsupported arch.** Slower, but numerically the same model. (Documented in `docs/prediction.md`;
   a not-yet-merged PR, [#682](https://github.com/jwohlwend/boltz/pull/682), makes this fallback
   automatic on kernel ImportError.)
2. `export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas` (already in step 8) and clear the Triton
   cache: `rm -rf ~/.triton/cache`.
3. Drop to `torch==2.13.0 --index-url https://download.pytorch.org/whl/cu130` (pins triton 3.7.1,
   ptxas-blackwell 13.1.80 — also fine).
4. Fall back to Path B (NGC container) or Path D (custom sm_121 wheel) below.

---

## 2. Ranked alternates

### Path B — NVIDIA NGC PyTorch container (strongest fallback; known-good GB10 precedent)
`nvcr.io/nvidia/pytorch:*-py3` images are **multi-arch (arm64 + amd64)**, verified via the NGC
images API. Recent tags:

| Tag | Arch | Contents | Pushed |
|---|---|---|---|
| `26.08-py3` | arm64 + amd64 | torch `2.14.0a0+4fdf77b940`, CUDA 13.4.1, Python 3.12, Ubuntu 24.04 ([release notes](https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-26-08.html)) | 2026-08-28 |
| `26.01-py3` | arm64 + amd64 | — | 2026-01-29 |
| `25.11-py3` | arm64 + amd64 | torch 2.10.0a0, CUDA 13.0.88, Triton 3.5.0 — **the image the OpenFold3-on-Spark project uses successfully** **[community]** | 2025-11-26 |

```bash
docker pull nvcr.io/nvidia/pytorch:26.08-py3        # ~12 GB
docker run --rm -it --gpus all --ipc=host --shm-size=32g \
  -v $HOME/.boltz:/root/.boltz -v $PWD:/work -w /work \
  -e BOLTZ_CACHE=/root/.boltz \
  nvcr.io/nvidia/pytorch:26.08-py3 bash
# inside:
pip install --no-deps -e /work/boltz            # do NOT let pip replace the container's torch
pip install hydra-core==1.3.2 pytorch-lightning==2.5.0 rdkit dm-tree==0.1.8 \
    einops einx fairscale mashumaro modelcif wandb click pyyaml biopython \
    numba gemmi==0.6.5 scikit-learn chembl_structure_pipeline "numpy<2.0"
pip install "cuequivariance-torch>=0.9.1" "cuequivariance-ops-torch-cu13>=0.9.1"
```
Caveat: the container's torch is a `2.14.0a0` pre-release and Boltz's `pyproject.toml` requires
`torch>=2.2`, so `pip install -e .` (without `--no-deps`) will happily *replace* it with a PyPI
x86-ish/cu12 wheel. Always use `--no-deps` for the Boltz install inside NGC and add deps manually.
NGC's Triton is built against the container CUDA, so its ptxas knows `sm_121a` even at Triton 3.5.

Then `docker save` the image to disk for the offline demo.

### Path C — the community GB10 fork, `sanjyotshenoy/boltz-gb10-spark` (read it, don't run it)
Full assessment (I read the repo, its `install.sh`, and its full diff against upstream):

* **Created 2026-01-01, last pushed 2026-01-01T02:33Z. 3 stars. Not touched since.**
* Forked from upstream commit `cb04aecc` (2025-09-08) = **Boltz v2.2.1**. Upstream has *not* cut a
  release since v2.2.1, but has merged 5 commits in 2026 that the fork lacks — notably
  `83bb04c4 fix: disable autocast using active device type in boltz2 (#653, #662)` and
  `98bd07f9 Allocate tensors directly on target device`. So: **current with the last upstream
  release, ~5 commits behind upstream `main`.**
* What it actually patches (the whole diff is 4 files):
  1. `src/boltz/main.py`: `--num_workers` default `2 → 0`. **Real fix, keep it.**
  2. `src/boltz/main.py`: adds `--matmul_precision` (default `medium`) and calls
     `torch.set_float32_matmul_precision(...)` before `trainer.predict()`. Cosmetic + small speedup.
  3. `pyproject.toml`: `cuda` extra `cuequivariance_ops_*_cu12>=0.5.0` → `*_cu13>=0.8.0`;
     `torch>=2.2 → >=2.9`; `requires-python >=3.12,<3.13`; lightning `2.5.0 → 2.5.0.post0`.
  4. `install.sh` (45 lines): torch from `whl/cu130`, `pip install -e .[cuda]`, then
     **uninstall triton and reinstall from the Azure DevOps Triton-Nightly feed**
     (`https://aiinfra.pkgs.visualstudio.com/PublicPackages/_packaging/Triton-Nightly/pypi/simple/`),
     then purge cu12 cuEq packages and force cu13.
* **Why I do not recommend running it as-is:** the Azure Triton-Nightly feed is a moving, unpinned,
  non-archival index — bad for a reproducible offline demo, and completely unnecessary now that
  Triton 3.6/3.7/3.8 are on PyPI with aarch64 wheels. Its `cuequivariance-*-cu13>=0.8.0` floor also
  predates the sm_121 PTX fix (cuEquivariance
  [PR #250](https://github.com/NVIDIA/cuEquivariance/pull/250), *"Restrict PTX 88 to sm_121 for
  CUDA 12.9+ … ensures PTX 88 is only used for GB10/sm_121 (DGX Spark)"*), which landed after 0.9.0.
* **Take from it:** `--num_workers 0`, the cu12→cu13 cuEquivariance swap, and the confirmation that
  its author saw `ImportError: Error importing triangle_multiplicative_update from
  cuequivariance_ops_torch` and `ptxas fatal: Value 'sm_121a' is not defined`.

### Path D — custom sm_121-only PyTorch wheel (last resort)
`Qanatpharma/pytorch-sm121-gb10` on Hugging Face **[community]** — `torch-2.12.0a0+gitb071fd7-cp312-cp312-linux_aarch64.whl`,
168 MB, built `TORCH_CUDA_ARCH_LIST="12.1" USE_CUDA=1 USE_CUDNN=1 USE_NCCL=0 USE_DISTRIBUTED=0`,
~2 h build on the Spark's 20 cores.
```bash
pip install https://huggingface.co/Qanatpharma/pytorch-sm121-gb10/resolve/main/torch-2.12.0a0+gitb071fd7-cp312-cp312-linux_aarch64.whl \
  --force-reinstall --no-deps
export TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas
```
This is the fix posted by `philipptrepte` in
[jwohlwend/boltz#663](https://github.com/jwohlwend/boltz/issues/663), the only GB10 issue on the
Boltz tracker. Caveats: `torch.cuda.get_arch_list()` returns `['sm_121']` **only** — nothing else
will run on it; no NCCL/distributed; Python 3.12 only; it is a `2.12.0a0` dev build, so Lightning
2.5.0 compatibility is unverified. **Use only if Paths A and B both hang.**

### Ranked
1. **Path A** (native venv, `torch==2.14.0+cu130` aarch64, upstream Boltz, cuEq cu13) — fewest moving
   parts, everything is a pinned release artifact, fully offline-reproducible.
2. **Path B** (NGC `26.08-py3` arm64) — most likely to Just Work; heavier (12 GB), but `docker save`
   makes a bulletproof offline artifact. Use if A misbehaves, or if you want a second machine-image.
3. **Path A + `--no_kernels`** — if the cuEq triangle kernels are the problem, this removes them.
4. **Path D** (custom sm_121 wheel).
5. **Path C** (the fork) — reference only.

---

## 3. Known risks

| # | Risk | Likelihood | Blast radius | Mitigation / evidence |
|---|---|---|---|---|
| R1 | `pip install torch` grabs the **default PyPI wheel** (x86 or cu12x) instead of the aarch64 cu130 one | High if you forget `--index-url` | Nothing works | Always `--index-url https://download.pytorch.org/whl/cu130`. Verified aarch64 cp312 wheels exist there for torch 2.9.0, 2.9.1, 2.10.0, 2.11.0, 2.12.0, 2.12.1, 2.13.0, **2.14.0** |
| R2 | `gemmi==0.6.5` has **no linux-aarch64 wheel on PyPI at any version ≤ 0.7.1** → source build | Certain | `pip install -e .` fails without a C++ toolchain | `apt install build-essential cmake python3.12-dev` first. gemmi ≥ 0.7.3 *does* ship aarch64 wheels, but bumping it off Boltz's `==0.6.5` pin risks API breakage — only do so if the source build fails |
| R3 | Triton emits `sm_121a` and an old bundled ptxas rejects it | Low with torch 2.14 | Prediction aborts with `PTXASError` | Triton bundled NVIDIA toolchain versions (from `cmake/nvidia-toolchain-version.json`): **3.5.0 → ptxas 12.8.93 (BROKEN)**; **3.6.0 → +ptxas-blackwell 12.9.86**; **3.7.0 → 13.1.80**; **3.8.0 → 13.3.33**. torch 2.14.0 pins `triton~=3.8.0`. Also set `TRITON_PTXAS_PATH=/usr/local/cuda/bin/ptxas` |
| R4 | Boltz's `[cuda]` extra installs **cu12** cuEquivariance on a CUDA-13 box | Certain if you run `pip install -e .[cuda]` | `ImportError: Error importing triangle_multiplicative_update` | Upstream `pyproject.toml` still pins `cuequivariance_ops_cu12>=0.5.0`. Install the base package and add `*-cu13` yourself |
| R5 | cuEquivariance kernels have no sm_121 path in older versions | Medium | Crash or silent fallback | `cuequivariance-ops-torch-cu13` aarch64 cp312 wheels exist from **0.8.0**; explicit sm_121 PTX handling merged after 0.9.0 ([PR #250](https://github.com/NVIDIA/cuEquivariance/pull/250)); latest is **0.11.1**. Pin ≥ 0.9.1. Escape hatch: `--no_kernels` |
| R6 | Lightning dataloader-worker hang at `Predicting: 0/?` | High at default `--num_workers 2` | Looks like a GPU hang; isn't | `--num_workers 0` |
| R7 | **No internet on demo day and MSAs aren't cached** | High if not rehearsed | Hard `RuntimeError: Missing MSA's in input and --use_msa_server flag not set.` | Section 5. Rehearse the offline run with the network cable out |
| R8 | Weights not pre-downloaded | High | `urllib` timeout at startup | Section 6: 6.2 GB, fetch during setup |
| R9 | `nvidia-smi --query-gpu=memory.*` returns N/A → any script that parses it dies | Certain on GB10 | Monitoring/telemetry only | Section 7 |
| R10 | `--use_potentials` + `--affinity` inflate runtime/memory a lot | Medium | Demo overruns | Affinity needs "2–3x more memory" than structure alone per [NVIDIA's Boltz-2 NIM perf docs](https://docs.nvidia.com/nim/bionemo/boltz2/latest/performance.html). Don't enable affinity for a peptide-HLA demo — the affinity head is for **small molecules ≤128 heavy atoms**, not peptides |
| R11 | `TORCH_FLOAT32_MATMUL_PRECISION` env var doesn't do anything | Medium | Silent no-op; you think TF32 is on when it isn't | The HF wheel README **[community]** recommends this env var, but I could not find it read anywhere in `torch/__init__.py` or `torch/cuda/__init__.py`. Use `torch.set_float32_matmul_precision("high")` in code, or the fork's `--matmul_precision` flag. **Uncertain — verify on the box.** |
| R12 | The fork is 5 upstream commits stale, incl. an autocast device-type fix | Low (if you use upstream) | Subtle numerical/device bugs | Use `jwohlwend/boltz` `main`, not the fork |
| R13 | `fairscale==0.4.13` is sdist-only (no wheels at all) | Certain | Trivial | Pure-Python build, installs fine on ARM |
| R14 | **Boltz-2 NIM container is x86-only** | Certain | Rules out the easiest path | NVIDIA staff, 2025-10-30: *"Those specific NIMs do not have images built for ARM64 which is why you get that error"* ([forum](https://forums.developer.nvidia.com/t/none-of-the-biology-nim-containers-can-run-on-dgx-spark-correct/349486)). Still unresolved. Note this **contradicts** the "NIM container 4.1 s" column in the HF wheel's benchmark table — treat that column as not-on-Spark or not reproducible |

Dependency wheel audit for **linux aarch64 / cp312** (all checked against PyPI on 2026-09-22):
`numpy 1.26.4` ✅ · `scipy 1.13.1` ✅ · `numba 0.61.0` ✅ · `llvmlite 0.49.0` ✅ · `rdkit 2026.3.6` ✅ ·
`dm-tree 0.1.8` ✅ · `scikit-learn 1.6.1` ✅ · `pytorch-lightning 2.5.0` ✅ (pure) · `einx 0.3.0` ✅ (pure) ·
`chembl-structure-pipeline 1.2.2` ✅ (pure) · **`gemmi 0.6.5` ❌ (source build)** · **`fairscale 0.4.13` ❌ sdist (pure, fine)**.
`trifast` (the old Boltz triangle-attention kernel package) has **no aarch64 wheels** — but current
Boltz `main` does not depend on it, so it is a non-issue.

---

## 4. `TORCH_CUDA_ARCH_LIST` — what value for GB10?

* **If you build PyTorch, DeepSpeed, or any CUDA extension from source:** `TORCH_CUDA_ARCH_LIST="12.1"`
  is the literal-correct value and is what the HF sm_121 wheel used. **But `nvcc` from CUDA 13.0
  accepts `compute_121`/`sm_121` while some build systems pass `compute_121` in contexts where it is
  rejected** — the OpenFold3-on-Spark project ships `patch_ds.py` which *remaps invalid `compute_121`
  flags to `compute_120` for NVCC while preserving `sm_121` for Triton's native support* **[community]**
  ([repo](https://github.com/adrian-greenneuron/openfold3-DGX-Spark)).
* **Pragmatic recommendation:** `TORCH_CUDA_ARCH_LIST="12.0;12.1"` or just `"12.0"` — sm_120 SASS runs
  on sm_121 per PyTorch's own `DEVICE_REQUIREMENT` table, and ptrblck states there is no perf gain
  from 12.1.
* **For Boltz-2 specifically you should not need to compile any CUDA at all.** Everything ships as a
  wheel. If you find yourself setting this variable, something has gone wrong.

### Flash-attention / Triton on ARM+Blackwell
* `flash-attn` (Dao-AILab) has **no aarch64 wheels** and a source build on ARM+sm_121 is a multi-hour
  gamble. **Boltz-2 does not need it.** The only place FlashAttention enters Boltz is the unmerged
  [PR #682](https://github.com/jwohlwend/boltz/pull/682), which routes `AttentionPairBias` through
  `torch.nn.functional.scaled_dot_product_attention` (PyTorch's built-in FA2 dispatch — **no extra
  dependency**), benchmarked at 1.15–1.38× on an RTX 5080 / sm_120. Do not bother during a hackathon.
* Triton works fine on aarch64: PyPI has `manylinux_2_27_aarch64` wheels for 3.5.0 through 3.8.0.

---

## 5. MSA dependency — how to run with no internet

### The mechanics (read from `src/boltz/main.py` and `src/boltz/data/parse/schema.py`)
* Without `--use_msa_server`, any protein chain with no `msa:` field raises
  `RuntimeError: Missing MSA's in input and --use_msa_server flag not set.`
* Accepted per-chain `msa:` values:
  * a path ending **`.a3m`** → `parse_a3m()`. Single chain / unpaired.
  * a path ending **`.csv`** → `parse_csv()`. Two columns, **`key`** and **`sequence`**. Rows with the
    same `key` across different chains are treated as *mutually aligned* (paired MSA). `key = -1`
    means unpaired. This is the format you want for a multi-chain complex.
  * the literal string **`empty`** → single-sequence mode for that chain. Boltz prints:
    *"Found explicit empty MSA for some proteins, will run these in single sequence mode. Keep in
    mind that the model predictions will be suboptimal without an MSA."*
  * Anything else is rejected: `MSA file {path} not supported, only a3m or csv.`
* **`msa:` is per-entity**, so you can freely mix: real MSA for the HLA heavy chain, real MSA for
  β2m, `empty` for the 9-mer peptide. (Constraint: all chains sharing the *same sequence* must share
  the same MSA — *"All proteins with the same sequence must share the same MSA!"*.)
* Source: [`docs/prediction.md`](https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md).

### (c) How to precompute MSAs now, while online — the easy way
**Boltz already writes reusable MSA files when you use the server.** From `compute_msa()` in
`main.py`, the server results are dumped to `<out_dir>/<input_stem>/msa/<target_id>_<entity_id>.csv`
with header `key,sequence`, combining paired + unpaired hits. So:

```bash
# ONLINE, once:
boltz predict inputs/hla.yaml --out_dir msa_gen --use_msa_server \
      --num_workers 0 --recycling_steps 0 --sampling_steps 10 --diffusion_samples 1
ls msa_gen/hla/msa/           # hla_0.csv  hla_1.csv  ...  (one per protein entity)
mkdir -p ~/msa_cache && cp msa_gen/hla/msa/*.csv ~/msa_cache/
```
Then in the offline YAML, point each protein chain at its cached CSV. **Rehearse the offline run with
the network physically disconnected** — that is the only way to be sure nothing else phones home.

Alternative (more control, still online): run ColabFold's MMseqs2 API directly and keep `.a3m` files,
e.g. via `colabfold_batch --msa-only`, or paste sequences into
[the ColabFold notebook](https://colabfold.mmseqs.com/). Boltz accepts `.a3m` directly for
single-chain-per-file use.

**Do not attempt a local MMseqs2 database.** ColabFold's reference DBs (`uniref30_2302` +
`colabfold_envdb_202108`) are ~**1 TB** on disk, batch search wants ~128 GB RAM and single-query
search wants ~768 GB RAM ([ColabFold README](https://github.com/sokrypton/ColabFold)). You have 3.4 TB
free and 121 GB unified, so it is *technically* borderline-possible and *practically* insane for a
4-day hackathon.

### (a)+(b) Single-sequence mode: what it costs, and what people actually do for peptide-HLA

This is the part where the pMHC field diverges from generic folding, and it works in your favour.

* **For the peptide: everybody uses no MSA.** A 9-mer has no meaningful homologs; an MMseqs2 search on
  it returns noise. Set `msa: empty`.
* **For the HLA heavy chain and β2m: use a real MSA, or don't — both are defensible.** HLA class I
  heavy chains and β2m are among the most densely sequenced proteins in existence and the fold is
  rigid and heavily represented in the PDB. The AlphaFold-pMHC literature reports that
  *single sequence information (rather than MSA) plus peptide-MHC structure templates as inputs
  achieved best performance*, with **median peptide RMSD ≈ 0.8 Å backbone / 1.8 Å all-atom for class I**
  ([Structure 2023, "Accurate modeling of peptide-MHC structures with AlphaFold"](https://pmc.ncbi.nlm.nih.gov/articles/PMC10028922/) —
  their own fine-tuned pipeline reports median Cα-peptide RMSD **0.73 Å** (discovery) / **0.77 Å** (test)
  using a purpose-built 8,232-sequence *paired* pMHC MSA).
* The same literature notes the MSA matters much more for **class II** register prediction than for
  class I. You are doing class I. **[inference]** Therefore: for a class-I demo, the MSA is a
  nice-to-have, not a correctness gate.
* Boltz's own README/docs call single-sequence mode "not recommended… reduces accuracy" — which is
  true in general and overstated for class-I pMHC specifically.

**Concrete recommendation for your demo:**
1. Cache real MSAs for the HLA heavy chain and β2m while online (they are two fixed sequences — you
   only ever need to do this once, and you can reuse them across every peptide you demo).
2. `msa: empty` for the peptide.
3. Optionally add a pMHC **template** (`templates: - cif: 1HHK.cif` or any class-I structure) — the
   literature above says templates are the biggest single win for peptide placement, and Boltz
   supports `templates:` natively with an optional `force:`+`threshold:` potential.
4. This combination makes your demo **100% offline after step 1, and reusable across peptides without
   any further network access** — swapping the peptide sequence needs no new MSA.

### Example offline YAML (peptide + HLA-A*02:01 heavy chain + β2m)

```yaml
version: 1
sequences:
  - protein:
      id: A                                   # HLA class I heavy chain (~275 aa, alpha1-3)
      sequence: GSHSMRYFFTSVSRPGRGEPRFIAVGYVDDTQFVRFDSDAASQRMEPRAPWIEQEGPEYWDGETRKVKAHSQTHRVDLGTLRGYYNQSEAGSHTVQRMYGCDVGSDWRFLRGYHQYAYDGKDYIALKEDLRSWTAADMAAQTTKHKWEAAHVAEQLRAYLEGTCVEWLRRYLENGKETLQRTDAPKTHMTHHAVSDHEATLRCWALSFYPAEITLTWQRDGEDQTQDTELVETRPAGDGTFQKWAAVVVPSGQEQRYTCHVQHEGLPKPLTLRWE
      msa: /home/USER/msa_cache/hla_0.csv
  - protein:
      id: B                                   # beta-2-microglobulin (99 aa)
      sequence: IQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLKNGERIEKVEHSDLSFSKDWSFYLLYYTEFTPTEKDEYACRVNHVTLSQPKIVKWDRDM
      msa: /home/USER/msa_cache/hla_1.csv
  - protein:
      id: C                                   # 9-mer epitope
      sequence: SLYNTVATL
      msa: empty
# optional but recommended — biggest single accuracy win for peptide placement:
# templates:
#   - cif: /home/USER/templates/1hhk.cif
#     chain_id: [A, B]
```
(Heavy-chain sequence above is an illustrative HLA-A\*02:01 mature ectodomain — **verify against
IMGT/UniProt P04439 for your actual allele before using it.**)

---

## 6. Weights: sizes and cache location

Cache dir resolution (`get_cache_path()` in `main.py`): `$BOLTZ_CACHE` if set (must be absolute),
else `--cache`, else **`~/.boltz`**.

Exact sizes from the Hugging Face API (`boltz-community/boltz-2`, `boltz-community/boltz-1`):

| File | Size | Cache path | Needed for |
|---|---|---|---|
| `boltz2_conf.ckpt` | **2,286.6 MB** (2.29 GB) | `~/.boltz/boltz2_conf.ckpt` | Boltz-2 structure — **required** |
| `boltz2_aff.ckpt` | **2,062.1 MB** (2.06 GB) | `~/.boltz/boltz2_aff.ckpt` | Boltz-2 affinity module (auto-downloaded too) |
| `mols.tar` | **1,855.7 MB** (1.86 GB) | downloaded to `~/.boltz/mols.tar`, extracted to `~/.boltz/mols/` | CCD component data — **required** |
| `boltz1_conf.ckpt` | 3,595.4 MB | `~/.boltz/boltz1_conf.ckpt` | only if `--model boltz1` |
| `ccd.pkl` | 345.9 MB | `~/.boltz/ccd.pkl` | only for Boltz-1 |

**Total Boltz-2 download ≈ 6.2 GB**; budget ~8–10 GB on disk after `mols.tar` extraction (the tar is
kept). `download_boltz2()` is idempotent — it skips any file already present, so it is safe to call
before going offline and safe to leave in the normal run path.

Source URLs (primary, then HF fallback), from `main.py`:
```
https://model-gateway.boltz.bio/boltz2_conf.ckpt   | https://huggingface.co/boltz-community/boltz-2/resolve/main/boltz2_conf.ckpt
https://model-gateway.boltz.bio/boltz2_aff.ckpt    | https://huggingface.co/boltz-community/boltz-2/resolve/main/boltz2_aff.ckpt
https://huggingface.co/boltz-community/boltz-2/resolve/main/mols.tar
```

---

## 7. Runtime expectations and speed knobs

### Published reference numbers
No official Boltz-2 GB10 benchmark exists. What does exist:

* **[community]** `Qanatpharma/pytorch-sm121-gb10` HF model card, Boltz-2 on **HP35** (villin
  headpiece, 35 residues) on a DGX Spark: **7 s**, 81% GPU utilisation, 38.7 W peak, confidence 0.93,
  with the custom sm_121 wheel; ∞ (hang) with the then-current pre-built wheels. The same table lists
  a "NIM container 4.1 s / 76% / 21 W" column which I believe cannot have been measured on the Spark
  (see R14) — **treat with suspicion.**
* **[community]** OpenFold3 on DGX Spark: ubiquitin (76 aa) cold ~3 min, **pre-warmed 55 s**;
  peak memory **15–54 GB** depending on query ([repo](https://github.com/adrian-greenneuron/openfold3-DGX-Spark)).
* **Official, but H100/H200/B200 only** — [Boltz-2 NIM performance page](https://docs.nvidia.com/nim/bionemo/boltz2/latest/performance.html),
  structure prediction, TensorRT, no templates, 1 worker:

  | Residues | H100 80GB (TRT) | H200 (TRT) | B200 (TRT) |
  |---|---|---|---|
  | 186 | 1.72 s | — | — |
  | 530 | 6.63 s | — | — |
  | 1,286 | 24.67 s | 21.62 s | 29.63 s |
  | 2,033 | 79.55 s | — | — |

  TRT is 1.45×–6.44× faster than the OSS Boltz implementation on H100. Templates cost a lot at short
  lengths (186 residues: 1.72 s → 7.27 s). Affinity: 6.21–81.19 s and **2–3× the memory**.

### Estimate for your target (**[inference]** — no measured GB10 pMHC number exists)
Your complex is 275 + 99 + 9 ≈ **383 tokens**, i.e. between the 186- and 530-residue rows.
* H100 OSS (non-TRT) at ~383 residues ≈ 4–10 s.
* GB10 vs H100: **273 GB/s** vs 3.35 TB/s memory bandwidth (~12× less) and far less BF16 compute.
  Boltz inference is heavily bandwidth- and attention-bound.
* **Expect roughly 1–5 minutes per prediction at defaults, plus a one-off 1–3 min warm-up** for
  Triton/cuEq kernel JIT on the very first run (the OpenFold3 report saw a 156 s first-run kernel
  compile that dropped to 0.5 s thereafter). **Measure it on day 1 and budget from the measurement,
  not from this estimate.**
* Unified-memory use: the model checkpoint is 2.3 GB; activations for ~400 tokens are small. Expect
  well under 20 GB of the 121 GB. Memory is not your constraint; time is.

### The knobs, and what they cost
| Flag | Default | Effect on time | Notes |
|---|---|---|---|
| `--sampling_steps` | **200** | **~linear.** 200→50 is ~4× faster on the diffusion stage | Biggest single lever. 50 is usually visually fine; 100 is a safe compromise |
| `--recycling_steps` | **3** | ~linear in the trunk (Pairformer) stage; 3→1 ≈ 2× on that stage | For a rigid, template-like fold like class-I MHC, 1–3 is plenty |
| `--diffusion_samples` | **1** | **linear** | Already 1. Raising to 5 gives you a confidence spread at 5× cost |
| `--max_parallel_samples` | 5 | batching only | Irrelevant at `diffusion_samples 1` |
| `--use_potentials` | off | **+30–100%** **[inference]** | Steering potentials; markedly better stereochemistry/clashes. Worth it for a *structure* demo |
| `--no_kernels` | off | **slower** (einsum instead of cuEq triangle kernels) | Correctness escape hatch, not a speed knob |
| `--subsample_msa` / `--num_subsampled_msa` | on / 1024 | lower = faster trunk | Already subsampling; leave alone |
| `--step_scale` | 1.5 (Boltz-2) | none | Lower = more sample diversity |
| `--output_format pdb` | mmcif | none | PDB is friendlier for PyMOL/py3Dmol in a demo |

### Recommended settings

**Fast-but-real, for a ~9-mer + HLA class I (use this for the live demo):**
```bash
boltz predict input.yaml --out_dir results --num_workers 0 \
  --recycling_steps 3 --sampling_steps 100 --diffusion_samples 1 \
  --use_potentials --output_format pdb --seed 42
```
**Fastest possible (interactive iteration / "does it run at all"):**
```bash
boltz predict input.yaml --out_dir results --num_workers 0 \
  --recycling_steps 1 --sampling_steps 50 --diffusion_samples 1 --output_format pdb
```
**Best quality (run overnight, keep the CIF as the "hero" result):**
```bash
boltz predict input.yaml --out_dir results --num_workers 0 \
  --recycling_steps 10 --sampling_steps 200 --diffusion_samples 5 --use_potentials
```
Read `confidence_*.json` → `iptm` and `pair_chains_iptm` for the **peptide↔heavy-chain interface** —
that is the number that means "the epitope is placed right", far more than `complex_plddt`.

### GPU telemetry on GB10 (the `memory.total = N/A` question)
`nvidia-smi --query-gpu=memory.total/memory.used/memory.free` returns `[N/A]` on GB10 **by design**:
the LPDDR5X pool is unified CPU+GPU and is not a discrete framebuffer exposed through the usual NVML
path. This is a known, widely-hit issue
([nvtop#426](https://github.com/Syllo/nvtop/issues/426),
[llama-swap#782](https://github.com/mostlygeek/llama-swap/issues/782),
[NVIDIA forum](https://forums.developer.nvidia.com/t/dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark/367765)).
What *does* work:

```bash
# GPU utilisation, power, clocks, temp -- these DO work
nvidia-smi --query-gpu=utilization.gpu,power.draw,clocks.sm,temperature.gpu --format=csv -l 1

# per-process GPU memory -- works where the aggregate gauge does not
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

# total / available unified memory -- the actual source of truth
grep -E 'MemTotal|MemAvailable|SwapTotal|SwapFree' /proc/meminfo
free -h          # watch the "available" column; swap must stay at 0 during a run
```
```python
# inside your Boltz process, the most useful numbers of all:
torch.cuda.mem_get_info()              # (free, total) from the CUDA driver
torch.cuda.max_memory_allocated()/2**30
torch.cuda.memory_summary()
```
The pattern the ecosystem has converged on (e.g.
[gnvitop PR #15](https://github.com/Linwei94/gnvitop/pull/15)) is: tolerate `[N/A]`/`[Not Supported]`
from NVML, and fall back to `/proc/meminfo` for capacity plus `--query-compute-apps` for
per-process usage. Community TUIs that already handle GB10 correctly: `spark-smi`, `dgxtop`,
`DanTup/dgx_dashboard` (all listed in [awesome-dgx-spark](https://github.com/bidual/awesome-dgx-spark)).
**Any preflight script that parses `memory.total` will break — grep your scripts for it now.**

---

## 8. Fallbacks if Boltz-2 will not run at all

Ranked by (probability it works on ARM64+sm_121) × (usefulness for peptide-HLA).

1. **Chai-1** (`chai_lab==0.6.1`, [chaidiscovery/chai-lab](https://github.com/chaidiscovery/chai-lab)) —
   **best fallback.** Its `requirements.in` is *pure PyTorch*: no triton pin, no flash-attn, no
   cuequivariance, no custom CUDA extension. Every dep has aarch64 wheels. Runs **MSA-free by
   default** ("uses embeddings without MSAs or templates"), which is exactly your offline
   constraint, and generates 5 samples by default. Caveats: README says *"latest-patch versions
   2.3.1 - 2.7.1 are confirmed to work correctly"* — torch 2.14 is untested, so pin defensively; it
   downloads weights + ESM embeddings on first run, so **warm its cache while online too**. MSAs, if
   you want them, go in as `aligned.pqt` (they ship an `.a3m` converter).
2. **Boltz-1 / Boltz-1x** (`--model boltz1`, same package) — if Boltz-2's affinity/steering code is
   what breaks, Boltz-1 shares the install and needs only `boltz1_conf.ckpt` (3.6 GB) + `ccd.pkl`
   (346 MB). Lower accuracy, no affinity head, but zero extra install risk.
3. **Boltz-2 with `--no_kernels`** — not really a fallback model, but the cheapest thing to try
   before abandoning Boltz-2. Pure-PyTorch triangle ops; slower, same weights, same accuracy.
4. **OpenFold3** — **[community]** proven on this exact hardware
   ([adrian-greenneuron/openfold3-DGX-Spark](https://github.com/adrian-greenneuron/openfold3-DGX-Spark),
   ubiquitin in 55 s warm). But it is a *Docker build* that JIT-compiles DeepSpeed `evoformer_attn`
   kernels and needs the `compute_121 → compute_120` patch. Higher setup cost than Chai-1, and it
   still wants MSAs. Good third option if you want an AF3-class model with a known-good GB10 recipe.
5. **ESMFold** — single-sequence by construction (no MSA at all, perfect for offline), pure PyTorch +
   `fair-esm`/HF `transformers`, ~2.8 GB weights. **But it is single-chain-only in practice** — it
   folds complexes via poly-glycine linkers, which is a bad fit for a three-chain pMHC and gives
   nothing about the peptide register. Use only as a "we can fold *something* on this box" demo.
6. **OpenFold (v1/v2)** — needs DeepSpeed + custom CUDA kernels + a full AlphaFold2 database
   (~2.5 TB). **Do not attempt in 4 days.**
7. **AlphaFold3** — weights require a per-request academic licence from DeepMind and forbid many
   uses; the code also wants a large genetic-database install. **Out of scope for a hackathon.**

---

## 9. Source list

* Boltz upstream: [repo](https://github.com/jwohlwend/boltz) · [`docs/prediction.md`](https://github.com/jwohlwend/boltz/blob/main/docs/prediction.md) · latest release **v2.2.1** (2025-09-08); `main` has 5 commits since, newest `b1ebfc46` (2026-05-29)
* Boltz GB10 issue: [jwohlwend/boltz#663 "Running boltz2 on CUDA 13.0 NVIDIA GB10"](https://github.com/jwohlwend/boltz/issues/663) (open, 2026-03-20) — the only GB10 issue on the tracker
* Boltz SDPA/bugfix PR: [jwohlwend/boltz#682](https://github.com/jwohlwend/boltz/pull/682) (open, 2026-05-18)
* Community fork: [sanjyotshenoy/boltz-gb10-spark](https://github.com/sanjyotshenoy/boltz-gb10-spark) · [`install.sh`](https://github.com/sanjyotshenoy/boltz-gb10-spark/blob/main/install.sh) · [patch commit `5deb18d7`](https://github.com/sanjyotshenoy/boltz-gb10-spark/commit/5deb18d738)
* Custom sm_121 torch wheel: [Qanatpharma/pytorch-sm121-gb10](https://huggingface.co/Qanatpharma/pytorch-sm121-gb10) **[community]**
* PyTorch arch policy: [`.ci/wheel/linux/build_env_setup.py`](https://github.com/pytorch/pytorch/blob/main/.ci/wheel/linux/build_env_setup.py) · [`torch/cuda/__init__.py`](https://github.com/pytorch/pytorch/blob/main/torch/cuda/__init__.py) · [forum thread 223744](https://discuss.pytorch.org/t/dgx-spark-gb10-cuda-13-0-python-3-12-sm-121/223744)
* PyTorch wheel index (verified aarch64 cp312 present): `https://download.pytorch.org/whl/cu130`
* Triton bundled ptxas versions: [`cmake/nvidia-toolchain-version.json`](https://github.com/triton-lang/triton/blob/main/cmake/nvidia-toolchain-version.json) per tag · [`third_party/nvidia/backend/compiler.py`](https://github.com/triton-lang/triton/blob/main/third_party/nvidia/backend/compiler.py) (`sm_arch_from_capability` → `sm_121a`)
* cuEquivariance: [docs](https://docs.nvidia.com/cuda/cuequivariance/index.html) · [PR #250 (sm_121 PTX)](https://github.com/NVIDIA/cuEquivariance/pull/250) · [issue #246 (ptxas for DGX Spark)](https://github.com/NVIDIA/cuEquivariance/issues/246)
* NGC PyTorch container: images API `https://api.ngc.nvidia.com/v2/repos/nvidia/pytorch/images` (arm64+amd64 confirmed) · [26.08 release notes](https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-26-08.html)
* Boltz-2 NIM: [performance tables](https://docs.nvidia.com/nim/bionemo/boltz2/latest/performance.html) · [ARM64 unavailability, NVIDIA staff](https://forums.developer.nvidia.com/t/none-of-the-biology-nim-containers-can-run-on-dgx-spark-correct/349486)
* DGX Spark playbooks: [NVIDIA/dgx-spark-playbooks](https://github.com/NVIDIA/dgx-spark-playbooks) — **no Boltz or structure-prediction playbook exists** (checked the full file tree; nearest are `playbook-healthcare-agent` with OpenFold3 test scripts and `playbook-single-cell`)
* Community index: [bidual/awesome-dgx-spark](https://github.com/bidual/awesome-dgx-spark) (§ scientific compute) · [adrian-greenneuron/openfold3-DGX-Spark](https://github.com/adrian-greenneuron/openfold3-DGX-Spark)
* GB10 telemetry: [nvtop#426](https://github.com/Syllo/nvtop/issues/426) · [llama-swap#782](https://github.com/mostlygeek/llama-swap/issues/782) · [gnvitop PR#15](https://github.com/Linwei94/gnvitop/pull/15) · [NVIDIA forum](https://forums.developer.nvidia.com/t/dear-nvidia-nvidia-smi-is-broken-on-the-dgx-spark/367765)
* pMHC modelling: ["Accurate modeling of peptide-MHC structures with AlphaFold", Structure 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10028922/) · [TCR–pMHC benchmarking, Brief. Bioinform. 2026](https://academic.oup.com/bib/article/27/3/bbag289/8703116)
* MSA infrastructure: [sokrypton/ColabFold](https://github.com/sokrypton/ColabFold) (DB sizes / RAM requirements)
* Fallbacks: [chaidiscovery/chai-lab](https://github.com/chaidiscovery/chai-lab)
