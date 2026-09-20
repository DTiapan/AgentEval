# Engineering Ledger — Index

> Read this file before non-trivial work. Update at end of each substantive session.

**Active phase:** Build → Verify  
**Last updated:** 2026-09-20

## Current focus

Bootstrapping AgentEval — an enterprise-grade, trajectory-first AI Agent Assurance and Quality Engineering platform. Completed v0.1 Core Engine implementation (Slices 0 through 7) with 37 tests (92.22% coverage), interactive CLI runner, sealed local sandbox, tool fault injector, idempotency scoring, and timeline scrubber replayer.

## Open attack plan

- [AP-002: Agent Contract Protocol, Introspection & Metric Recommender Pipeline (v0.2)](attack-plans.md#ap-002-agent-contract-protocol-introspection--metric-recommender-pipeline-v02)
- [AP-001: Platform Architecture, Pluggable BYOA Harness & Trajectory Assurance Engine](attack-plans.md#ap-001-platform-architecture-pluggable-byoa-harness--trajectory-assurance-engine) (completed)

## Recent sessions

- **2026-09-20 (session 8)**: **Dynamic On-the-Fly Persona Synthesis & Jev Selector Integrated** ([AP-002](attack-plans.md#ap-002-agent-contract-protocol-introspection--metric-recommender-pipeline-v02)). Implemented zero-friction persona synthesis and caching pipeline: 35+ curated candidate persona taxonomy (`agenteval/personas/registry.py`), sub-50ms typed Jev persona selector (`agenteval/recommender/persona_selector.py`), markdown synthesizer with local file cache in `.agenteval/personas/` (`agenteval/personas/synthesizer.py`), and CLI auto-selection in `agenteval plan --endpoint ...` with `[CACHED]` vs `[SYNTHESIZED]` diagnostic badges. 80 passed tests with 90.56% coverage and strict mypy/ruff validation.
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
- [Interactive Architecture Diagram](../design/architecture.html)
- [Constraints & Quality Floor](../../CONSTRAINTS.md)
- [Phases & Quality Gates](phases.md)
- [Attack plans](attack-plans.md)
- [Decisions](decisions.md)
- [Lessons](lessons.md)
- [ADRs](../decisions/)
