# AGENTS.md — AgentEval

Welcome agent! This file defines repository rules, operating principles, and workflow orchestration for **AgentEval: Production-Grade AI Agent Assurance & Evaluation Platform**.

## Craft (orchestration + ledger)

- Non-trivial work: read `docs/engineering-ledger/INDEX.md` first.
- Read `CONSTRAINTS.md` before writing code. Do not weaken it to make a change pass.
- Route phases and tasks via `using-craft` skill by searching `.agents/skills/` (never produce unvalidated AI slop).
- **Skill-driven development (required):** Before implementing, post a **Skill declaration** — **phase**, **one primary skill** (read `.agents/skills/<name>/SKILL.md`; route via `using-craft`), **optional overlay** at most one. Enforced in Cursor by [`.cursor/rules/skill-driven-development.mdc`](.cursor/rules/skill-driven-development.mdc). No skill stacking; no unvalidated slop; minimal diffs per `CONSTRAINTS.md`. Say when the slice is done and which skill gates the next step.
- Append DR/LL/INDEX before ending substantive sessions.
- Irreversible forks: ADR in `docs/decisions/` per `documentation-and-adrs`.

## Engineering Core Principles

1. **Pluggable Agent Architecture (BYOA)**: Any agent (HTTP/REST, MCP, CLI, Python callable) must be a drop-in evaluation target with zero code changes required.
2. **Trajectory-First Assurance**: Validate the full thought-action-observation-side effect chain, not just the final string output.
3. **Deterministic Evidence vs Self-Report**: Never trust an agent's self-generated claim; always assert environmental side-effects (files, DB, API mutations) using sealed execution evidence.
4. **Autonomous Golden Dataset Loop**: Continuously curate failure traces from telemetry into regression test suites with adversarial perturbations.
5. **No Guesswork Verdicts**: Explicitly flag unprovable actions as `UNVERIFIABLE` rather than assuming silent passes or guessed failures.
6. **Open Standards First**: Native OpenTelemetry and OpenInference compliance for traces, spans, and telemetry.
