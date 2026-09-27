# Phases & Quality Gates

> Governed by `using-craft` lifecycle router and `CONSTRAINTS.md`.
> Every phase transition requires concrete gate evidence and user sign-off.

## Active Lifecycle Board

| Phase | Skill | Status | Gate Evidence Required | Status & Evidence |
|-------|-------|--------|------------------------|-------------------|
| **Shape** | `idea-refine` | **Approved** | Idea one-pager with HMW, directions, assumptions, MVP scope, and Not Doing list | [docs/ideas/agent-assurance-platform.md](../ideas/agent-assurance-platform.md) approved by user. |
| **Spec / ADR** | `documentation-and-adrs`, `spec-driven-development` | **Approved** | Accepted ADRs, architecture spec, and product roadmap | [ADR-001](../decisions/ADR-001-build-on-inspect-ai.md), [architecture.md](../design/architecture.md), [ROADMAP.md](../ROADMAP.md) accepted. |
| **Plan** | `planning-and-task-breakdown` | **Approved** | Attack plan with ordered, testable implementation slices | [attack-plans.md](attack-plans.md#ap-001-platform-architecture-pluggable-byoa-harness--trajectory-assurance-engine) (AP-001) accepted. |
| **Build** | `incremental-implementation`, `test-driven-development` | **Approved** | Working code + pytest green with ≥85% coverage (CONSTRAINTS.md) | Slices 0 through 7 implemented, 37 tests green, 92.22% coverage. |
| **Verify** | `constraint-driven-development` | **Active** | Working CLI demo (`agenteval run`, `agenteval replay`), fault injection, state diff proof | Interactive CLI verified with live playback, chaos fault injection, and jump-to-fail replayer. |
| **Review** | `code-review-and-quality` | Planned | Multi-axis review against CONSTRAINTS.md (no stubs, no suppressed checks) | Pre-merge verification. |
| **Ship** | `shipping-and-launch` | Planned | CI pipeline green, clean v0.1 tag, publishable package | Release milestone. |

---

## Phase log

- **2026-09-20**:
  - Completed **Shape** phase deliverables under `idea-refine`: produced [docs/ideas/agent-assurance-platform.md](../ideas/agent-assurance-platform.md). Formally approved by user.
  - Completed **Spec / ADR** phase deliverables: produced [ADR-001](../decisions/ADR-001-build-on-inspect-ai.md), [architecture.md](../design/architecture.md), [ROADMAP.md](../ROADMAP.md), and tactical decisions DR-001 through DR-005.
  - Completed **Plan** phase deliverables: formulated AP-001 in [attack-plans.md](attack-plans.md).
  - Completed **Build** phase deliverables: implemented all 8 vertical slices with strict test-driven development, achieving 92.22% coverage across 37 automated tests.
  - Entered **Verify** phase: validated interactive execution, chaos fault injection recovery, and offline replay with root-cause jumping.
- **2026-09-27**:
  - Completed **Assurance Appliance & OSS Bridges** (Phases 1–6, [DR-025](decisions.md#active-index)): implemented Priority Tiering (`P0`, `P1`, `P2`), dynamic budget projections, PromptFoo red-team bridge, DeepEval trajectory metrics bridge, Inspect AI Docker sandbox task builder, and deterministic state-diff ($\Delta S$) hardening. All 198 tests passing at 86.26% coverage, clean `mypy --strict`, clean `ruff`, and verified Vite web console build.

