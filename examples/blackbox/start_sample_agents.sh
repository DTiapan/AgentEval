#!/usr/bin/env bash
# Start all rule-based sample agents (separate terminals not required).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

start_one() {
  local script="$1"
  local port="$2"
  if lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "Port $port already in use — skipping $script"
    return
  fi
  python3 "$script" &
  echo "Started $script (PID $!) on :$port"
}

start_one refund_agent_server.py 8765
start_one helpdesk_agent_server.py 8767
start_one fulfillment_agent_server.py 8768

echo ""
echo "Sample endpoints:"
echo "  Refund:       http://127.0.0.1:8765/chat  (+ examples/blackbox/refund-agent-prd.md)"
echo "  Helpdesk:     http://127.0.0.1:8767/chat  (+ examples/blackbox/helpdesk-agent-prd.md)"
echo "  Fulfillment:  http://127.0.0.1:8768/chat  (+ examples/blackbox/fulfillment-agent-prd.md)"
echo "AgentEval API/console: agenteval serve  →  http://127.0.0.1:8766/"
