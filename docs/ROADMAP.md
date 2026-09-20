# AgentEval — Product Roadmap & Execution Guide

> **North Star**: One tool to attack all planes of AI agent assurance — evaluation, trajectory verification, tool-call validation, sandbox side-effect proof, golden dataset curation, observability, and CI/CD quality gates.
>
> **Delivery Philosophy**: Every version is a **working, shippable product**. No version is a "foundation only" release. Each version solves a real problem end-to-end, and the next version expands the blast radius.

---

## The Burning Problem We Solve

Every team shipping AI agents today is flying blind:
- They can't **prove** their agent actually did what it claims.
- They can't **catch regressions** before production.
- They can't distinguish **"it worked"** from **"it got lucky."**
- They have **zero visibility** into the reasoning trajectory — only the final output.
- Their "testing" is running the agent a few times and eyeballing the result (**vibes-based QA**).

AgentEval gives them **sealed, deterministic proof — or honestly tells them when proof is impossible.**

### Market Validation (2026)
- Only **~16%** of enterprise agent projects qualify as true autonomous agents; **quality is the #1 barrier to production** (Menlo Ventures / LangChain State of AI Agents 2026).
- AI Agent Audit & Assurance market: **~$0.6B in 2026 → projected $23B by 2036** (FactMR).
- **EU AI Act** (August 2026) legally requires evidence-based assurance for autonomous agents in regulated sectors.
- EY, Deloitte, NVIDIA (NemoClaw), and TestMu AI all launched agent assurance products in 2026 — the big money confirms the pain.

### Our Moat (What Nobody Else Does)
| Differentiator | Why It Matters |
|---|---|
| **Sealed Execution Evidence** | We assert *actual environment mutations* (files created, DB rows committed, API calls made) — never trust an agent's self-report. |
| **Explicit `UNVERIFIABLE` Verdict** | Every other tool silently passes or guesses. We refuse to claim something we can't prove. |
| **Auto-Mining Production Failures → Golden Datasets** | Turns the platform into a flywheel: production incidents automatically become regression tests. |
| **Deterministic First, LLM Judge Second** | Cheap/reliable assertions fire first ($0 cost, 100% reproducible). LLM judge is opt-in for subjective criteria only. |
| **True BYOA (Bring Your Own Agent)** | Any agent — HTTP, MCP, Python callable, CLI binary — plugs in with zero code changes. We own everything downstream. |

---

## Competitive Landscape & Positioning

### Direct Competitors & Adjacent Players

| Player | What They Do | Their Strength | Their Gap (Our Opportunity) |
|---|---|---|---|
| **DeepEval** | Pytest-style LLM evaluation library | Great DX, 50+ metrics, CI/CD native | Output-string focused. No trajectory verification, no side-effect proof, no sandbox execution. |
| **LangSmith** | LangChain's tracing + evaluation platform | Deep LangGraph integration, trajectory visualization | Locked to LangChain ecosystem. Passive monitoring — doesn't actively execute and assert. |
| **Arize Phoenix** | OTel-based LLM observability | Strong ML infra team adoption, open-source tracing | Observability only. Doesn't run evaluations, doesn't generate golden datasets, doesn't gate CI. |
| **Braintrust** | Framework-neutral eval platform | Enterprise portability, clean API | No sandbox execution, no environmental side-effect verification. |
| **Maxim AI** | Multi-turn agent simulation & QA | Polished UI, persona-based testing | Cloud SaaS lock-in. No local-first CLI, no deterministic state diffing. |
| **TestMu AI (formerly LambdaTest)** | AI Assurance + Kane CLI + Agentic Testing | Requirement-linked lifecycle, browser automation | Proprietary cloud platform. Heavy enterprise pricing. No open-source core. |
| **NVIDIA NemoClaw / OpenShell** | Agent runtime security & sandbox isolation | Kernel-level Landlock/seccomp isolation, privacy routing | Security-focused, not evaluation-focused. Doesn't score trajectories or generate test suites. **Complementary to us.** |
| **NeMo Guardrails** | Conversational safety rails (Colang policies) | Jailbreak detection, topical boundaries, hallucination checks | Guards *what an agent says*, not *what an agent did*. Orthogonal to our trajectory + side-effect verification. |

### Where AgentEval Sits

```
                    ┌─────────────────────────────────────────────────────┐
                    │              AGENT LIFECYCLE                        │
                    │                                                     │
 ┌──────────┐  ┌───┴──────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
 │  BUILD   │→ │  TEST    │→ │  DEPLOY  │→ │ MONITOR  │→ │  LEARN   │  │
 │          │  │          │  │          │  │          │  │          │  │
 │ Frameworks│ │ AgentEval│  │ NemoClaw │  │ Phoenix  │  │ AgentEval│  │
 │ LangGraph│  │ DeepEval │  │ OpenShell│  │ LangSmith│  │ (mining) │  │
 │ CrewAI   │  │ Braintrust│ │ E2B      │  │ AgentOps │  │          │  │
 └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
                    │                                                     │
                    │  AgentEval spans TEST + MONITOR + LEARN            │
                    │  (the full assurance lifecycle)                     │
                    └─────────────────────────────────────────────────────┘
```

---

## Architecture Overview (All Planes)

AgentEval attacks **six planes** of agent assurance through a single unified platform:

| Plane | What It Covers | Key Components |
|---|---|---|
| **1. Pluggable Agent Interface (BYOA)** | Connect any agent with zero code changes | `HTTPAdapter`, `MCPAdapter`, `CallableAdapter`, `CLIAdapter` |
| **2. Trajectory & Tool-Call Verification** | Validate every step of the reasoning chain | `ToolSchemaEvaluator`, `StepEfficiencyEvaluator`, Loop/Thrashing Guard |
| **3. Sandbox & Side-Effect Proof** | Execute tool calls in isolation, capture state diffs | Ephemeral sandbox (local → OpenShell/Docker), `StateDiffEvaluator` |
| **4. Hybrid Evaluation Engine** | Score with deterministic checks + optional LLM/Jev judge | Deterministic assertions ($0), Jev System One typed scoring ($0.04/M tokens), calibrated G-Eval/CoT (opt-in) |
| **5. Continuous Golden Dataset Loop** | Auto-mine failures into regression suites | Production trace ingestion, failure clustering, adversarial synthesis |
| **6. Observability & CI/CD Quality Gate** | Telemetry, reporting, and PR gating | OTel/OpenInference, flame graphs, CLI exit codes, markdown reports |

### Verdict Taxonomy (Core Innovation)
Every evaluation produces one of four explicit verdicts:

| Verdict | Meaning | When It Fires |
|---|---|---|
| `PASS` | All assertions met with sealed evidence | Deterministic checks + state diffs + (optional) LLM judge all agree |
| `FAIL` | Explicit logic, safety, or assertion failure | Wrong tool called, schema violation, state diff mismatch, safety breach |
| `UNVERIFIABLE` | Agent claimed completion but proof is missing | Side-effect cannot be observed (e.g., external API with no mock, no audit trail) |
| `ANOMALOUS` | Task completed but with concerning signals | Excessive token usage, loop/backtrack detected, extreme latency |

---

## Foundation Strategy: Build on Inspect AI

> **Decision**: [ADR-001](../decisions/ADR-001-build-on-inspect-ai.md) — Use UK AISI's `inspect_ai` (MIT license) as the evaluation engine core. Build our unique IP as Inspect extensions. Import DeepEval metrics as optional complements.

### Why Inspect AI
- **MIT-licensed**, government-backed (UK AI Safety Institute), actively maintained
- Composable `@task` / `@solver` / `@scorer` / `@tool` primitives — our extensions are standard Python
- Docker/K8s sandbox infrastructure built-in (extensible to OpenShell)
- Full transcript/trajectory capture and log system
- `inspect view` web viewer + VS Code extension for trajectory visualization
- 200+ pre-built benchmarks via `inspect_evals` (GAIA, SWE-bench, CyBench, BFCL)

### Architecture Stack

```
┌─────────────────────────────────────────────────────┐
│              AgentEval (Our Platform)                │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ BYOA Adapter Layer (our IP)                  │   │
│  │ Wraps any agent as an Inspect AI Solver      │   │
│  └──────────────────────┬──────────────────────┘   │
│                         │                           │
│  ┌──────────────────────▼──────────────────────┐   │
│  │ Inspect AI Core Engine (reused)              │   │
│  │ @task, @solver, @scorer, sandbox, transcript │   │
│  └──────────────────────┬──────────────────────┘   │
│                         │                           │
│  ┌──────────────────────▼──────────────────────┐   │
│  │ AgentEval Custom Scorers (our IP)            │   │
│  │ • StateDiffScorer (sealed evidence)          │   │
│  │ • UnverifiableScorer (verdict taxonomy)      │   │
│  │ • SealedEvidenceScorer (env state proof)     │   │
│  │ • JevScorer (System One typed decisions)     │   │
│  │ + DeepEval metrics (optional import)         │   │
│  │   • ToolCorrectnessMetric                    │   │
│  │   • AgentLoopDetectionMetric                 │   │
│  │   • StepEfficiencyMetric                     │   │
│  └──────────────────────┬──────────────────────┘   │
│                         │                           │
│  ┌──────────────────────▼──────────────────────┐   │
│  │ AgentEval Extensions (our IP)                │   │
│  │ • OpenShell sandbox backend                  │   │
│  │ • Production trace → dataset miner           │   │
│  │ • CI/CD quality gate & PR bot                │   │
│  │ • Adversarial scenario generator             │   │
│  │ • Drift detection (6 drift modes)            │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### What We Reuse vs. What We Build

| Layer | Reuse | Build (Our IP) |
|---|---|---|
| **Task Runner** | Inspect AI `@task` + `inspect eval` CLI | Our `agenteval run` wrapper with Rich output |
| **Agent Execution** | Inspect AI `@solver` primitive | BYOA Adapter Layer (HTTP, MCP, CLI, Callable → Solver) |
| **Evaluation** | Inspect AI `@scorer` + DeepEval metrics (opt-in) | `StateDiffScorer`, `SealedEvidenceScorer`, `UnverifiableScorer`, `JevScorer` |
| **Sandbox** | Inspect AI Docker sandbox | OpenShell backend plugin, local tempfile sandbox |
| **Transcript** | Inspect AI log system | Production trace → Inspect dataset converter |
| **Visualization** | `inspect view` web viewer | Custom dashboard (v0.5) |
| **Benchmarks** | 200+ via `inspect_evals` | Custom benchmark integration |

---

## Evaluation Techniques & Research Foundation

Our evaluator design is grounded in the latest research. This section documents the techniques we adopt, their academic backing, and which version introduces them.

### Tiered Judge Architecture

We implement a **three-tier judge architecture** that optimizes for cost, speed, and accuracy:

| Tier | Judge Type | Cost | Latency | When to Use | Version |
|---|---|---|---|---|---|
| **Tier 0** | Deterministic code checks (schema validation, state diffs, regex) | $0 | <1ms | Always — first line of defense | v0.1 |
| **Tier 1** | **Jev (TypeSafe AI System One)** — typed classification, scoring, boolean decisions | ~$0.04/M tokens | 70–500ms | High-volume structured decisions: tool correctness, policy compliance, safety classification | v0.3 |
| **Tier 2** | **LLM-as-a-Judge** (GPT-4o, Claude, Gemini) — Chain-of-Thought reasoning | ~$5–15/M tokens | 1–5s | Subjective criteria: helpfulness, reasoning quality, nuanced policy adherence | v0.3 |

### Jev (TypeSafe AI System One) Integration

**What**: Jev is a "System One" model by TypeSafe AI (released September 2026) optimized for fast, typed decision-making. It does not generate prose — it evaluates input against predefined questions and returns structured, probabilistic verdicts in a single parallel pass.

**Why it matters for AgentEval**: Traditional LLM-as-a-Judge is expensive ($5–15/M tokens) and slow (1–5s per eval). Jev is **40–200x faster** and **40–400x cheaper** while matching human-level accuracy on narrow classification tasks. This is perfect for high-volume, production-grade scoring.

**Three Jev Primitives we use**:

| Primitive | AgentEval Use Case | Example |
|---|---|---|
| **Choice** | Tool selection correctness — "Did the agent pick the right tool from this list?" | `choice(options=["search_db", "call_api", "write_file"], state=tool_call)` |
| **Score** | Step quality rating — "Rate this reasoning step 1–5 on the rubric" | `score(rubric="1=irrelevant, 5=optimal", state=step_context)` |
| **Noul (Boolean)** | Binary safety checks — "Was a destructive action performed?" "Did the agent violate the policy?" | `noul(question="Did the agent access unauthorized data?", state=trajectory)` |

**Confidence Gating Pattern**: When Jev's confidence is below a threshold (e.g., 0.7), automatically escalate to Tier 2 (full LLM judge). This gives us the speed of Jev for clear-cut cases and the reasoning depth of GPT-4o for ambiguous ones.

### Research-Backed Evaluation Techniques

#### 1. Compounding Error Detection
**Source**: *"A Survey for LLM Agent Trajectory Analysis: From Failure Attribution to Enhancement"* (TUM, July 2026)

A 1% error at an early step can snowball into catastrophic downstream failure. Our evaluators implement **step-level attribution** to pinpoint the specific tool call or decision that broke the chain, rather than just labeling the whole run as "failed."

**Implementation**: `FirstUnrecoverableStepScorer` — walks the trajectory backward from the failure point, testing each step's constraints to find the earliest violation that made recovery impossible.

#### 2. pass^k Consistency Metric
**Source**: τ-bench (Sierra Research), Anthropic reliability research

Unlike `pass@k` (at least one of k attempts succeeds — optimistic), `pass^k` measures whether the agent succeeds on **all** k attempts — the reliability floor.

| Metric | Formula | What It Measures | Our Use |
|---|---|---|---|
| `pass@k` | P(≥1 success in k tries) | Capability ceiling | Benchmark comparison |
| `pass^k` | P(all k succeed) = (c/n)^k | Reliability floor | Production readiness gate |

**Why it matters**: Research shows agents with 60% `pass@1` can drop to **25% `pass^3`** — exposing massive reliability gaps invisible to single-shot testing. We report both metrics.

#### 3. OAT (One-class Agent Tracing) — Unsupervised Failure Attribution
**Source**: *"Tracing Agentic Failure from the Flow of Success"* (arxiv, July 2026)

OAT trains only on **successful trajectories** using Neural Controlled Differential Equations (NCDEs), then detects anomalous steps in failure trajectories by comparing against the learned "normal flow." It's 200–5,000x faster than prompting-based baselines.

**Our adoption**: Phase v0.4+ — once we have enough successful trajectory data from the golden dataset, implement OAT-style anomaly scoring as an unsupervised evaluator that requires zero manual annotation.

#### 4. Six Drift Modes (Trace-Eval Gap)
**Source**: Future AGI research, industry consensus 2026

Static evaluation datasets go stale as production evolves. Six drift modes explain why agents pass offline evals but fail in production:

| Drift Mode | What Changes | Detection Strategy | Version |
|---|---|---|---|
| **Input-Distribution** | User queries shift from golden set distribution | Embedding distance monitoring | v0.4 |
| **Prompt-Template** | System prompt or few-shot examples updated | Hash-based version tracking | v0.3 |
| **Retrieval-Corpus** | Knowledge base grows, rotates, or is re-embedded | Retrieval quality regression tests | v0.4 |
| **Tool-Definition** | Agent's toolset changes (added/renamed/removed tools) | Schema diff against scenario expectations | v0.2 |
| **Judge-Calibration** | LLM judge model updates or rubric evolves | Periodic calibration against human labels | v0.3 |
| **Agent-Step Compounding** | Error accumulation across multi-step trajectories | `FirstUnrecoverableStepScorer` + `pass^k` | v0.2 |

#### 5. AgentRx Constraint-Based Attribution
**Source**: AgentRx framework (2026)

Synthesizes executable constraints from tool schemas and policies, then evaluates each trajectory step against them. Produces an auditable log of constraint violations with a grounded failure taxonomy. Improves step-level localization by ~75% over standard prompting.

**Our adoption**: The `SealedEvidenceScorer` already implements a version of this — we assert executable constraints (file exists, DB row matches, API response captured) rather than asking an LLM "did it work?"

#### 6. TraceElephant Full Observability
**Source**: TraceElephant benchmark (2026)

Demonstrated that attribution accuracy improves by **76%** when using full traces (inputs + reasoning + tool results) vs. partial observations (output-only). Validates our architectural decision to capture the complete trajectory, not just the final answer.

### Benchmark Integration Strategy

| Benchmark | Domain | Integration | Version |
|---|---|---|---|
| **GAIA** | General AI Assistant tasks | Via `inspect_evals` (free) | v0.1 |
| **SWE-bench Verified** | Software engineering agent tasks | Via `inspect_evals` (free) | v0.1 |
| **BFCL** (Berkeley Function Calling) | Tool-calling accuracy | Via `inspect_evals` (free) | v0.1 |
| **CyBench** | Cybersecurity agent tasks | Via `inspect_evals` (free) | v0.2 |
| **τ-bench** | Customer service (Retail, Airline, Banking) | Custom integration with `pass^k` | v0.2 |
| **ClawBench** | Real-world web agent tasks | Custom integration with trace evidence | v0.3 |

---

## Version Roadmap

### Sandbox Strategy Across Versions

| Version | Sandbox Approach | Rationale |
|---|---|---|
| **v0.1** | Inspect AI local sandbox + captured function call records | Leverages Inspect's built-in isolation |
| **v0.2** | + Mock HTTP server (local proxy for API call capture) | Enables REST agent tool verification |
| **v0.3** | + Optional NVIDIA OpenShell integration + Inspect Docker sandbox | Kernel-level isolation for destructive tool calls |
| **v0.4+** | + E2B / Modal as pluggable sandbox backends | Enterprise-grade, cloud-native isolation |

---

## v0.1 — "Prove the Thesis" (Working CLI)

> **Goal**: A developer can run `agenteval run` against their Python agent, see trajectory traces, get deterministic verdicts (`PASS` / `FAIL` / `UNVERIFIABLE`), and trust the result.
>
> **User Story**: *"I built a LangGraph agent that searches documents and answers questions. I want to know if it's calling the right tools with the right parameters, and whether it actually wrote the file it claims to have written."*

### What Ships
| Component | Scope | Files |
|---|---|---|
| **Core Domain Models** | `Trajectory`, `Step`, `ToolCall`, `Observation`, `EvaluationResult`, `Verdict`, `TestScenario` | `agenteval/core/models.py` |
| **CallableAdapter** | In-process Python agent execution (LangGraph, CrewAI, any callable) | `agenteval/adapters/callable.py`, `agenteval/adapters/base.py` |
| **Scenario Loader** | YAML/JSON test scenario definitions with expected outcomes | `agenteval/scenarios/loader.py`, `agenteval/scenarios/schema.py` |
| **Basic Sandbox** | Temp directory + SQLite + function call capture | `agenteval/sandbox/local.py` |
| **ToolSchemaEvaluator** | Validates tool names and arguments against JSON schemas | `agenteval/evaluators/tool_schema.py` |
| **StateDiffEvaluator** | Compares pre/post environment state (files, DB rows) | `agenteval/evaluators/state_diff.py` |
| **Verdict Engine** | Aggregates evaluator scores → `PASS` / `FAIL` / `UNVERIFIABLE` | `agenteval/engine/verdict.py` |
| **CLI Runner** | `agenteval run --scenario tests/` with table output | `agenteval/cli/main.py` |
| **Example Agent + Test Suite** | A sample agent with a sample test scenario demonstrating the full loop | `examples/` |

### What Doesn't Ship (Yet)
- HTTP, MCP, CLI adapters
- LLM-as-a-Judge evaluator
- `ANOMALOUS` verdict (needs efficiency baselines)
- Web dashboard
- Production trace ingestion
- Adversarial dataset generation
- PR bot / CI reporter

### Definition of Done
- [ ] `pip install -e .` works
- [ ] `agenteval run --scenario examples/scenarios/` executes the sample agent, captures trajectory, asserts tool calls and state diffs, prints verdicts
- [ ] At least one `PASS`, one `FAIL`, and one `UNVERIFIABLE` example scenario
- [ ] `pytest tests/` passes with ≥85% coverage on core modules
- [ ] README with quickstart that a developer can follow in < 5 minutes

### Tech Stack
| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11+ | Native to AI/ML ecosystem, every agent framework is Python |
| **Eval Engine** | **Inspect AI** (MIT) | UK AISI framework — task runner, sandbox, transcript, 200+ benchmarks ([ADR-001](../decisions/ADR-001-build-on-inspect-ai.md)) |
| Type System | Pydantic v2 + `mypy --strict` | Domain model validation + strict typing |
| CLI | Typer + Rich (wrapping `inspect eval`) | Beautiful terminal output, extends Inspect's CLI |
| Test Runner | pytest | Industry standard, familiar DX |
| Linting | Ruff | Fast, replaces flake8+isort+black in one tool |
| Packaging | pyproject.toml + Hatch | Modern Python packaging |
| Optional: Metrics | DeepEval (opt-in import) | `ToolCorrectnessMetric`, `AgentLoopDetectionMetric`, `StepEfficiencyMetric` |
| Optional: Fast Judge | Jev / TypeSafe AI (opt-in) | System One typed decisions at 40–200x speed of LLM judge |

---

## v0.2 — "Multi-Protocol BYOA + StepEfficiency" (Expanding the Blast Radius)

> **Goal**: Support all four agent protocols (HTTP, MCP, CLI, Python callable). Add loop/thrashing detection and the `ANOMALOUS` verdict. Mock HTTP server for API call capture.
>
> **User Story**: *"My agent is an MCP server. I want to point AgentEval at it and test whether it handles multi-turn conversations correctly without getting stuck in loops."*

### What Ships (Incremental on v0.1)
| Component | Scope |
|---|---|
| **HTTPAdapter** | Connect to any REST/webhook agent endpoint |
| **MCPAdapter** | Native MCP client (stdio + SSE transport) |
| **CLIAdapter** | Subprocess agent execution with stdin/stdout capture |
| **StepEfficiencyEvaluator** | Loop detection (sliding-window hash), token budget enforcement, backtrack scoring |
| **`ANOMALOUS` Verdict** | Fires when task completes but with concerning efficiency signals |
| **Mock HTTP Server** | Local proxy that records outgoing API calls for assertion |
| **Scenario Generators** | Helper utilities to create scenario YAML from existing agent runs (record → replay) |
| **Rich CLI Output** | Colored trajectory trace display, step-by-step tool call inspection |

### Definition of Done
- [ ] All four adapters pass integration tests against sample agents
- [ ] Loop detection correctly flags a deliberately looping agent as `ANOMALOUS`
- [ ] Mock HTTP server captures and replays external API calls
- [ ] `agenteval record` captures a live agent run and saves it as a replayable scenario

---

## v0.3 — "LLM Judge + OpenShell Sandbox + OTel Tracing"

> **Goal**: Add calibrated LLM-as-a-Judge for subjective criteria. Integrate NVIDIA OpenShell for kernel-level sandbox isolation. Emit OpenTelemetry traces.
>
> **User Story**: *"My agent generates customer support responses. I need to verify it's not only calling the right tools but also that the final response is helpful, safe, and on-policy — and I need my security team to trust the sandbox."*

### What Ships (Incremental on v0.2)
| Component | Scope |
|---|---|
| **JevScorer** | TypeSafe AI System One integration for high-speed typed evaluation (Choice/Score/Noul primitives) with confidence gating to LLM fallback |
| **LLMJudgeEvaluator** | Calibrated Chain-of-Thought scoring with configurable rubrics (helpfulness, safety, policy compliance, reasoning quality) |
| **Judge Calibration Pipeline** | Pairwise comparison, position bias detection, human label alignment scoring |
| **OpenShell Sandbox Backend** | Optional NVIDIA OpenShell integration for Landlock/seccomp/network namespace isolation (as Inspect AI sandbox plugin) |
| **Docker Sandbox Backend** | Ephemeral Docker container execution for tool calls (via Inspect AI built-in) |
| **OpenTelemetry Exporter** | Emit trajectory spans in OpenInference format to any OTel-compatible backend |
| **Trace Ingestion** | Import traces from Langfuse, Arize Phoenix, or raw OTel OTLP for offline evaluation |
| **NeMo Guardrails Integration** | Optional: Test whether NeMo Guardrails policies hold under adversarial inputs |
| **Drift Detection (Prompt + Judge)** | Hash-based prompt version tracking + periodic judge calibration checks |

### Definition of Done
- [ ] LLM judge scores correlate with human labels at ≥0.75 Cohen's kappa on a validation set
- [ ] OpenShell sandbox correctly prevents unauthorized file/network access in test scenarios
- [ ] OTel traces visible in Jaeger/Grafana when connected
- [ ] `agenteval run --judge gpt-4o --sandbox openshell` works end-to-end

---

## v0.4 — "Golden Dataset Flywheel + CI/CD Quality Gate"

> **Goal**: Close the loop — production failures automatically become regression tests. Ship the CI/CD quality gate that blocks PRs on regression.
>
> **User Story**: *"My agent broke in production last week. I want that failure to automatically become a test case so it never happens again. And I want my CI pipeline to block any PR that would cause a regression."*

### What Ships (Incremental on v0.3)
| Component | Scope |
|---|---|
| **Production Trace Miner** | Ingest production traces (OTel/Langfuse/Phoenix), cluster failures by error taxonomy, extract minimal reproducible scenarios |
| **Adversarial Scenario Generator** | Synthesize edge cases: prompt injections, schema corruptions, malformed tool returns, rate-limit simulations |
| **Golden Dataset Manager** | Versioned, immutable dataset store with semantic deduplication |
| **Regression Gate** | `agenteval gate --threshold 0.95` exits non-zero if pass rate drops below threshold |
| **GitHub Actions Integration** | Pre-built workflow template: run AgentEval on PR, post markdown summary with trace links |
| **GitLab CI Template** | Same for GitLab |
| **PR Comment Bot** | Auto-posts regression table + flame graph link as a PR comment |

### Definition of Done
- [ ] A production failure trace is ingested and converted into a replayable scenario within 60 seconds
- [ ] `agenteval gate` correctly blocks a PR that introduces a regression
- [ ] GitHub Actions workflow runs end-to-end on a sample repo
- [ ] Golden dataset deduplication prevents duplicate scenarios from accumulating

---

## v0.5 — "Developer Dashboard + Multi-Agent Swarm Evaluation"

> **Goal**: Ship a premium, modern web dashboard for visual trace inspection, dataset curation, and evaluation history. Support evaluating multi-agent swarms (not just single agents).
>
> **User Story**: *"I have a 4-agent swarm (planner, researcher, coder, reviewer). I need to see how they coordinate, where handoffs fail, and which agent is the bottleneck."*

### What Ships (Incremental on v0.4)
| Component | Scope |
|---|---|
| **Web Dashboard** | Vite + Vanilla CSS dark-mode dashboard: run matrix, trajectory flame graphs, step-by-step diff inspector, dataset curation interface |
| **Multi-Agent Topology** | Model and visualize inter-agent communication patterns, handoff success rates, coordination bottlenecks |
| **Swarm-Level Evaluators** | Evaluate collective goal completion, agent specialization adherence, redundancy detection |
| **Dataset Curation UI** | Visual interface for reviewing, editing, approving, and versioning golden dataset scenarios |
| **Comparison Mode** | Side-by-side comparison of two agent versions (A/B evaluation) across the same scenario suite |
| **Cost Attribution** | Per-step, per-agent, per-tool token and latency cost breakdown |

### Definition of Done
- [ ] Dashboard renders trajectory flame graphs with < 200ms load time
- [ ] Multi-agent swarm evaluation correctly identifies inter-agent handoff failures
- [ ] A/B comparison shows clear regression/improvement metrics between two agent versions
- [ ] UI follows `ui-ux-pro-max` and `frontend-ui-engineering` skill standards (premium, accessible, responsive)

---

## v1.0 — "Production-Grade Platform"

> **Goal**: Enterprise-ready, battle-tested platform with full documentation, plugin ecosystem, and community.

### What Ships (Incremental on v0.5)
| Component | Scope |
|---|---|
| **Plugin System** | Pluggable evaluators, sandbox backends, trace importers, reporters |
| **Enterprise Auth** | SSO/OIDC integration for dashboard |
| **PostgreSQL + ClickHouse** | Production-scale storage for teams running thousands of evaluations |
| **Compliance Reports** | EU AI Act, NIST AI RMF, ISO/IEC 42001 evidence export templates |
| **Benchmark Suite** | GAIA, SWE-bench, BFCL integration for standardized agent benchmarking |
| **SDK (Python + TypeScript)** | Programmatic API for embedding AgentEval in custom workflows |
| **Documentation Site** | Full docs with tutorials, API reference, and architecture guides |

---

## Execution Principles

### 1. Every Version is a Working Product
No version is "just infrastructure." Every version has:
- A clear user story
- A working CLI command that solves a real problem
- Example scenarios that demonstrate the full loop
- Tests that prove it works
- A README section that a developer can follow

### 2. Iterative Building (Stack-Ranked Delivery)
```
v0.1: Core models + CallableAdapter + ToolSchema + StateDiff + Verdict + CLI
  ↓ (working product — can evaluate Python agents)
v0.2: + HTTP/MCP/CLI adapters + Loop detection + ANOMALOUS + Record/Replay
  ↓ (working product — can evaluate any agent protocol)
v0.3: + LLM Judge + OpenShell + OTel tracing + Trace ingestion
  ↓ (working product — adds subjective eval + security sandbox + observability)
v0.4: + Golden dataset mining + CI/CD gate + PR bot
  ↓ (working product — closes the flywheel loop)
v0.5: + Web dashboard + Multi-agent swarms + A/B comparison
  ↓ (working product — adds visual intelligence layer)
v1.0: + Plugin system + Enterprise + Compliance + Benchmarks + SDK
  ↓ (production-grade platform)
```

### 3. Sandbox Evolution (Don't Over-Engineer Early)
| Phase | Sandbox | Dependency |
|---|---|---|
| v0.1–v0.2 | Python tempfile + SQLite + function call capture | Zero external deps |
| v0.3 | + NVIDIA OpenShell (optional) + Docker (optional) | Opt-in, not required |
| v0.4+ | + E2B / Modal as pluggable backends | Enterprise cloud option |

### 4. Adapter Protocol Expansion
| Phase | Adapters Available |
|---|---|
| v0.1 | `CallableAdapter` (Python in-process) |
| v0.2 | + `HTTPAdapter` + `MCPAdapter` + `CLIAdapter` |
| v0.3+ | Community-contributed adapters via plugin system |

### 5. Evaluator / Scorer Expansion
| Phase | Scorers Available (Inspect AI `@scorer`) |
|---|---|
| v0.1 | `ToolSchemaScorer` + `StateDiffScorer` + `UnverifiableScorer` |
| v0.2 | + `StepEfficiencyScorer` (loop/thrashing) + `FirstUnrecoverableStepScorer` + `pass^k` reporting |
| v0.3 | + `JevScorer` (System One typed decisions) + `LLMJudgeScorer` (calibrated, opt-in) + drift detection |
| v0.4 | + `RegressionScorer` (golden dataset) + OAT-style unsupervised anomaly scorer |
| v0.5 | + `SwarmCoordinationScorer` (multi-agent) + `CostAttributionScorer` |

---

## Project Structure (Target)

```
AgentEval/
├── AGENTS.md                          # Craft orchestration rules
├── CONSTRAINTS.md                     # Quality bar contract
├── pyproject.toml                     # Python package config (inspect-ai as dependency)
├── README.md                          # Quickstart & overview
│
├── agenteval/                         # Core Python package
│   ├── __init__.py
│   ├── core/
│   │   ├── models.py                  # Pydantic domain models (Verdict, etc.)
│   │   ├── config.py                  # Platform configuration
│   │   └── exceptions.py             # Custom exception hierarchy
│   │
│   ├── adapters/                      # BYOA → Inspect Solver bridge
│   │   ├── base.py                    # AgentAdapter ABC → Solver
│   │   ├── callable.py                # Python in-process adapter
│   │   ├── http.py                    # HTTP/REST adapter (v0.2)
│   │   ├── mcp.py                     # MCP client adapter (v0.2)
│   │   └── cli.py                     # Subprocess adapter (v0.2)
│   │
│   ├── scorers/                       # Custom Inspect AI @scorer implementations
│   │   ├── tool_schema.py            # Tool name + argument schema validation
│   │   ├── state_diff.py             # Sealed environment state diff assertion
│   │   ├── unverifiable.py           # UNVERIFIABLE verdict scorer
│   │   ├── sealed_evidence.py        # Environmental side-effect proof
│   │   ├── step_efficiency.py        # Loop/thrashing/budget detection (v0.2)
│   │   ├── first_unrecoverable.py    # Compounding error root-cause locator (v0.2)
│   │   ├── jev_scorer.py             # TypeSafe AI Jev System One integration (v0.3)
│   │   ├── llm_judge.py              # Calibrated LLM-as-a-Judge (v0.3)
│   │   └── deepeval_bridge.py        # Optional DeepEval metric imports (v0.3)
│   │
│   ├── sandbox/                       # Sandbox backend plugins
│   │   ├── openshell.py              # NVIDIA OpenShell backend (v0.3)
│   │   └── local_enhanced.py         # Enhanced local sandbox (tempfile + SQLite)
│   │
│   ├── tasks/                         # Inspect AI @task definitions
│   │   ├── scenario_task.py          # YAML/JSON scenario → Inspect Task converter
│   │   └── benchmark_tasks.py        # Pre-wired benchmark tasks (GAIA, SWE-bench, τ-bench)
│   │
│   ├── datasets/                      # Golden dataset management (v0.4)
│   │   ├── store.py                   # Versioned dataset repository
│   │   ├── miner.py                  # Production trace → Inspect dataset converter
│   │   ├── adversarial.py            # Synthetic edge-case generator
│   │   └── drift.py                  # Six drift mode detection
│   │
│   ├── telemetry/                     # Observability (v0.3)
│   │   ├── otel.py                   # OpenTelemetry span exporter
│   │   └── ingest.py                # Trace importer (Langfuse/Phoenix/OTLP)
│   │
│   └── cli/                          # Developer CLI
│       ├── main.py                    # Typer app wrapping inspect eval
│       └── reporters/                # Output formatters
│           ├── table.py              # Rich table output
│           ├── markdown.py           # PR comment generator (v0.4)
│           └── json.py              # Machine-readable output
│
├── tests/                             # Test suite
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── examples/                          # Working examples
│   ├── agents/                       # Sample agents to evaluate
│   ├── scenarios/                    # Sample YAML test scenarios
│   └── README.md
│
├── docs/                              # Documentation
│   ├── ROADMAP.md                    # This file
│   ├── design/
│   │   ├── architecture.md           # System architecture spec
│   │   └── architecture.html         # Interactive diagram viewer
│   ├── engineering-ledger/           # Craft engineering ledger
│   └── decisions/                    # ADRs
│
├── dashboard/                         # Web UI (v0.5)
│
└── .agents/                           # Craft skills (52 installed)
    └── skills/
```

---

## Key Integration Points

### With NVIDIA Stack
| Tool | Integration Type | Version |
|---|---|---|
| **OpenShell** | Pluggable sandbox backend — kernel-level isolation for destructive tool calls | v0.3 |
| **NemoClaw** | Complementary platform — we evaluate agents, they secure the runtime | v0.3+ |
| **NeMo Guardrails** | Test target — verify that Colang policies hold under adversarial inputs | v0.3+ |

### With Observability Stack
| Tool | Integration Type | Version |
|---|---|---|
| **Langfuse** | Trace importer — ingest production spans for offline evaluation | v0.3 |
| **Arize Phoenix** | Trace importer — same | v0.3 |
| **OpenTelemetry** | Native exporter — emit trajectory spans in OpenInference format | v0.3 |
| **Jaeger / Grafana** | Visualization — view AgentEval traces in existing observability dashboards | v0.3 |

### With Agent Frameworks
| Framework | Adapter | Version |
|---|---|---|
| **LangGraph** | `CallableAdapter` (in-process) | v0.1 |
| **CrewAI** | `CallableAdapter` (in-process) | v0.1 |
| **AutoGen** | `CallableAdapter` (in-process) | v0.1 |
| **Google AGY SDK** | `CallableAdapter` (in-process) | v0.1 |
| **Any HTTP Agent** | `HTTPAdapter` (REST/webhook) | v0.2 |
| **Any MCP Server** | `MCPAdapter` (stdio/SSE) | v0.2 |
| **Any CLI Agent** | `CLIAdapter` (subprocess) | v0.2 |

### With CI/CD
| Platform | Integration | Version |
|---|---|---|
| **GitHub Actions** | Pre-built workflow template + PR comment bot | v0.4 |
| **GitLab CI** | Pipeline template | v0.4 |
| **Any CI** | `agenteval gate --threshold 0.95` exit code | v0.4 |

---

## Success Metrics (How We Know It's Working)

### v0.1 Success
- [ ] A developer installs AgentEval and runs their first evaluation in < 5 minutes
- [ ] The verdicts (`PASS` / `FAIL` / `UNVERIFIABLE`) are trustworthy and match manual inspection
- [ ] At least 3 different agent frameworks tested successfully via `CallableAdapter`

### v0.2 Success
- [ ] All four adapter protocols work against real agents
- [ ] Loop detection catches a deliberately looping agent within 10 steps
- [ ] Record/replay produces identical trajectories on deterministic agents

### v0.3 Success
- [ ] LLM judge scores correlate with human labels (Cohen's κ ≥ 0.75)
- [ ] OpenShell sandbox prevents unauthorized access in 100% of test cases
- [ ] OTel traces are visible in Jaeger/Grafana without custom configuration

### v0.4 Success
- [ ] A production failure is automatically converted to a regression test in < 60 seconds
- [ ] CI gate correctly blocks a regression-introducing PR
- [ ] Golden dataset grows organically from production usage

### v0.5 Success
- [ ] Dashboard loads trajectory flame graphs in < 200ms
- [ ] Multi-agent swarm evaluation identifies coordination bottlenecks
- [ ] A/B comparison clearly shows improvement/regression between agent versions

### v1.0 Success
- [ ] Platform handles 10,000+ evaluations/day without degradation
- [ ] Plugin ecosystem has at least 5 community-contributed evaluators
- [ ] Used by ≥ 3 enterprise teams in production

---

## Current Status

**Phase**: Shape → Build (transitioning)  
**Version**: Pre-v0.1  
**Foundation**: Inspect AI (MIT) — [ADR-001](../decisions/ADR-001-build-on-inspect-ai.md)  
**Next Action**: Scaffold the v0.1 Python package on Inspect AI and implement custom scorers

### Completed
- [x] Competitive analysis (TestMu AI, DeepEval, LangSmith, Arize Phoenix, Braintrust, Maxim AI)
- [x] NVIDIA sandbox research (OpenShell, NemoClaw, NeMo Guardrails)
- [x] Architecture design with Mermaid diagrams
- [x] `AGENTS.md` with core engineering principles
- [x] `CONSTRAINTS.md` with quality bar contract
- [x] Craft framework adopted (v0.2.3, 52 skills installed)
- [x] Git repo initialized, remote linked to `DTiapan/AgentEval`
- [x] Engineering ledger bootstrapped (INDEX, phases, attack plans)
- [x] Interactive architecture diagram viewer (`docs/design/architecture.html`)
- [x] Foundation strategy decided — build on Inspect AI ([ADR-001](../decisions/ADR-001-build-on-inspect-ai.md))
- [x] Jev (TypeSafe AI System One) researched — adopted as Tier 1 judge
- [x] Research survey completed — compounding errors, pass^k, OAT, drift modes, AgentRx, TraceElephant, τ-bench

### Up Next
- [ ] Scaffold `pyproject.toml` with `inspect-ai` as core dependency
- [ ] Implement BYOA adapter base → Inspect AI `@solver` bridge
- [ ] Implement `CallableAdapter` (first adapter)
- [ ] Implement `ToolSchemaScorer` (Inspect AI `@scorer`)
- [ ] Implement `StateDiffScorer` (Inspect AI `@scorer`)
- [ ] Implement `UnverifiableScorer` (our core innovation)
- [ ] Implement scenario YAML → Inspect `@task` converter
- [ ] Build `agenteval run` CLI wrapping `inspect eval`
- [ ] Create example agent + test scenarios
- [ ] Ship v0.1
