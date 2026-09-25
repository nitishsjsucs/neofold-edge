#!/usr/bin/env bash
# Regenerate the README screenshots from the running app.
#
# Uses headless Chrome plus the app's own deep-link parameters (?run=1&tab=...)
# so every shot is reproducible from a URL rather than hand-driven. Start the
# app first:  python -m uvicorn app.main:app --port 8420
set -euo pipefail

CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
URL="${URL:-http://localhost:8420}"
OUT="$(cd "$(dirname "$0")/.." && pwd)/docs/img"
mkdir -p "$OUT"

shot(){                                   # shot <name> <w> <h> <query>
  local name=$1 w=$2 h=$3 q=$4
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --no-sandbox \
    --enable-unsafe-swiftshader --use-gl=angle --use-angle=swiftshader \
    --window-size="$w,$h" --force-device-scale-factor=2 \
    --virtual-time-budget=25000 \
    --screenshot="$OUT/$name.png" "$URL/$q" >/dev/null 2>&1
  # Crop the dead background a fixed window leaves below a short panel, then
  # cap the width: 2x device pixels is more than GitHub ever renders.
  python3 "$(dirname "$0")/_trim.py" "$OUT/$name.png"
}

echo "capturing to docs/img ..."
shot dashboard          1560 1010 "?run=1"
shot candidates         1120 1500 "?run=1&figure=candidates"
shot structure          1120 1500 "?figure=structure&structure=kras_g12d_9mer_mut_model_0"
shot evidence-roc       1120 1720 "?figure=evidence&tab=pane-val"
shot evidence-holdout   1120 1450 "?figure=evidence&tab=pane-holdout"
shot evidence-plddt     1120 1260 "?figure=evidence&tab=pane-conf"
shot evidence-md        1120  980 "?figure=evidence&tab=pane-md"
shot evidence-scaling   1120  900 "?figure=evidence&tab=pane-bench"
echo "done."
