# Phases & Quality Gates

> Governed by `using-craft` lifecycle router and `CONSTRAINTS.md`.
> Every phase transition requires concrete gate evidence and user sign-off.

## Active Lifecycle Board

| Phase | Skill | Status | Gate Evidence Required | Status & Evidence |
|-------|-------|--------|------------------------|-------------------|
| **Shape** | `idea-refine` | **Sign-off pending** | Idea one-pager with HMW, directions, assumptions, MVP scope, and Not Doing list | [docs/ideas/agent-assurance-platform.md](../ideas/agent-assurance-platform.md) complete. Awaiting user sign-off. |
| **Spec / ADR** | `documentation-and-adrs`, `spec-driven-development` | **Ready** | Accepted ADRs, architecture spec, and product roadmap | [ADR-001](../decisions/ADR-001-build-on-inspect-ai.md), [architecture.md](../design/architecture.md), [ROADMAP.md](../ROADMAP.md) complete. |
| **Plan** | `planning-and-task-breakdown` | **Ready** | Attack plan with ordered, testable implementation slices | [attack-plans.md](attack-plans.md#ap-001-platform-architecture-pluggable-byoa-harness--trajectory-assurance-engine) (AP-001) complete. |
| **Build** | `incremental-implementation`, `test-driven-development` | Planned | Working code + pytest green with ≥85% coverage (CONSTRAINTS.md) | Next phase once Shape/Spec/Plan signed off. |
| **Verify** | `constraint-driven-development` | Planned | Working CLI demo (`agenteval run`, `agenteval replay`), fault injection, state diff proof | Scheduled in v0.1 DoD. |
| **Review** | `code-review-and-quality` | Planned | Multi-axis review against CONSTRAINTS.md (no stubs, no suppressed checks) | Pre-merge verification. |
| **Ship** | `shipping-and-launch` | Planned | CI pipeline green, clean v0.1 tag, publishable package | Release milestone. |

---

## Phase log

- **2026-09-20**:
  - Completed **Shape** phase deliverables under `idea-refine`: produced [docs/ideas/agent-assurance-platform.md](../ideas/agent-assurance-platform.md).
  - Completed **Spec / ADR** phase deliverables: produced [ADR-001](../decisions/ADR-001-build-on-inspect-ai.md), [architecture.md](../design/architecture.md), [ROADMAP.md](../ROADMAP.md), and tactical decisions DR-001 through DR-005.
  - Completed **Plan** phase deliverables: formulated AP-001 in [attack-plans.md](attack-plans.md).
  - Gate check: Presenting Shape one-pager to user for formal sign-off before entering **Build**.
