# AgentEval

> **Production-Grade AI Agent Assurance, Reliability & Chaos Engineering Platform**

[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

AgentEval is an enterprise-grade agent assurance platform designed to test autonomous agents as **stateful, looping distributed systems** rather than single-turn prompt-response generators.

## Core Philosophy

- **BYOA (Bring Your Own Agent)**: Connect any agent (Python in-process, HTTP, MCP, CLI) with zero code rewrites.
- **Trajectory-First Assurance**: Verify the full thought $\to$ action $\to$ observation chain, not just the final output string.
- **Sealed Execution Evidence**: Assert real environmental mutations ($\Delta S$: disk, database rows, mock API calls).
- **Chaos & Fault Injection**: Inject synthetic timeouts, HTTP 500s, 429s, and process crashes (`SIGKILL`) to evaluate recovery and idempotency (`duplicate_side_effect_rate`).
- **Interactive Time-Travel Replay**: Play back runs live (`--live`) or step-by-step (`agenteval replay <run-id>`) with direct jumps to the root-cause failure point (`--jump-to-fail`).
- **No Guesswork Verdicts**: Explicit `UNVERIFIABLE` verdict when environmental evidence cannot be proven.

## Quickstart

```bash
# Install in editable mode with dev dependencies
uv pip install -e ".[dev]"

# Run test scenarios against your agent
agenteval run --scenario examples/scenarios/

# Run with live-streaming step execution
agenteval run --scenario examples/scenarios/ --live

# Replay an execution interactively
agenteval replay <run-id> --jump-to-fail
```

## Architecture & Roadmap

- [Product Roadmap (v0.1 → v1.0)](docs/ROADMAP.md)
- [System Architecture](docs/design/architecture.md)
- [Idea Refinement One-Pager](docs/ideas/agent-assurance-platform.md)
- [ADR-001: Inspect AI Foundation](docs/decisions/ADR-001-build-on-inspect-ai.md)
