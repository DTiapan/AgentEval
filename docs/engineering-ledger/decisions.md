# Tactical decisions (DR)

Decisions reversible without a formal ADR. Promote to `docs/decisions/` when reversal cost is high.

## Active index

| ID | Title | Status | Date |
|----|-------|--------|------|
| ADR-001 | [Build on Inspect AI as Evaluation Engine Foundation](../decisions/ADR-001-build-on-inspect-ai.md) | Accepted | 2026-09-20 |
| ADR-002 | [Dynamic Persona Synthesis, Stack-Ranking & Multi-Vendor LiteLLM Gateway](../decisions/ADR-002-dynamic-persona-synthesis-litellm.md) | Accepted | 2026-09-20 |
| DR-001 | Adopt Jev (TypeSafe AI System One) as Tier 1 judge — 40–200x faster than LLM-as-a-Judge for typed classification scoring. Confidence gating pattern: escalate to Tier 2 LLM when Jev confidence < 0.7. Ships in v0.3. | Accepted | 2026-09-20 |
| DR-002 | Adopt pass^k (reliability floor) alongside pass@k (capability ceiling) as dual metrics. Research shows 60% pass@1 agents can drop to 25% pass^3. Ships in v0.2. | Accepted | 2026-09-20 |
| DR-003 | Implement FirstUnrecoverableStepScorer for compounding error root-cause attribution (inspired by AgentRx). Ships in v0.2. | Accepted | 2026-09-20 |
| DR-004 | Implement Real-Time & Interactive Trajectory Replay (`agenteval replay` & live streaming) as a core capability. Enables step-by-step playback, time-travel debugging, jump-to-failure spotlighting, and side-by-side golden vs failing diff. Ships starting in v0.1. | Accepted | 2026-09-20 |
| DR-005 | Adopt 8-Plane Agent Reliability & Chaos Engineering Architecture. Extends evaluation unit from (Prompt -> Response) to (Agent x Environment x Scenario x FaultPlan). Incorporates ToolFaultInjector, IdempotencyScorer (duplicate_side_effect_rate), and Process Crash/Recovery Harness. | Accepted | 2026-09-20 |
| DR-006 | Adopt Plane 0 (Agent Contract, Discovery & Requirement Engineering) and Archetype-Driven Metric Segregation with Jev Metric Router. Formalizes PRD-to-Scenario compilation, MCP/OpenAPI auto-introspection, and specialized profiles (Tool, RAG, Code, Support, Swarm). | Accepted | 2026-09-20 |
| DR-007 | Ingest Agency-Agents Persona Corpus, Support Live HTTP BYOA Endpoints, and Integrate TypeSafe AI / Jev Typed Classification with Air-Gapped Fallback. Eliminates metric selection friction by deriving evaluation suites, invariants, and chaos fault plans directly from persona/PRD specs. | Accepted | 2026-09-20 |
| DR-008 | On-the-Fly Dynamic Persona Synthesis, Jev Selection & Local Disk Caching. Maintain a 35+ candidate persona catalog across Engineering, SRE, Security, Data, and Support. Select top matching personas with sub-50ms typed Jev inference, synthesize complete persona specifications on the fly, and persist in `.agenteval/personas/{slug}.md` for zero-latency reuse. | Accepted | 2026-09-20 |
| DR-009 | **Black-box-first evaluation** for enterprise customers: default **`blackbox`** execution profile (endpoint-observable evidence only). Retain v0.1 **`harness`** profile (sandbox ΔS, fault injection) as opt-in for in-process BYOA. Product pipeline = understand → hypothesize → candidate pool → risk → **set-cover optimization** → execute pack → coverage → gap-targeted re-test. Formalized in [ADR-003](../decisions/ADR-003-black-box-test-intelligence-pipeline.md); implemented via [AP-003](attack-plans.md#ap-003-black-box-test-intelligence-pipeline-v02v03). | Accepted | 2026-09-20 |
| DR-010 | **Frozen regression suite:** On first bootstrap (requirements + endpoint), generate the optimized test pack **once** and persist under `.agenteval/suites/<agent_id>/` as the versioned source of truth. Subsequent runs **load and execute** that suite for regression (“what broke?”)—**no implicit regeneration** on `run` or CI. New generation only via explicit `suite regenerate` (new version) or append-only extend (gap loop). Spec: [Frozen regression suite](../design/black-box-test-intelligence-pipeline.md#frozen-regression-suite-generate-once-run-many). | Accepted | 2026-09-20 |
| DR-012 | **Minimum-friction entry & UI-later delivery:** Primary onboarding = **functional requirements** (PRD/upload text) + optional **HTTP endpoint**; AgentEval derives personas, test pack, and runs—users do not author scenario YAML or AgentCard by default. **CLI + library services first**, then **HTTP API** exposing the same Pydantic contracts; **web UI** (upload requirements, generate, execute, navigate results) deferred to v0.4+ but core modules must stay UI/API-ready. Harness scenario YAML remains **low-priority / advanced** framework path. | Accepted | 2026-09-20 |
| DR-011 | **Suite pruning on capability removal:** When a capability is **removed** from requirements/manifest, drop (archive) regression tests **linked to that capability** on the next explicit `suite sync` / `regenerate` / `migrate` after spec update—never on plain `suite run`. Changelog records removed test IDs. Added capabilities use extend/regen append only. Spec: [Pruning when functionality is removed](../design/black-box-test-intelligence-pipeline.md#pruning-when-functionality-is-removed). | Accepted | 2026-09-20 |
| ADR-003 | [Black-Box Test Intelligence Pipeline & Dual Execution Profiles](../decisions/ADR-003-black-box-test-intelligence-pipeline.md) | Accepted | 2026-09-20 |


---

<!-- New entries above ## Archive -->

## Archive

<!-- Superseded decisions moved here with Superseded-by link -->
