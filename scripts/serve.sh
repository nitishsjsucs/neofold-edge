#!/usr/bin/env bash
# Serve the dashboard from the Nano, reachable over the tailnet and nowhere else.
#
# BIND DEFAULTS TO THE TAILSCALE ADDRESS, NOT 0.0.0.0, AND THAT IS DELIBERATE.
# Binding to all interfaces would also publish the dashboard on whatever Wi-Fi
# the machine happens to be joined to -- including a conference network on demo
# day. The tailnet address is private to your own devices.
#
#   ./scripts/serve.sh            # start (or restart) in a tmux session
#   ./scripts/serve.sh status     # is it up, and on what address
#   ./scripts/serve.sh logs       # tail the log
#   ./scripts/serve.sh stop       # stop it
#
#   BIND=127.0.0.1 ./scripts/serve.sh    # loopback only; reach it by SSH tunnel
set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$PWD"
SESSION="${SESSION:-neofold}"
PORT="${PORT:-8420}"
LOG="$ROOT/.serve.log"

# Prefer the tailnet address; fall back to loopback if Tailscale is not up.
if [ -z "${BIND:-}" ]; then
  BIND="$(tailscale ip -4 2>/dev/null | head -1 || true)"
  [ -n "$BIND" ] || BIND=127.0.0.1
fi

VENV="$ROOT/.venv-app"
[ -d "$VENV" ] || VENV="$ROOT/.venv"

case "${1:-start}" in
  status)
    if tmux has-session -t "$SESSION" 2>/dev/null; then
      echo "running in tmux session '$SESSION'"
      curl -sS -o /dev/null -w "  http://$BIND:$PORT  ->  HTTP %{http_code}\n" \
        --max-time 5 "http://$BIND:$PORT/api/health" || echo "  not responding yet"
    else
      echo "not running"
    fi
    exit 0 ;;
  logs) exec tail -f "$LOG" ;;
  stop)
    tmux kill-session -t "$SESSION" 2>/dev/null && echo "stopped" || echo "was not running"
    exit 0 ;;
esac

tmux kill-session -t "$SESSION" 2>/dev/null || true
tmux new-session -d -s "$SESSION" \
  "cd '$ROOT' && . '$VENV/bin/activate' && exec python -m uvicorn app.main:app \
   --host '$BIND' --port '$PORT' >> '$LOG' 2>&1"

# The startup thread warms the MHCflurry models and the proteome seed index,
# which takes ~25 s. Wait for /api/health rather than guessing.
printf 'starting on %s:%s ' "$BIND" "$PORT"
for _ in $(seq 1 60); do
  if curl -sS -o /dev/null --max-time 2 "http://$BIND:$PORT/api/health" 2>/dev/null; then
    echo; echo "ready:  http://$BIND:$PORT"
    command -v hostname >/dev/null && \
      echo "        http://$(hostname):$PORT   (tailnet MagicDNS name)"
    echo
    echo "tmux attach -t $SESSION    # watch it"
    echo "$0 stop                    # stop it"
    exit 0
  fi
  printf '.'; sleep 1
done
echo; echo "did not come up in 60 s -- check: $0 logs" >&2
exit 1
