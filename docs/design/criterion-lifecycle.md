# Acceptance criteria lifecycle

> **Traces to:** FR-B-03, FR-B-04, FR-B-14, FR-B-15, FR-B-16; [domain-model.md](domain-model.md);
> [persistence-schema.md](persistence-schema.md) tables `acceptance_criteria`,
> `criterion_verdicts`, `evidence_items`.

## Purpose

A **requirement** states *what* must hold. An **acceptance criterion** states *how
we would know* — with an **evidence kind** and a **check kind**. Verdicts are
recorded **per criterion**, not per chat turn.

## States

```text
                    ┌─────────────┐
   extract / pack ─►│  proposed   │
                    └──────┬──────┘
                           │ U2 review (Studio, future)
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         approved      rejected    (edit → proposed)
              │
              │ suite freeze (immutable)
              ▼
         frozen in SuiteVersion
              │
              │ run executes
              ▼
    CriterionVerdict (PASS | FAIL | UNVERIFIABLE)
```

**Requirement** `review_status` uses the same vocabulary (`proposed` | `approved` | `rejected`).
On freeze, only **approved** requirements and criteria are included (v1: auto-approve
extracted rows; UI review is FR-B-04).

## Who does what

| Phase | U1 (engineer) | U2 (sign-off) | System |
|-------|---------------|---------------|--------|
| Ingest | Supplies PRD | — | Proposes requirements + default criteria |
| Review | — | Edits / approves / adds criteria | Persists draft on suite version |
| Freeze | Triggers create/sync | Confirms (future explicit gate) | Writes immutable rows + `test_data_json` |
| Run | Connects target | — | Collects evidence, scores each criterion |
| Sign-off | — | Reads report per requirement / control | No client-side synthesis |

## Criterion record (logical)

| Field | Meaning |
|-------|---------|
| `stable_id` | Stable within requirement (e.g. `observable-response`, `refund-ceiling`) |
| `description` | Human-readable condition |
| `evidence_kind` | What must be collected (see registry below) |
| `check_kind` | How to decide PASS/FAIL from evidence |
| `source_kind` | `extracted` \| `pack` \| `user` |
| `verdict_tier` (on verdict) | `deterministic` \| `model_judged` |

## Evidence kind registry (backbone, v1)

| `evidence_kind` | Produced by | Used in profile |
|-----------------|-------------|-----------------|
| `http_observation` | Transport connector (black-box POST) | Black-box default |
| `http_trace_step` | Sealed `execution_steps` | Black-box |
| `db_diff` | Evidence connector | Harness / customer probe |
| `audit_log_row` | Evidence connector | Pack + connector |
| `trace_span` | OTel / Inspect log (future) | Harness / Inspect |

If a criterion needs a kind that no installed connector or pack can produce →
**UNVERIFIABLE** (FR-B-15). Never PASS.

## Check kind registry (backbone, v1)

| `check_kind` | Behavior | Deterministic? |
|--------------|----------|----------------|
| `blackbox_observable` | Rules on `ObservationBundle` + rationale (today: `observable_scorer`) | Yes |
| `schema_assertion` | JSON/schema match on evidence payload | Yes |
| `state_diff_assertion` | ΔS keys in harness sandbox | Yes |
| `pack_check` | Delegates to pack-registered scorer entry point | Usually yes |
| `model_judged` | LLM rubric; labeled; cannot override UNVERIFIABLE | No |

Packs may add **check kinds** only by registering scorers; backbone lists kinds in
[pack-interface.md](pack-interface.md).

## Scoring rules (invariants)

1. **PASS** or **FAIL** → at least one `EvidenceItem` linked in `criterion_verdict_evidence`.
2. No evidence → **UNVERIFIABLE**.
3. Re-score same evidence + same criterion → same deterministic result (NFR-B-04).
4. `model_judged` never flips UNVERIFIABLE to PASS/FAIL (FR-B-16).

## Current implementation gap

| Designed | Today |
|----------|--------|
| Multiple criteria per requirement | One placeholder `observable-response` per capability on freeze |
| U2 review UI | Not built (FR-B-04) |
| `criterion_verdicts` on run | **Partial** — written on `save_run` when frozen `test_cases` exist |
| Evidence rows | **Partial** — `evidence_items` on run; PASS/FAIL linked per FR-B-15 |

**Next code slice:** runner writes `evidence_items` + `criterion_verdicts` using
`check_kind=blackbox_observable` and `evidence_kind=http_observation`.
