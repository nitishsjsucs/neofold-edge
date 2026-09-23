#!/usr/bin/env bash
# Prove the pipeline runs with no network access.
#
# Rather than unplugging (which would also kill your SSH session), this points
# every HTTP(S) client at a dead port. Any outbound call fails loudly, so a
# successful run is evidence that none was made.
#
# Run this BEFORE the demo, with all weights already cached.
set -uo pipefail

NEOFOLD_HOME="${NEOFOLD_HOME:-$HOME/neofold}"
CASE="${1:-cases/kras_g12d_c0802_cached.yaml}"
OUT="${2:-offline_proof}"

cd "$NEOFOLD_HOME"
# shellcheck disable=SC1091
source .venv-boltz/bin/activate
export PATH="/usr/local/cuda/bin:$PATH"
export CPATH="$HOME/pylocal/usr/include/python3.12:$HOME/pylocal/usr/include"

# Dead proxy: 127.0.0.1:9 is the discard port, nothing listens there.
export http_proxy="http://127.0.0.1:9"  https_proxy="http://127.0.0.1:9"
export HTTP_PROXY="$http_proxy"         HTTPS_PROXY="$https_proxy"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 WANDB_MODE=offline

echo "=== network sanity check (this SHOULD fail) ==="
if curl -s --max-time 5 https://pypi.org > /dev/null 2>&1; then
  echo "!! WARNING: outbound HTTPS still works -- the proxy block is not in effect"
else
  echo "OK: outbound HTTPS is blocked inside this shell"
fi

echo
echo "=== running prediction with no network ==="
START=$(date +%s)
boltz predict "$CASE" \
  --out_dir "$OUT" --accelerator gpu --num_workers 0 \
  --recycling_steps 3 --diffusion_samples 1 --sampling_steps 200 \
  --output_format mmcif --override 2>&1 | tail -6
EXIT=${PIPESTATUS[0]}
echo "exit=$EXIT  wall=$(( $(date +%s) - START ))s"

if [[ $EXIT -eq 0 ]]; then
  echo
  echo "PASS: a full structure prediction completed with all network access blocked."
  find "$OUT" -name "*_model_0.cif" | head
else
  echo
  echo "FAIL: prediction did not complete offline. Most likely an asset is not"
  echo "cached yet. Re-run it once ONLINE, then try this again."
fi
exit $EXIT
