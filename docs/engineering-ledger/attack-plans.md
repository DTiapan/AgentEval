# Attack plans

## Active index

| ID | Title | Status |
|----|-------|--------|
| AP-001 | Platform Architecture, Pluggable BYOA Harness & Trajectory Assurance Engine | completed |
| AP-002 | Agent Contract Protocol, Introspection & Metric Recommender Pipeline (v0.2) | active |
| AP-003 | Black-Box Test Intelligence Pipeline (v0.2 → v0.3) | active |

---

## AP-003: Black-Box Test Intelligence Pipeline (v0.2 → v0.3)

- **Owner**: Craft / Dev
- **Status**: active
- **Goal**: Implement the north-star pipeline from [ADR-003](../decisions/ADR-003-black-box-test-intelligence-pipeline.md) and [black-box-test-intelligence-pipeline.md](../design/black-box-test-intelligence-pipeline.md): understand agent from spec + endpoint only, generate a **large candidate pool**, **optimize** to a minimal high-value pack (mandatory security floor + set cover), execute in **`blackbox`** profile, report multi-axis **coverage** and **gaps**, and state **limitations** honestly. Preserve v0.1 **harness** profile without conflating evidence models.

### Phase A — Must-have (v0.2 Black-Box MVP)

1. [ ] **B0** — Planning models: `AgentTestModel` (DECLARED / INFERRED), `CandidateTest`, `CoverageTag`, `TestPack`, `CoverageReport`, `LimitationsReport`.
2. [ ] **B1** — Rule-based failure hypotheses (templates); unit tests without LLM. Spec: [Test generation strategy § B1](../design/black-box-test-intelligence-pipeline.md#b1--rule-based-failure-templates-mvp).
3. [ ] **B2** — Bounded candidate pool (persona × capability × hypothesis); JSON artifact; **never auto-run full pool**. Spec: [Test generation strategy](../design/black-box-test-intelligence-pipeline.md#test-generation-strategy).
4. [ ] **B4** — Optimizer: mandatory security floor + greedy set cover; efficiency stats.
5. [ ] **B5 (MVP)** — Post-run coverage map + critical uncovered list (**report only**).
6. [ ] **B7** — `blackbox` + `ObservationBundle` on **HTTP** `HTTPAdapter` only.
7. [ ] **B8 (MVP)** — `agenteval plan` (pool vs pack, limitations); **`suite init`** (bootstrap + persist); **`suite run`** (regression, load frozen pack, diff — [DR-010](decisions.md#active-index)).

**Phase A first code increment:** B0 + B4 + B5 (MVP) with fixture pools → then B1 → B2 → B7 → B8 (include suite persistence in B8).

**Regression contract:** `suite run` must never call generation/optimizer unless user passed an explicit regenerate/extend flag.

**Spec drift ([DR-011](decisions.md#active-index)):** Each test stores `capability_id` / coverage tags. On `suite sync` after spec update: **remove** tests for dropped capabilities (archive + changelog); **extend** for new capabilities only—no full silent regen.

### Phase B — Later (v0.3+)

8. [ ] **B3** — Full configurable risk scorer (six dimensions).
9. [ ] **B5 (full)** — Gap detector → targeted candidates → incremental re-optimize.
10. [ ] **B6** — Metric applicability on `MetricRouter` + pack.
11. [ ] **B8 (full)** — Risk map, metric rationale, efficiency dashboards in CLI/reports.
12. [ ] **B9** — Inspect AI plan compiler (AP-002 step 6).
13. [ ] **Optional** — LLM hypothesis expansion; HYPOTHESIZED provenance layer; MCP/CLI black-box ingress.

### References

- [ROADMAP — Black-Box Incremental Delivery](../ROADMAP.md#black-box-test-intelligence-incremental-delivery)
- [DR-009](decisions.md#active-index) — Black-box default, harness opt-in

---

## AP-002: Agent Contract Protocol, Introspection & Metric Recommender Pipeline (v0.2)

- **Owner**: Craft / Dev
- **Status**: active
- **Goal**: Implement Plane 0 (Agent Contract & Discovery) and the 4-layer Metric Recommender Pipeline. Standardize Universal Core (Group A) vs Domain-Specific (Group B) metrics, integrate MCP/OpenAPI auto-introspection, formalize `AgentCard` manifests, and introduce Jev-powered dynamic evaluation plan generation (`agenteval plan`).

### Steps
1. [x] Define Universal Core Metric Invariants (Group A: Loop bounds, thrashing detection, deterministic proof vs unverifiable, token/latency budgets) enforced across 100% of runs.
2. [x] Define Domain-Specific Metric Profiles (Group B: Tool-Action, RAG Triad, Coding, Enterprise Support, Swarm).
3. [x] Implement Layer 1 (Signal Ingestion & DNA Extractor): extract tools, schemas, and intent from MCP (`tools/list`), OpenAPI specs, and Python frameworks.
4. [x] Implement Layer 2 (Jev Archetype Classifier): fast typed Bayesian/probabilistic classifier returning structured `AgentArchetype` and capabilities.
5. [x] Implement Layer 3 (Metric Policy & Matrix Resolver): merge Group A with resolved Group B profiles into an execution plan.
6. [ ] Implement Layer 4 (Inspect AI Plan Compiler): compile resolved plan into executable Inspect AI tasks with calibrated scorers and fault plans.
7. [x] Implement CLI integration: `agenteval plan --agent <target>` (preview recommendation) and `agenteval plan --manifest <path>`.
8. [x] Implement Declarative `AgentCard` schema (`agenteval.manifest.yaml`) for zero-guess enterprise specification.
9. [x] Write end-to-end integration tests verifying auto-metric recommendation on Tool-Action, RAG, and Support agents.
10. [x] Implement Agency-Agents persona parser & benchmark corpus (`agenteval/introspect/persona.py`, `examples/agency_personas/`).
11. [x] Implement Live BYOA `HTTPAdapter` connecting external REST/chat agent endpoints (`agenteval/adapters/http.py`).
12. [x] Implement TypeSafe AI / Jev Classifier client (`agenteval/recommender/jev_client.py`) with air-gapped local fallback.
13. [x] Implement Spec-to-Scenario Compiler (`agenteval/scenarios/compiler.py`) auto-deriving test scenarios from personas & PRDs.
14. [x] Update CLI `plan` and `run` to support `--persona`, `--endpoint`, and `--prd`.
15. [x] Implement dynamic on-the-go persona synthesis (`agenteval/personas/synthesizer.py`), Jev persona selector (`agenteval/recommender/persona_selector.py`), 35+ curated persona taxonomy (`agenteval/personas/registry.py`), and local disk caching (`.agenteval/personas/`).
16. [x] Adopt LiteLLM multi-vendor gateway (`agenteval/personas/dynamic.py`), 5-tier operational stack ranking (`--top-personas`), and formalize ADR-002 (`docs/decisions/ADR-002-dynamic-persona-synthesis-litellm.md`).

---

## AP-001: Platform Architecture, Pluggable BYOA Harness & Trajectory Assurance Engine

- **Owner**: Craft / Dev
- **Status**: active
- **Goal**: Establish core pluggable agent evaluation platform with universal agent adapters (HTTP, MCP, CLI, Python callable), trajectory-first verification engine, sandbox side-effect assertions, telemetry collector, and CLI test runner.

### Steps
1. [x] Adopt Craft framework in repository (`craft.project.yaml`, `AGENTS.md`, 52 domain skills installed in `.agents/skills`).
2. [x] Connect local git repository with remote `https://github.com/DTiapan/AgentEval.git`.
3. [x] Research TestMu AI Assurance, competitive landscape, and define implementation blueprint.
4. [x] Scaffold core Python package (`agenteval/core`, `agenteval/adapters`, `agenteval/evaluators`, `agenteval/sandbox`, `agenteval/replay`, `agenteval/faults`, `agenteval/engine`, `agenteval/cli`).
5. [x] Implement Universal Agent Adapters (`CallableAdapter`, `ToolAdapter`, `LocalToolAdapter`).
6. [x] Implement Trajectory & Tool Call Evaluators (`ToolContractValidator`, `StateDiffEvaluator`, `IdempotencyScorer`).
7. [x] Implement Real-Time Live Streamer & Interactive Trajectory Replay (`agenteval run --live`, `agenteval replay <trace.json>`, step scrubbing, `--jump-to-fail`).
8. [ ] Implement OpenTelemetry / OpenInference tracing and metrics exporter (v0.2).
9. [ ] Implement Self-evolving Golden Dataset synthesizer & production log miner (v0.3).
10. [x] Implement CLI and CI/CD quality gate reporter (`agenteval run --scenario <path>`, exit codes for PASS vs FAIL/UNVERIFIABLE).
11. [ ] Build high-impact modern developer dashboard with visual scrubber, flame graphs, and dataset curation (v0.4).

---

## Archive

<!-- Move cancelled/superseded AP summaries here -->
