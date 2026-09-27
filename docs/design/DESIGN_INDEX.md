# AgentEval — design index (read this first)

> **Purpose:** Single entry point so product and engineering build on the same
> foundations. **Do not add features** that are not traced to a requirement row
> below without updating the traceability matrix first.

## Canonical stack (top → bottom)

| Order | Document | Role |
|-------|----------|------|
| 1 | [domain-model.md](domain-model.md) | **Entities, relationships, invariants** — source of truth for “what exists” |
| 2 | [persistence-schema.md](persistence-schema.md) | **Tables, indexes, migration phases** — how entities are stored |
| 3 | [criterion-lifecycle.md](criterion-lifecycle.md) | **Acceptance criteria** — propose → approve → freeze → score |
| 4 | [pack-interface.md](pack-interface.md) | **Domain packs + connectors** — plugin contract (no domain in backbone) |
| 5 | [requirements-traceability.md](requirements-traceability.md) | **FR-B / FR-P → schema → API → code → tests** |
| 6 | [PRD_SAAS_FULL.md](PRD_SAAS_FULL.md) §9A | Product requirements and status |
| 7 | [black-box-test-intelligence-pipeline.md](black-box-test-intelligence-pipeline.md) | Black-box **pipeline** (ingest → run); maps to domain model § vocabulary |
| 8 | [architecture.md](architecture.md) | **Dual profiles** (harness vs black-box) + long-term subsystems; see §0 for alignment |

## ADRs (decisions)

| ADR | Topic |
|-----|--------|
| [ADR-001](../decisions/ADR-001-build-on-inspect-ai.md) | Inspect AI as eval engine |
| [ADR-004](../decisions/ADR-004-sqlite-local-persistence.md) | SQLite persistence |
| [ADR-005](../decisions/ADR-005-backbone-domain-packs-source-of-truth.md) | Backbone + packs, SoT, one target/run |
| [ADR-006](../decisions/ADR-006-pack-and-connector-contract.md) | Pack/connector contract (points to pack-interface.md) |

## Implementation vs design (honest)

| Layer | Design complete? | Code aligned? |
|-------|------------------|---------------|
| Entity model | Yes | Partial |
| SQLite v2 DDL | Yes | Tables created; many empty |
| Freeze → requirements / test_cases | Yes | **Yes** (slice 1) |
| Freeze → full criteria UX | Yes (lifecycle doc) | Placeholder criterion only |
| Run → criterion_verdicts + evidence | Yes | **Partial** (`save_run` + normalized suite) |
| Packs | Interface doc | **No** implementation |
| Inspect integration | ADR-001/005 | **No** |

## Build order (enforced)

```text
① Design debt closed (this index + lifecycle + pack interface + traceability)
② Runner writes evidence + per-criterion verdicts (slice 2 ✓)
③ API/UI reads criterion verdicts (slice 3 ✓)
④ Fintech pack v0
⑤ Inspect eval() wiring
⑥ CI backbone boundary (NFR-B-07)
```

## Vocabulary bridge (pipeline ↔ domain model)

| Pipeline / code today | Domain model |
|----------------------|--------------|
| `AgentCapability` | `Requirement` (until criteria are authored separately) |
| `CandidateTest` / `TestPack` | `TestCase` (frozen in suite version) |
| `capability_id` | `Requirement.stable_id` (`requirement_id()`) |
| `TestCaseResult.verdict` | Rollup; target is `CriterionVerdict` |
| `ObservationBundle` | Input to `EvidenceItem` (HTTP kind) |
| `ProvenanceLayer` (DECLARED/INFERRED/HYPOTHESIZED) | Hypothesis metadata; not the same as verdict tier |
