# ADR-001: Build on Inspect AI as Evaluation Engine Foundation

- **Status**: Accepted (reaffirmed 2026-09-24; not yet implemented)
- **Date**: 2026-09-20
- **Decision Makers**: @ajas.bakran
- **Tags**: architecture, foundation, build-vs-buy

## Context

AgentEval needs an evaluation engine that can run test scenarios against agents, capture trajectories, execute scorers, and manage sandbox environments. Three options were evaluated:

| Option | Approach | Engineering Time Saved | Risk |
|---|---|---|---|
| **A: Build on Inspect AI** | Use UK AISI's `inspect_ai` (MIT) as the core engine. Build our IP as custom scorers, solvers, and sandbox backends. | ~60% — get task runner, transcript capture, Docker sandbox, 200+ benchmarks for free | Inspect AI is model-evaluation-centric (Solver abstraction); may need adaptation for agent-under-test patterns |
| **B: Build on DeepEval** | Use DeepEval's metric library and pytest integration. Build our IP as custom metrics + standalone runner. | ~40% — get trajectory metrics, loop detection, pytest DX | VC-backed (Confident AI); licensing/pricing risk. Cloud dependency conflicts with local-first philosophy |
| **C: Build from scratch** | Own framework using Pydantic, OTel SDK, Typer, Rich as building blocks. | 0% — rebuild everything | Months rebuilding what already exists. Unique IP ships later. |

## Decision

**Option A: Build on Inspect AI with DeepEval metrics as optional imports.**

### What We Reuse from Inspect AI
- `@task`, `@scorer`, `@tool` composable primitives
- Docker/K8s sandbox infrastructure (extensible to OpenShell)
- Full transcript/trajectory capture and log system
- `inspect view` for trajectory visualization (web viewer + VS Code extension)
- 200+ pre-built benchmarks via `inspect_evals` (GAIA, SWE-bench, CyBench, etc.)
- CLI (`inspect eval`) as underlying runner

### What We Build (Our Unique IP)
- **BYOA Adapter Layer** — Wraps any agent (HTTP, MCP, CLI, callable) as an Inspect AI Solver
- **`StateDiffScorer`** — Sealed environment state diff assertion (our core innovation)
- **`SealedEvidenceScorer`** — Environmental side-effect proof verification
- **`UnverifiableScorer`** — Explicit `UNVERIFIABLE` verdict when proof is missing
- **Jev Integration** — TypeSafe AI's System One model for high-speed, typed classification scoring
- **OpenShell Sandbox Backend** — NVIDIA OpenShell as a pluggable sandbox environment
- **Production Trace Miner** — OTel/Langfuse/Phoenix → Inspect dataset converter
- **Adversarial Scenario Generator** — Edge-case synthesis
- **CI/CD Quality Gate** — `agenteval gate` with exit codes and PR reporting
- **`agenteval` CLI** — Our wrapper CLI with Rich output, extending `inspect eval`

### What We Import from DeepEval (Optional)
- `ToolCorrectnessMetric` / `ArgumentCorrectnessMetric` (as comparative baselines)
- `AgentLoopDetectionMetric` (deterministic, complementary to our own)
- `StepEfficiencyMetric` (for efficiency benchmarking)
- G-Eval patterns (for custom LLM-as-a-Judge rubrics)

## Consequences

### Positive
- Ship v0.1 much faster — focus 100% of engineering on novel IP
- Inherit government-backed, actively maintained, MIT-licensed infrastructure
- Get 200+ benchmarks for free (GAIA, SWE-bench, etc.)
- Community alignment with UK AISI safety evaluation ecosystem
- Plugin system is Python-native — our extensions are standard Python packages

### Negative
- Dependency on Inspect AI's release cycle and API stability
- Must adapt the Solver abstraction for BYOA agent-under-test patterns
- Two layers of CLI (our `agenteval` wrapping `inspect eval`) — must feel seamless
- Must clearly differentiate from "just an Inspect AI plugin" in positioning

### Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Inspect AI deprecates or breaks Solver API | Pin major version; our adapter layer isolates consumers from changes |
| Performance overhead of Inspect AI's logging | Profile early; disable verbose logging in CI mode |
| DeepEval licensing changes | All DeepEval imports are optional; our core evaluators have zero DeepEval dependency |

## Implementation status (2026-09-24)

Not implemented as of v0.2. `inspect-ai` is listed only as an optional extra in
`pyproject.toml` and is not imported anywhere in `agenteval/`. The runner,
scorers, sandbox and replay were built in-repo, so the code currently matches
Option C, not Option A.

Decision reaffirmed: the domain-agnostic backbone is built on Inspect AI.
Domain plugins ship as separate packages that contribute tasks, solvers and
scorers through Inspect's setuptools entry points. Migration of existing
modules onto Inspect primitives is planned in ADR-005.

## References
- [Inspect AI Documentation](https://inspect.ai-safety-institute.org.uk/)
- [Inspect AI GitHub](https://github.com/UKGovernmentBEIS/inspect_ai)
- [DeepEval Documentation](https://docs.confident-ai.com/)
- [TypeSafe AI Jev](https://typesafe.ai/)
