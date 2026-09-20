# Engineering Ledger — Index

> Read this file before non-trivial work. Update at end of each substantive session.

**Active phase:** Build → Verify  
**Last updated:** 2026-09-20

## Current focus

**Black-box test intelligence** ([ADR-003](../decisions/ADR-003-black-box-test-intelligence-pipeline.md), [design spec](../design/black-box-test-intelligence-pipeline.md), [AP-003](attack-plans.md#ap-003-black-box-test-intelligence-pipeline-v02v03)) is the north-star product: optimize minimal high-value packs from spec + endpoint, with honest coverage/limitations. **Product entry ([DR-012](decisions.md#active-index)):** requirements-first (+ optional URL), CLI/library now, API next, UI later; scenario YAML harness deprioritized. v0.1 harness remains opt-in **`harness`** profile. AP-002 personas/metrics; AP-003 B0–B9 + North Star entry slices E1–E4.

## Open attack plan

- [AP-003: Black-Box Test Intelligence Pipeline (v0.2 → v0.3)](attack-plans.md#ap-003-black-box-test-intelligence-pipeline-v02v03)
- [AP-002: Agent Contract Protocol, Introspection & Metric Recommender Pipeline (v0.2)](attack-plans.md#ap-002-agent-contract-protocol-introspection--metric-recommender-pipeline-v02)
- [AP-001: Platform Architecture, Pluggable BYOA Harness & Trajectory Assurance Engine](attack-plans.md#ap-001-platform-architecture-pluggable-byoa-harness--trajectory-assurance-engine) (completed)

## Recent sessions

- **2026-09-20 (session 12)**: **E3 HTTP API façade** — `SuiteWorkflow` library service, FastAPI `/v1/suites/preview|init|run`, `agenteval serve`; optional `[api]` extra. 108 tests, ~86% coverage.
- **2026-09-20 (session 11)**: **North Star entry & UI-later** ([DR-012](decisions.md#active-index)) — roadmap: PRD-first bootstrap, API-ready core, web UI deferred; YAML harness low priority.
- **2026-09-20 (session 10)**: **Black-box MVP backbone verified** — `suite init`/`suite run`, sample refund HTTP agent, rule scorer; roadmap records **Allure-class HTML run report** (later, with dashboard)—not JUnit/CSV.
- **2026-09-20 (session 9)**: **Black-Box Test Intelligence — product architecture & incremental roadmap** ([ADR-003](../decisions/ADR-003-black-box-test-intelligence-pipeline.md), [DR-009](decisions.md#active-index), [AP-003](attack-plans.md#ap-003-black-box-test-intelligence-pipeline-v02v03)). Documented full pipeline, dual profiles, slices B0–B9. **Must-have vs later:** v0.2 scoped to HTTP black-box MVP (B0–B2, B4, B5 report-only, B7–B8); v0.3+ gets B3, gap automation, B6/B9, harness/MCP expansion. Docs-only.
- **2026-09-20 (session 8)**: **Dynamic Persona Synthesis, 5-Tier Stack Ranking & LiteLLM Gateway** ([ADR-002](../decisions/ADR-002-dynamic-persona-synthesis-litellm.md), [AP-002](attack-plans.md#ap-002-agent-contract-protocol-introspection--metric-recommender-pipeline-v02)). Eliminated static persona maintenance in favor of on-the-fly dynamic persona discovery powered by LiteLLM (100+ providers). Personas are stack-ranked across 5 operational tiers (Frequent Users, Power Users, Adversaries, Novice, Security Auditors) with `--top-personas` windowing to eliminate evaluation bloat. Delivered local disk caching in `.agenteval/personas/`, updated CLI reporting, formalized ADR-002, and updated product roadmap sequence. 83 passed tests with 90.46% coverage and clean `mypy --strict`.
- **2026-09-20 (session 7)**: **Plane 0 & Archetype Metric Recommender Pipeline Formulated** ([DR-006](decisions.md#active-index), [AP-002](attack-plans.md#ap-002-agent-contract-protocol-introspection--metric-recommender-pipeline-v02)). Formalized the two-group evaluation taxonomy: Group A (Universal Core enforced on 100% of agents) and Group B (Domain-Specific Metrics: Tool, RAG, Code, Support, Swarm). Designed 4-layer Metric Recommender Pipeline: Signal Ingestion → Jev Archetype Classifier → Profile Matrix Resolver → Inspect AI Plan Compiler. Updated ROADMAP.md (9 planes), architecture.md (Section 5), and attack-plans.md with AP-002.
- **2026-09-20 (session 6)**: **v0.1 Core Engine & CLI Implementation Completed (Slices 0 → 7)**. Delivered all 8 vertical slices in full adherence to `CONSTRAINTS.md`:
  - Slice 0: Scaffolding, `pyproject.toml`, Hatchling, Typer, Rich, pytest setup.
  - Slice 1: Core domain models (`ExecutionTrace`, `StepRecord`, `ToolCall`, `ToolResult`, `StateDiff`, `ReliabilityScorecard`, `Verdict`, `FailureClass`).
  - Slice 2: `LocalSandbox` with SHA256 file and SQLite state hashing and deterministic $\Delta S$ computation.
  - Slice 3: `ToolAdapter`, `LocalToolAdapter`, and `ToolFaultInjector` chaos engine (timeouts, HTTP errors, exceptions).
  - Slice 4: `ToolContractValidator`, `StateDiffEvaluator`, and `IdempotencyScorer` (`duplicate_side_effect_rate`).
  - Slice 5: `CallableAdapter` and multi-turn `AgentLoopEngine` with live step callbacks.
  - Slice 6: `TestScenario` schema, `ScenarioLoader` (YAML/JSON), and `VerdictEngine` (`PASS`, `FAIL`, `UNVERIFIABLE`, `ANOMALOUS`).
  - Slice 7: `TraceReplayer` with Rich timeline scrubber & `--jump-to-fail`, interactive Typer CLI (`agenteval run`, `agenteval replay`, `agenteval version`), and working runnable examples (`examples/agents/order_processor.py`, `order_success.yaml`, `order_chaos.yaml`, `unverifiable_claim.yaml`). Full suite passes 37 tests with 92.22% coverage. Transitioning to **Verify** phase.
- **2026-09-20 (session 5)**: **Production Agent Reliability & Chaos Architecture Integrated** ([DR-005](decisions.md#active-index)). Cross-checked AgentEval against Anthropic production agent reliability patterns. Shifted evaluation unit from (Prompt -> Response) to (Agent x Environment x Scenario x FaultPlan). Added Plane 4 (Chaos Engineering & Fault Injection) to ROADMAP.md (8 planes total). Added ToolFaultInjector, ToolContractValidator, IdempotencyScorer (duplicate_side_effect_rate), and AgentLoopMetrics to v0.1 deliverables. Added CrashRecoveryHarness (SIGKILL + resume), ContextPressureInjector, and N-run variance (pass^k) to v0.2. Updated architecture.md and ledger.
- **2026-09-20 (session 4)**: **First-class Real-Time & Interactive Trajectory Replay added** ([DR-004](decisions.md#active-index)). Added requirement for real-time live streaming (`agenteval run --live`), interactive terminal/web time-travel debugger (`agenteval replay <run-id>`), `--jump-to-fail` root-cause fast forward, and side-by-side golden vs failing diff replay. Updated ROADMAP.md (Plane 7, v0.1/v0.2 deliverables), architecture.md, and attack plan AP-001.
- **2026-09-20 (session 3)**: **Foundation strategy decided** — build on Inspect AI (MIT, UK AISI) as eval engine core ([ADR-001](../decisions/ADR-001-build-on-inspect-ai.md)). Researched Jev (TypeSafe AI System One) for Tier 1 high-speed typed judge. Completed academic research survey: compounding errors (TUM 2026), pass^k consistency metrics (τ-bench/Sierra), OAT unsupervised failure attribution (arxiv July 2026), six drift modes (Future AGI), AgentRx constraint-based attribution, TraceElephant full observability. Updated roadmap with tiered judge architecture, research-backed techniques, revised project structure for Inspect AI integration.
- **2026-09-20 (session 2)**: Direction verdict scored **8.5/10** on industry problem-fit. Created comprehensive product roadmap (`docs/ROADMAP.md`) covering v0.1→v1.0 with stack-ranked iterative delivery. Researched NVIDIA OpenShell/NemoClaw/NeMo Guardrails sandbox strategy. Created `CONSTRAINTS.md` with anti-slop quality bar. Built interactive architecture diagram viewer (`docs/design/architecture.html`).
- **2026-09-20 (session 1)**: Initialized AgentEval repository with Craft framework (`DTiapan/craft` v0.2.3, profile: all). Linked remote `https://github.com/DTiapan/AgentEval.git`. Completed state-of-the-art competitive analysis on TestMu AI Assurance, mapped architecture, and initialized ledger.

## Quick links

- [**Idea Refinement One-Pager (Shape Gate)**](../ideas/agent-assurance-platform.md)
- [**Product Roadmap (v0.1→v1.0)**](../ROADMAP.md)
- [Architecture & System Design](../design/architecture.md)
- [**Black-Box Test Intelligence Pipeline**](../design/black-box-test-intelligence-pipeline.md)
- [Interactive Architecture Diagram](../design/architecture.html)
- [Constraints & Quality Floor](../../CONSTRAINTS.md)
- [Phases & Quality Gates](phases.md)
- [Attack plans](attack-plans.md)
- [Decisions](decisions.md)
- [Lessons](lessons.md)
- [ADRs](../decisions/)
