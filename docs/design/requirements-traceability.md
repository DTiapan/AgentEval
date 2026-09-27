# Backbone requirements traceability

> **Source requirements:** [PRD §9A](PRD_SAAS_FULL.md)
> **Update rule:** Change code or schema → update **Implementation** column in same PR.

Legend: **—** = not applicable yet | **⬜** not started | **◐** partial | **✓** built

## FR-B — functional backbone

| ID | Requirement (short) | Schema (v2) | API / surface | Code | Tests |
|----|---------------------|-------------|---------------|------|-------|
| FR-B-01 | Spec text versioned | `specification_versions` ⬜ | — | `suite_versions.requirements_text` ◐ | ingest |
| FR-B-02 | Stable requirement IDs | `requirements.stable_id` ◐ | — | `requirement_ids.py`, ingest ✓ | `test_requirement_stable_id` ✓ |
| FR-B-03 | Acceptance criteria | `acceptance_criteria` ◐ | — | default criterion on freeze ◐ | `test_normalized_suite_freeze` ◐ |
| FR-B-04 | Review before freeze | `review_status` ◐ | Studio ⬜ | auto-approved ◐ | ⬜ |
| FR-B-05 | Spec diff by ID | — | sync ⬜ | `suite_sync` ◐ | `test_suite_sync` ✓ |
| FR-B-06 | Candidate pool | `candidate_pool_json` ✓ | preview/init ✓ | `SuiteBootstrap` ✓ | bootstrap tests ✓ |
| FR-B-07 | Optimized pack | `pack_json` ✓ | init ✓ | `TestPackOptimizer` ✓ | optimizer tests ✓ |
| FR-B-08 | Test ↔ criterion links | `test_case_criteria` ◐ | — | `normalized_suite.py` ✓ | freeze test ✓ |
| FR-B-09 | Frozen suite version | `suite_versions` ✓ | `/v1/suites` ✓ | `SuiteRepository` ✓ | repo tests ✓ |
| FR-B-10 | Sync changelog | — | sync ⬜ | `suite_sync` + archive ✓ | sync test ✓ |
| FR-B-11 | Run vs target | `targets`, `assurance_runs.target_id` ◐ | run ✓ | HTTP + default target ◐ | migrations test ◐ |
| FR-B-12 | Sealed steps | `execution_steps` ✓ | replay ✓ | `execution_trace` ✓ | repo e2e ✓ |
| FR-B-13 | Evidence items | `evidence_items` ◐ | — | `persist_run_evidence_and_verdicts` ✓ | `test_run_criterion_verdicts` ✓ |
| FR-B-14 | Verdict per criterion | `criterion_verdicts` ◐ | `GET runs/latest`, suite detail ✓ | on `save_run` + `enrich_run_report` ✓ | `test_api_requirements_verdicts` ✓ |
| FR-B-15 | UNVERIFIABLE rules | — | report ✓ | scorer partial ✓ | observable_scorer tests ◐ |
| FR-B-16 | Deterministic re-score | — | — | partial ◐ | ⬜ |
| FR-B-17 | Per-requirement status | — | report ◐ | coverage by capability ◐ | ⬜ |
| FR-B-18 | Baseline compare | `baseline_run_id` ⬜ | diff ◐ | previous run only ◐ | ⬜ |
| FR-B-19 | HTML report | — | report ✓ | `html_report` ✓ | html_report tests ✓ |
| FR-B-20 | API = library | — | `/v1/*` ◐ | `SuiteWorkflow` ◐ | e2e partial ✓ |
| FR-B-21 | Enable packs on suite | `suite_pack_selections` ⬜ | Studio ⬜ | presets UI only ◐ | ⬜ |
| FR-B-22 | Pack-sourced requirements | `requirements.source_pack_id` ⬜ | — | spec only ◐ | ⬜ |
| FR-B-23 | Report by control | `compliance_controls` ⬜ | report ⬜ | ⬜ | ⬜ |

## FR-P — pack / connector contract

| ID | Requirement | Design | Code |
|----|-------------|--------|------|
| FR-P-01 | Pack without backbone edits | [pack-interface.md](pack-interface.md) ✓ | ⬜ |
| FR-P-02 | Declare check + evidence kinds | pack-interface ✓ | ⬜ |
| FR-P-03 | Eight slots | pack-interface ✓ | ⬜ |
| FR-P-04 | Connectors separate | pack-interface ✓ | `connectors` table ◐, adapters ◐ |
| FR-P-05 | Reproducible freeze metadata | persistence schema ✓ | ⬜ |
| FR-P-06 | List installed packs/connectors | — | ⬜ |

## NFR-B

| ID | Constraint | Enforced |
|----|------------|----------|
| NFR-B-01 | Single node | ✓ default |
| NFR-B-02 | Scale assumptions | Documented; not load-tested |
| NFR-B-03 | 200 ms overhead | Not measured |
| NFR-B-04 | Deterministic re-score | Partial |
| NFR-B-05 | Durability | SQLite WAL ✓ |
| NFR-B-06 | Offline | Partial (LLM optional) |
| NFR-B-07 | CI boundary | ⬜ |
