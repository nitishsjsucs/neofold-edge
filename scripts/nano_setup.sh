#!/usr/bin/env bash
# Full reproducible setup on the HP ZGX Nano (GB10, aarch64, CUDA 13).
#
# Every step here was executed and verified on the machine. Notably it needs
# NO sudo: the one component that normally requires `apt install python3.12-dev`
# is worked around by unpacking the .deb into $HOME.
#
# Usage:  bash scripts/nano_setup.sh [--with-openmm]
set -euo pipefail

NEOFOLD_HOME="${NEOFOLD_HOME:-$HOME/neofold}"
WITH_OPENMM=0
[[ "${1:-}" == "--with-openmm" ]] && WITH_OPENMM=1

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }

mkdir -p "$NEOFOLD_HOME"
cd "$NEOFOLD_HOME"

# ---------------------------------------------------------------------------
say "1/6  Python headers without sudo"
# Triton compiles a CUDA shim at runtime and needs Python.h; gemmi needs it too
# if you ever use the upstream 0.6.5 pin. `apt-get download` needs no root.
if [[ ! -f "$HOME/pylocal/usr/include/python3.12/Python.h" ]]; then
  mkdir -p "$HOME/pkgtmp" "$HOME/pylocal"
  (cd "$HOME/pkgtmp" && apt-get download libpython3.12-dev python3.12-dev)
  for d in "$HOME"/pkgtmp/*.deb; do dpkg-deb -x "$d" "$HOME/pylocal"; done
fi
export CPATH="$HOME/pylocal/usr/include/python3.12:$HOME/pylocal/usr/include"
export PATH="/usr/local/cuda/bin:$PATH"
echo "Python.h: $(ls "$HOME/pylocal/usr/include/python3.12/Python.h")"

# ---------------------------------------------------------------------------
say "2/6  Boltz-2 environment (GPU)"
if [[ ! -d .venv-boltz ]]; then python3 -m venv .venv-boltz; fi
# shellcheck disable=SC1091
source .venv-boltz/bin/activate
pip install -q --upgrade pip wheel setuptools

# cu132 is the newest stable aarch64 build and runs fine on the 13.0 driver.
# sm_120 SASS is valid on GB10's sm_121, so no custom wheel is needed.
pip install -q "numpy<2.0" torch==2.14.0+cu132 \
  --index-url https://download.pytorch.org/whl/cu132 \
  --extra-index-url https://pypi.org/simple

# Boltz pins gemmi==0.6.5, which has no aarch64 wheel. 0.7.5 does. Install it
# first and take Boltz with --no-deps; the resulting pip warning is cosmetic.
pip install -q gemmi==0.7.5
pip install -q boltz==2.2.1 --no-deps
pip install -q hydra-core==1.3.2 pytorch-lightning==2.5.0 "rdkit>=2024.3.2" \
  dm-tree==0.1.8 requests==2.32.3 "pandas>=2.2.2" types-requests einops==0.8.0 \
  einx==0.3.0 fairscale==0.4.13 mashumaro==3.14 modelcif==1.2 wandb==0.18.7 \
  click==8.1.7 pyyaml==6.0.2 biopython==1.84 scipy==1.13.1 numba==0.61.0 \
  scikit-learn==1.6.1 chembl_structure_pipeline==1.2.2

# Boltz's [cuda] extra pins the CUDA-12 cuEquivariance build, which is wrong
# here and breaks the triangle kernels. Install the cu13 packages instead.
pip install -q "cuequivariance-torch>=0.9.1" "cuequivariance-ops-torch-cu13>=0.9.1"

python -c "import torch,boltz; print('torch',torch.__version__,'cuda',torch.cuda.is_available())"
deactivate

# ---------------------------------------------------------------------------
say "3/6  MHCflurry environment (CPU, keeps the GPU free for Boltz)"
if [[ ! -d .venv-mhc ]]; then python3 -m venv .venv-mhc; fi
# shellcheck disable=SC1091
source .venv-mhc/bin/activate
pip install -q --upgrade pip
pip install -q torch --index-url https://download.pytorch.org/whl/cpu
pip install -q mhcflurry fastapi uvicorn gemmi
deactivate

# ---------------------------------------------------------------------------
say "4/6  Pre-fetch everything the offline demo needs"
source .venv-mhc/bin/activate
mhcflurry-downloads fetch models_class1_presentation   # ~198 MB
deactivate
# Boltz weights (~6.2 GB) download on first prediction into ~/.boltz
if [[ ! -f "$HOME/.boltz/boltz2_conf.ckpt" ]]; then
  echo "NOTE: Boltz weights not yet cached. Run one prediction WHILE ONLINE."
fi

# ---------------------------------------------------------------------------
if [[ $WITH_OPENMM == 1 ]]; then
  say "5/6  OpenMM (separate venv -- its nvidia-* stack conflicts with torch's)"
  if [[ ! -d .venv-md ]]; then python3 -m venv .venv-md; fi
  # shellcheck disable=SC1091
  source .venv-md/bin/activate
  pip install -q --upgrade pip wheel
  pip install -q "openmm[cuda13]==8.6.1"
  # CUDA minor-version compatibility EXCLUDES PTX JIT: the default nvrtc (13.4)
  # can emit PTX that a 13.0 driver rejects. Pin it down to match the driver.
  pip install -q --force-reinstall "nvidia-cuda-nvrtc==13.0.88"
  pip install -q "pdbfixer==1.12.0" "mdtraj==1.11.1.post2" numpy
  python -m openmm.testInstallation || echo "OpenMM install test reported problems"
  deactivate
else
  say "5/6  OpenMM skipped (pass --with-openmm to include it)"
fi

# ---------------------------------------------------------------------------
say "6/6  Done"
cat <<EOF

Environments created under $NEOFOLD_HOME:
  .venv-boltz   structure prediction (GPU)
  .venv-mhc     binding screen + web app (CPU)
$( [[ $WITH_OPENMM == 1 ]] && echo "  .venv-md      OpenMM stability test (GPU)" )

Every Boltz run needs these, and --num_workers 0:
  export PATH=/usr/local/cuda/bin:\$PATH
  export CPATH=\$HOME/pylocal/usr/include/python3.12:\$HOME/pylocal/usr/include
EOF
