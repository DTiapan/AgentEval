# Engineering Ledger — Index

> Read this file before non-trivial work. Update at end of each substantive session.

**Active phase:** Shape → Build (transitioning)  
**Last updated:** 2026-09-20

## Current focus

Bootstrapping AgentEval — an enterprise-grade, trajectory-first AI Agent Assurance and Quality Engineering platform. Abstracting away golden datasets, telemetry/tracing, tool-call side-effect verification, multi-turn reasoning evaluation, and CI/CD regression gates behind a single pluggable interface: "Bring Your Own Agent" (BYOA).

## Open attack plan

- [AP-001: Platform Architecture, Pluggable BYOA Harness & Trajectory Assurance Engine](attack-plans.md#ap-001-platform-architecture-pluggable-byoa-harness--trajectory-assurance-engine)

## Recent sessions

- **2026-09-20 (session 3)**: **Foundation strategy decided** — build on Inspect AI (MIT, UK AISI) as eval engine core ([ADR-001](../decisions/ADR-001-build-on-inspect-ai.md)). Researched Jev (TypeSafe AI System One) for Tier 1 high-speed typed judge. Completed academic research survey: compounding errors (TUM 2026), pass^k consistency metrics (τ-bench/Sierra), OAT unsupervised failure attribution (arxiv July 2026), six drift modes (Future AGI), AgentRx constraint-based attribution, TraceElephant full observability. Updated roadmap with tiered judge architecture, research-backed techniques, revised project structure for Inspect AI integration.
- **2026-09-20 (session 2)**: Direction verdict scored **8.5/10** on industry problem-fit. Created comprehensive product roadmap (`docs/ROADMAP.md`) covering v0.1→v1.0 with stack-ranked iterative delivery. Researched NVIDIA OpenShell/NemoClaw/NeMo Guardrails sandbox strategy. Created `CONSTRAINTS.md` with anti-slop quality bar. Built interactive architecture diagram viewer (`docs/design/architecture.html`).
- **2026-09-20 (session 1)**: Initialized AgentEval repository with Craft framework (`DTiapan/craft` v0.2.3, profile: all). Linked remote `https://github.com/DTiapan/AgentEval.git`. Completed state-of-the-art competitive analysis on TestMu AI Assurance, mapped architecture, and initialized ledger.

## Quick links

- [**Product Roadmap (v0.1→v1.0)**](../ROADMAP.md)
- [Architecture & System Design](../design/architecture.md)
- [Interactive Architecture Diagram](../design/architecture.html)
- [Constraints & Quality Floor](../../CONSTRAINTS.md)
- [Phases](phases.md)
- [Attack plans](attack-plans.md)
- [Decisions](decisions.md)
- [Lessons](lessons.md)
- [ADRs](../decisions/)
