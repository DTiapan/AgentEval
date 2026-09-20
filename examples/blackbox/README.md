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
python3 examples/blackbox/refund_agent_server.py
```

### Terminal 2 — preview pack (optional, no files written)

**North Star entry (requirements only):**

```bash
agenteval plan --prd examples/blackbox/requirements.md --max-tests 10
```

Or with manifest:

```bash
agenteval plan --manifest examples/blackbox/refund_agent.card.yaml --max-tests 10
```

### Terminal 2 — bootstrap suite (generate once)

```bash
# Requirements only (run later with -e on suite run):
agenteval suite init \
  --prd examples/blackbox/requirements.md \
  --agent-id refund-agent \
  --max-tests 10

# Requirements + endpoint (probe + store URL):
agenteval suite init \
  -e http://127.0.0.1:8765/chat \
  --prd examples/blackbox/requirements.md \
  --agent-id refund-agent \
  --max-tests 10
```

Writes `derived_agent_card.json`; with `-e`, also `endpoint_probe.json` (inferred tools/JSON shape).

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

**Reports:** CLI table on `suite run` plus JSON above. Rich Allure-style HTML reports are planned later ([roadmap](../docs/ROADMAP.md), B8 report slice)—same direction as the assurance dashboard, not flat JUnit/CSV exports.
