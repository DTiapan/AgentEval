# CONSTRAINTS.md — AgentEval Quality Bar & Behavioral Contract

Last reviewed: 2026-09-20 by @craft

## 1. Non-Negotiable Quality Floor (Always Enforced)

- **Anti-AI Slop Guarantee**: We refine and build a battle-tested, production-grade product. Never output generic boilerplate, placeholder stubs, or lazy "AI slop".
- **Skill-First Discipline**: For every phase and sub-task, inspect `.agents/skills/` and utilize the appropriate skill (`using-craft`, `idea-refine`, `system-design`, `architecture-diagram`, `ui-ux-pro-max`, `test-driven-development`, `api-design`).
- **UI/UX Excellence**: Whenever frontend or user interfaces are touched, strictly follow `ui-ux-pro-max` and `frontend-ui-engineering` (Cursor: [`.cursor/rules/ui-frontend-strict.mdc`](.cursor/rules/ui-frontend-strict.mdc)). Read both SKILL.md files, run `ui-ux-pro-max` `search.py` per slice, document what you applied. No basic browser defaults, generic color schemes, or unstyled tables. Premium typography, dark mode, responsive layouts, and interactive micro-states are mandatory. No UI “MVP drift” without completing the skill workflow.
- **No Unimplemented Stubs**: No `throw new Error("TODO")`, `pass` placeholders in production logic, or empty `catch {}` blocks.
- **No Suppression Comments**: No `@ts-ignore`, `eslint-disable`, `# noqa`, or `# type: ignore` without an approved exception.
- **Deterministic Evidence over Self-Report**: Evaluators must assert actual environment state diffs (DB rows, file writes, HTTP calls) and never rely solely on an agent's self-generated claim. If proof is missing, label as `UNVERIFIABLE`.
- **Real Data in Product UI (no demo execution)**: Console, replay, reports, and assurance views must not show synthetic trajectories, invented tool steps, or hardcoded “demo” outcomes. All visible run data must come from engine/API artifacts; if traces are not captured yet, show honest empty/UNVERIFIABLE states and implement persistence first. Enforced in Cursor by [`.cursor/rules/no-demo-ui-data.mdc`](.cursor/rules/no-demo-ui-data.mdc).
- **Black-Box vs Harness Profiles** ([ADR-003](docs/decisions/ADR-003-black-box-test-intelligence-pipeline.md)): In **`harness`** profile, sealed ΔS and tool interception apply. In **`blackbox`** profile (default for enterprise endpoint eval), assert only **observable** endpoint evidence; report **UNTESTABLE** for internal state (e.g. DB consistency) unless the customer provides an external probe. Never conflate the two in verdict copy.

## 2. Enforced Engineering Dimensions

| Dimension | Rule | Checked by | Runs at |
|---|---|---|---|
| **Skill Routing** | Check & apply relevant `.agents/skills` per task | `using-craft` | Every session/phase |
| **Python Typing** | Strict type hinting on all domain models & adapters | `mypy --strict` / `ruff check` | Every edit |
| **Linting & Formatting** | Flawless formatting and PEP8/standard compliance | `ruff check` & `ruff format` | Every edit |
| **Unit & Integration Tests** | 100% passing suite on adapters and evaluation engine | `pytest tests/` | Every task |
| **Security: Secrets** | Zero API keys, tokens, or credentials in codebase | `gitleaks detect --redact` | Commit, CI |
| **UI Aesthetics** | Rich theme tokens, CSS variables, accessible contrast | `ui-ux-pro-max` heuristics | UI builds |

## 3. Measured Metrics & Ratchets

| Metric | Baseline | Direction |
|---|---|---|
| Code Coverage on Core Modules | 85% | Must not fall |
| Trajectory Evaluation Determinism | 100% reproducible | Must not drift |
| Adapter Latency Overhead | < 15ms per step | Must not grow |

## 4. Exceptions & Drift Policy

This file is a contract. An agent may not weaken thresholds, delete assertions, or skip tests to make a build turn green. Any exception must be explicitly reviewed and documented.
