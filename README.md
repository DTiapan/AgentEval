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

Upload **requirements (PRD)** and an optional **agent URL** in Studio; freeze the pack, run assurance, inspect trajectories and reports. Data is persisted in SQLite when you use `agenteval serve` (default).

```bash
# Install
uv pip install -e ".[dev]"

# Build the console once
cd web && npm install && npm run build && cd ..

# API + Web UI + SQLite persistence (opens http://127.0.0.1:8766/)
agenteval serve

# API only (no web/dist)
agenteval serve --no-ui
```

For local UI development with hot reload, run `npm run dev` in `web/` (proxies API to port 8766) alongside `agenteval serve --no-ui` or full `agenteval serve`.

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
