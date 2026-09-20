# Black-box MVP walkthrough (no LLM judge)

## What this proves

1. **Suite init** — requirements + `AgentCard` → candidate pool → optimized pack → saved under `.agenteval/suites/`
2. **Suite run** — frozen pack executed against HTTP endpoint → **rule-based** PASS/FAIL/UNVERIFIABLE (Tier 0 scorer)

## Prerequisites

- Python 3.11+
- `pip install -e ".[dev]"` from repo root
- **No API keys** required for this demo

## Steps

### Terminal 1 — start mock agent

```bash
python examples/blackbox/refund_agent_server.py
```

### Terminal 2 — bootstrap suite (generate once)

```bash
agenteval suite init \
  --manifest examples/blackbox/refund_agent.card.yaml \
  --endpoint http://127.0.0.1:8765/chat \
  --max-tests 10
```

### Terminal 2 — regression run (no regeneration)

```bash
agenteval suite run --agent-id refund-agent
```

Re-run `suite run` after changing the mock server to see regressions.

## Artifacts

```
.agenteval/suites/refund-agent/
  suite.manifest.json
  candidate_pool.json
  test_pack.json
  runs/<run_id>.json
  latest_run.json
```
