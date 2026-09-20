# ADR-003: Black-Box Test Intelligence Pipeline & Dual Execution Profiles

- **Status**: Accepted
- **Date**: 2026-09-20
- **Decision Makers**: @ajas.bakran
- **Tags**: architecture, black-box, test-optimization, coverage, product

## Context

AgentEval’s **primary customer** is an autonomous agent exposed only via:

- Functional requirements, description, personas, declared capabilities/tools, policies, and an **invocation endpoint** (plus credentials).

We do **not** have access to customer source code, internal prompts, databases, or internal execution traces.

The v0.1 **harness path** (in-process callable, `LocalSandbox`, `ToolFaultInjector`, `StateDiffEvaluator`) remains valuable for BYOA developers who run agents in our environment. It is **not** sufficient as the default mental model for enterprise black-box evaluation: claiming sealed ΔS or database consistency without an external probe would violate credibility (see product spec §14).

The differentiated product value is:

> Given specification + endpoint, infer what should be tested, select the **smallest high-value test pack**, execute at the endpoint, score results, report **multi-dimensional coverage**, and surface **what remains unknown**.

Today the repo has Plane 0 building blocks (`AgentCard`, PRD ingestion, dynamic personas, `MetricRouter`, `ScenarioCompiler`, `HTTPAdapter`) but **no** candidate pool vs optimized pack separation, risk-aware set cover, coverage mapping, or gap-driven re-test.

## Decision

### 1. Black-box-first product pipeline (authoritative spec)

Adopt the **Black-Box Test Intelligence Pipeline** as the north-star product flow, documented in [black-box-test-intelligence-pipeline.md](../design/black-box-test-intelligence-pipeline.md):

```
Requirements → Understanding → Agent Test Model → Failure Surface →
Candidate Tests (large pool, not auto-run) → Risk → Optimization →
Test Pack → Endpoint Execution → Observation → Scoring →
Coverage → Gaps → Targeted Re-test
```

Core IP lives in **understanding provenance**, **optimization**, and **coverage honesty**—not in a generic scenario generator that executes every variant.

### 2. Dual execution profiles (same platform, different evidence)

| Profile | When | Evidence sources |
|---------|------|------------------|
| **`blackbox`** (default for enterprise eval) | Customer endpoint only | Request/response, HTTP status, latency, N-run consistency, optional structured fields returned by the agent, customer-declared external probes |
| **`harness`** (opt-in) | In-process / local tools / dev CI | Existing sandbox ΔS, tool fault injection, internal tool traces |

Scoring and verdicts must consume an **`ObservationBundle`** per profile. Black-box mode must **never** assert internal state (e.g. DB consistency) unless observable via declared probes or API.

Extend the verdict/limitations vocabulary beyond single-test `UNVERIFIABLE` to pack-level **TESTED | OBSERVED | INFERRED | UNTESTABLE** (see design doc).

### 3. Incremental implementation (attack plan AP-003)

**Must-have (v0.2):** B0, B1, B2, B4, B5 (coverage report only), B7 (HTTP blackbox), B8 (plan + `run --pack`).  
**Later (v0.3+):** B3, B5 gap automation, B6, B8 rich reports, B9 Inspect compiler, LLM hypotheses, non-HTTP black-box.

Do **not** rewrite v0.1 harness modules. Harness chaos, MCP/CLI adapters, and advanced replay are **not** v0.2 gates for black-box MVP.

**Order:** B0 + B4 + B5 (fixtures) → B1 → B2 → B7 → B8.

### 4. Inspect AI placement

Inspect AI remains the **execution and scorer runtime** ([ADR-001](ADR-001-build-on-inspect-ai.md)). Set-cover optimization, mandatory security floors, and coverage mapping stay **in-repo and deterministic**. Layer 4 (Inspect Plan Compiler) ships **after** black-box observation schema stabilizes (slice B9).

### 5. Metric router alignment

`MetricRouter` recommendations must gain **applicability predicates** tied to the Agent Test Model (e.g. skip `state_diff_delta_s` when `side_effects_observable=false`). Scorers named in the router but not implemented remain **planned** until wired behind the facade.

### 6. Frozen regression suite ([DR-010](../engineering-ledger/decisions.md#active-index))

First upload of requirements + endpoint **bootstraps** a versioned suite on disk. All later runs **reuse** that pack to detect regressions. Regeneration is **explicit** (new suite version), never automatic on each run—so prior test investment and historical comparability are preserved. When capabilities are **removed** from the spec, linked tests are **pruned** on explicit suite maintenance ([DR-011](../engineering-ledger/decisions.md#active-index)), not left as stale CI noise. See [Frozen regression suite](../design/black-box-test-intelligence-pipeline.md#frozen-regression-suite-generate-once-run-many).

## Alternatives Considered

### A: Extend `ScenarioCompiler` only
- **Pros:** Minimal new code.
- **Cons:** Emits all scenarios, no optimization, no coverage model—does not deliver product moat.
- **Rejected.**

### B: White-box only; require sandbox access for all customers
- **Pros:** Strongest sealed evidence.
- **Cons:** Incompatible with typical enterprise deployment; limits market.
- **Rejected** as default; retained as `harness` profile.

### C: LLM generates and runs all tests
- **Pros:** Fast to demo.
- **Cons:** Cost explosion, redundant coverage, no mandatory security floor—violates §6–§7 of product spec.
- **Rejected.**

## Consequences

- **Positive:** Clear product story, credible limitations reporting, reuse of existing Plane 0 + HTTP adapter.
- **Negative:** Two execution paths to maintain; docs and CLI must label profile explicitly.
- **Follow-up:** Update [ROADMAP.md](../ROADMAP.md), [AP-003](../engineering-ledger/attack-plans.md), [architecture.md](../design/architecture.md) cross-links; implement slices per attack plan.

## References

- [Black-Box Test Intelligence Pipeline](../design/black-box-test-intelligence-pipeline.md)
- [ROADMAP — Incremental delivery](../ROADMAP.md#black-box-test-intelligence-incremental-delivery)
