# Attack plans

## Active index

| ID | Title | Status |
|----|-------|--------|
| AP-001 | Platform Architecture, Pluggable BYOA Harness & Trajectory Assurance Engine | completed |
| AP-002 | Agent Contract Protocol, Introspection & Metric Recommender Pipeline (v0.2) | active |

---

## AP-002: Agent Contract Protocol, Introspection & Metric Recommender Pipeline (v0.2)

- **Owner**: Craft / Dev
- **Status**: active
- **Goal**: Implement Plane 0 (Agent Contract & Discovery) and the 4-layer Metric Recommender Pipeline. Standardize Universal Core (Group A) vs Domain-Specific (Group B) metrics, integrate MCP/OpenAPI auto-introspection, formalize `AgentCard` manifests, and introduce Jev-powered dynamic evaluation plan generation (`agenteval plan`).

### Steps
1. [ ] Define Universal Core Metric Invariants (Group A: Loop bounds, thrashing detection, deterministic proof vs unverifiable, token/latency budgets) enforced across 100% of runs.
2. [ ] Define Domain-Specific Metric Profiles (Group B: Tool-Action, RAG Triad, Coding, Enterprise Support, Swarm).
3. [ ] Implement Layer 1 (Signal Ingestion & DNA Extractor): extract tools, schemas, and intent from MCP (`tools/list`), OpenAPI specs, and Python frameworks.
4. [ ] Implement Layer 2 (Jev Archetype Classifier): fast typed Bayesian/probabilistic classifier returning structured `AgentArchetype` and capabilities.
5. [ ] Implement Layer 3 (Metric Policy & Matrix Resolver): merge Group A with resolved Group B profiles into an execution plan.
6. [ ] Implement Layer 4 (Inspect AI Plan Compiler): compile resolved plan into executable Inspect AI tasks with calibrated scorers and fault plans.
7. [ ] Implement CLI integration: `agenteval plan --agent <target>` (preview recommendation) and `agenteval run --auto-plan`.
8. [ ] Implement Declarative `AgentCard` schema (`agenteval.manifest.yaml`) for zero-guess enterprise specification.
9. [ ] Write end-to-end integration tests verifying auto-metric recommendation on Tool-Action, RAG, and Support agents.

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
