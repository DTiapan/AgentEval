# Idea Refinement: AgentEval (AI Agent Assurance & Reliability Platform)

> Formulated under `idea-refine` skill guidelines.
> Date: 2026-09-20
> Status: Ready for Shape Gate Sign-Off

---

## 1. Problem Statement

**How Might We** provide autonomous AI agent builders with deterministic, sealed execution assurance, fault-injection resilience, and interactive replay so they can deploy agents into production with 100% verifiable reliability rather than vibes-based testing?

---

## 2. Target User & Success Criteria

### Target User
AI Agent engineers, framework builders (LangGraph, CrewAI, AutoGen, Antigravity SDK), and enterprise AI platform teams shipping agents with tool-calling and system mutation capabilities into production environments.

### What Success Looks Like
1. **Zero-Code Instrumentation (BYOA)**: A developer points `agenteval run` at their agent (callable, HTTP, MCP, or CLI) with zero code rewrites.
2. **Deterministic Evidence vs Self-Report**: The platform asserts actual environmental mutations ($\Delta S$: disk, database rows, mock API calls) rather than trusting an agent's self-generated string output.
3. **Chaos Resilience**: Injects synthetic tool timeouts, HTTP 500s, 429s, and process crashes to verify that the agent retries safely with idempotency and resumes from checkpoints.
4. **Interactive Time-Travel Replay**: When an agent fails, developers can step through the trajectory live (`--live`), rewind/fast-forward (`agenteval replay`), and jump directly to the root-cause failure point (`--jump-to-fail`).
5. **No Guesswork Verdicts**: Explicit `UNVERIFIABLE` verdict whenever environmental evidence is missing, refusing to guess.

---

## 3. Recommended Direction: Inspect AI Foundation + Unique Reliability IP

We evaluated three strategic paths:
- **Direction A (Build from scratch)**: High risk, months wasted recreating task loops, loggers, and evaluation scaffolding.
- **Direction B (Build on DeepEval)**: SaaS/cloud lock-in, primarily string-matching/G-Eval LLM metrics, lacks sandbox state diffing.
- **Direction C (Recommended & Accepted — ADR-001)**: Build on UK AISI's **Inspect AI** (MIT license) as the evaluation engine core, and engineer our unique intellectual property as composable extensions:
  1. Universal BYOA Adapters (HTTP, MCP, CLI, Callable).
  2. Chaos Engineering & Tool Fault Injection Middleware (`ToolFaultInjector`).
  3. Deterministic State Diff Assertions (`StateDiffEvaluator`).
  4. Idempotency & Duplicate Side-Effect Scorer (`IdempotencyScorer`).
  5. Interactive Terminal & Web Replay Engine (`agenteval replay`).
  6. Tiered Fast Judge (Jev System One typed scoring with LLM fallback).

---

## 4. Key Assumptions to Validate

| # | Assumption | Validation Strategy | Status |
|---|---|---|---|
| **1** | Any agent can be wrapped as an Inspect AI Solver without modifying the agent's internal code. | Implement `CallableAdapter` in v0.1 and test against a sample multi-turn tool-calling agent. | Validating in v0.1 |
| **2** | Synthetic tool faults (timeouts, HTTP 500) can be injected transparently via a proxy without changing the agent runtime. | Implement `ToolFaultInjector` proxy in `agenteval/faults/` and verify agent retry behavior. | Validating in v0.1 |
| **3** | Pre/post environment state diffs ($\Delta S$) can be captured deterministically across temp dirs and SQLite databases. | Build `LocalSandbox` with pre/post state hash snapshots. | Validating in v0.1 |
| **4** | Developers prefer stepping through an interactive terminal TUI / Web scrubber over reading large raw JSON logs. | Deliver `agenteval replay <run-id> --jump-to-fail` and test DX. | Validating in v0.1 |
| **5** | Jev (TypeSafe AI) can score typed classification checks 40–200x faster than LLM judges with $\ge 90\%$ accuracy. | Benchmark Jev vs. GPT-4o judge on tool schema & safety classification in v0.3. | Planned for v0.3 |

---

## 5. MVP Scope (v0.1 — "Prove the Core Loop & Chaos Harness")

### What's In:
- Core Domain Models (`ExecutionTrace`, `StepRecord`, `ToolCall`, `ToolResult`, `StateSnapshot`, `Verdict`, `ReliabilityScorecard`).
- Agent Loop Metrics (`agent_loop_iterations`, `duplicate_actions`, `termination_reason`, `tokens_consumed`, `time_to_completion`).
- `CallableAdapter` for in-process Python agent execution.
- Tool Call Proxy with `ToolFaultInjector` (timeouts, HTTP 500, delays).
- `ToolContractValidator` for pre-execution parameter & schema validation.
- `IdempotencyScorer` (`duplicate_side_effect_rate`) detecting duplicate mutations on retry.
- `StateDiffEvaluator` asserting pre/post file and SQLite table mutations.
- `agenteval run --scenario examples/ [--live]`.
- `agenteval replay <run-id> [--tui | --web | --jump-to-fail]`.
- Working sample agent with test scenarios for clean pass, tool fault recovery, idempotency violation, and unverifiable state.

---

## 6. Not Doing (and Why)

- **Not Doing (v0.1): HTTP/MCP/CLI Adapters** — Confined to v0.2 to nail down the core execution trace and fault injection abstractions first on Python callables.
- **Not Doing (v0.1): LLM-as-a-Judge** — Zero-cost deterministic assertions and schema checks first. LLM judges introduce cost and non-determinism; deferred to v0.3.
- **Not Doing (v0.1): Long-Running / Multi-Day Scheduled Agents** — Unnecessary complexity before finite multi-turn reliability is solid; deferred to v1.0.
- **Not Doing (v0.1): Heavy Browser DOM / Video Recording** — Focus on API, MCP, and system-level mutations first; browser agents deferred to v0.5.
- **Not Doing (v0.1): Cloud SaaS / Multi-Tenant Clusters** — Local-first CLI developer experience must be frictionless before adding distributed infra.

---

## 7. Open Questions & Risks

1. **Inspect AI Logging Overhead**: Does Inspect AI's comprehensive transcript logging add unacceptable latency during real-time live streaming?
   * *Mitigation*: Profile early in v0.1; introduce lightweight streaming event-bus mode for live runs.
2. **Agent Framework Diversity**: How cleanly can LangGraph, CrewAI, and raw OpenAI function calling be unified under `CallableAdapter`?
   * *Mitigation*: The adapter interface requires only `(user_input, history) -> List[ToolCall]`. Any callable agent fits this signature.
