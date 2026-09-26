# AgentEval

> **Production-Grade AI Agent Assurance, Reliability & Chaos Engineering Platform**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

AgentEval is an enterprise-grade agent assurance platform designed to test autonomous agents as **stateful, looping distributed systems** rather than single-turn prompt-response generators.

## Core Philosophy

- **BYOA (Bring Your Own Agent)**: Connect any agent (Python in-process, HTTP, MCP, CLI) with zero code rewrites.
- **Trajectory-First Assurance**: Verify the full thought → action → observation chain, not just the final output string.
- **Sealed Execution Evidence**: Assert real environmental mutations (ΔS: disk, database rows, mock API calls).
- **Chaos & Fault Injection**: Inject synthetic timeouts, HTTP 500s, 429s, and process crashes (`SIGKILL`) to evaluate recovery and idempotency (`duplicate_side_effect_rate`).
- **Interactive Time-Travel Replay**: Play back runs step-by-step with jumps to the root-cause failure point (Web Console or `agenteval replay` for harness traces).
- **No Guesswork Verdicts**: Explicit `UNVERIFIABLE` verdict when environmental evidence cannot be proven.

## Quickstart (Web Console — product default)

End-to-end MVP: **PRD → agent URL → create suite → run → report**. Console fields come from the engine API only ([MVP checklist](docs/MVP.md)). SQLite persistence is on by default with `agenteval serve`.

```bash
# Install
uv pip install -e ".[dev]"

# Build the console once
cd web && npm install && npm run build && cd ..

# API + Web UI + SQLite (http://127.0.0.1:8766/#/console)
agenteval serve

# API only (no web/dist)
agenteval serve --no-ui
```

**Try it with the sample refund agent** (`agenteval serve` does **not** start the agent for you)

```bash
# Terminal 1 — mock HTTP agent on :8765 (leave running)
python3 examples/blackbox/refund_agent_server.py

# Terminal 2 — serve console
agenteval serve
```

**Preferred sample (real tools + SQLite):** see [examples/real-agent/README.md](examples/real-agent/README.md) — `OPENAI_API_KEY`, then `python3 examples/real-agent/ops_agent_server.py` (`http://127.0.0.1:8770/chat`) and import `examples/real-agent/ops-agent-prd.md`.

Keyword mocks in `examples/blackbox/` are optional CI fixtures, not the product default.

For local UI hot reload: `npm run dev` in `web/` (proxies to port 8766) with `agenteval serve` or `agenteval serve --no-ui`.

**Clean slate** (removes persisted suites like old demo runs — not done automatically):

```bash
agenteval db reset --yes
cd web && npm run build && cd ..
agenteval serve
```

In the console header, choose **New suite…** for an empty Studio form without deleting other agents.

## Advanced: harness & engineering CLI

Scenario YAML and in-process sandbox proof remain supported for framework users and CI — not the default onboarding path.

```bash
agenteval run --scenario examples/scenarios/
agenteval suite init --prd path/to/requirements.md --endpoint http://127.0.0.1:8080/agent
```

See [Product Roadmap](docs/ROADMAP.md) and [DR-021](docs/engineering-ledger/decisions.md#active-index) (Web UI-first delivery).

## Architecture & Roadmap

- [Product Roadmap (v0.1 → v1.0)](docs/ROADMAP.md)
- [Black-Box Test Intelligence Pipeline](docs/design/black-box-test-intelligence-pipeline.md) — spec + endpoint → optimized test pack, coverage, limitations ([ADR-003](docs/decisions/ADR-003-black-box-test-intelligence-pipeline.md))
- [System Architecture](docs/design/architecture.md)
- [Idea Refinement One-Pager](docs/ideas/agent-assurance-platform.md)
- [ADR-001: Inspect AI Foundation](docs/decisions/ADR-001-build-on-inspect-ai.md)
