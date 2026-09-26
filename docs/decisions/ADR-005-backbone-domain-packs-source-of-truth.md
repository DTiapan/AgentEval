# ADR-005: Domain-agnostic backbone, domain packs, and source of truth

**Status:** Accepted  
**Date:** 2026-09-25  
**Context:** [ADR-001](ADR-001-build-on-inspect-ai.md) (Inspect AI), [ADR-004](ADR-004-sqlite-local-persistence.md) (SQLite), [domain model](../design/domain-model.md), [PRD §9A](../design/PRD_SAAS_FULL.md), [idea one-pager §8](../ideas/agent-assurance-platform.md)

## Context

AgentEval grew without a domain model. Domain wording (refunds, tickets, orders)
leaks into about 15 backbone modules, and ADR-001 (Inspect AI) was never
implemented. The target market is now small regulated companies, served by
domain packs (fintech first, then insurance, then health). Before rewriting the
schema we must fix three things: how packs plug in, what is authoritative when
SQLite and Inspect logs both exist, and what a run is allowed to cover.

## Decision

1. **Backbone plus packs.** The backbone owns every entity in the
   [domain model](../design/domain-model.md) and contains no domain vocabulary.
   Domain packs are Python packages discovered through entry points (the
   mechanism Inspect AI already uses). A pack may fill any subset of these slots:
   options, domain terms, mandatory requirements, scenarios and personas,
   synthetic test data, evidence interpreters, checks, compliance mappings.
   Connectors (transport and evidence sources) are separate and domain-agnostic.
   In v1 packs ship with AgentEval; customer-written packs are out of scope.

2. **SQLite is the source of truth; Inspect logs are copied alongside.**
   Runs execute through Inspect (`Task` / `Sample` / `Solver` / `Scorer`). After
   each run the backbone writes runs, executions, evidence and verdicts to SQLite
   and stores the Inspect `EvalLog` file next to it, referenced by path and hash.
   The API, UI and reports read SQLite only. The log is kept for audit, for
   debugging with Inspect's own viewer, and for re-scoring.

3. **One target per run.** A run executes exactly one suite version against
   exactly one target. Comparing agents or environments is done by comparing
   runs against a chosen baseline (FR-B-18).

4. **Test data is stored, not regenerated.** Synthetic test data from packs or
   generators is produced once when test cases are proposed and frozen with the
   suite version. Runs replay stored data, so a run can be reproduced exactly.

## Alternatives considered

| Option | Why not |
|--------|---------|
| Inspect logs as source of truth | API and UI would parse log files for every query; no relational queries across runs; evidence sealing and `UNVERIFIABLE` are not Inspect concepts |
| SQLite only, no Inspect logs | Loses Inspect's viewer and the audit value of the raw log |
| Multi-target runs | Complicates the run, verdict and report model; baseline comparison already covers the need |
| Regenerate test data per run | Runs become irreproducible; a verdict change could come from the data, not the agent |
| Domain logic as backbone presets | The current state; it is what makes new domains require backbone edits |

## Consequences

- **Positive:** new domains need no backbone change (FR-P-01); every run is
  reproducible from stored rows; reports have one data source; Inspect's
  ecosystem (sandboxes, scorers, viewer) becomes available.
- **Negative:** two artifacts per run (row data plus log file) must be kept in
  sync and pruned together; a migration is needed from current JSON and SQLite
  tables; domain wording must be moved out of existing modules.
- **Follow-ups:** rewrite `persistence-schema.md` against the domain model;
  define the pack and connector interface; label each existing module keep,
  change, move or delete; add the CI boundary check (NFR-B-07).
