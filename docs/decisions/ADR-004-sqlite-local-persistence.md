# ADR-004: SQLite for local and single-tenant persistence (v1)

**Status:** Accepted  
**Date:** 2026-09-21  
**Context:** [Black-box pipeline](ADR-003-black-box-test-intelligence-pipeline.md), [DR-012](../engineering-ledger/decisions.md) (API/library first), [no-demo-ui-data](../../.cursor/rules/no-demo-ui-data.mdc)

## Context

Today, suites and runs live as JSON under `.agenteval/suites/{agent_id}/` (`SuiteStore`). That works for CLI and single-user dev but does not support:

- Multi-tenant **workspaces**, **users**, and RBAC (SaaS PRD)
- Queryable **run history**, **per-test results**, and **execution steps** (trajectory replay)
- **Audit** events (freeze suite, run, API key use)
- A single code path for **HTTP API**, **web UI**, and **CI** without ad hoc file scans

We need a real persistence layer whose schema matches Pydantic domain models, with a credible path to PostgreSQL later.

## Decision

1. **Use SQLite** as the default embedded database for local dev, CI, and early single-node deploys.
   - File path: `{data_dir}/agenteval.db` (default `data_dir = .agenteval`, overridable via `AGENTEVAL_DATA_DIR` or `DATABASE_URL=sqlite:///...`).
   - Enable `PRAGMA foreign_keys = ON` and **WAL** journal mode for concurrent readers (API + CLI).

2. **Relational schema** for tenancy, agents, frozen suites, runs, test results, and execution steps. Large immutable blobs (full candidate pool, PRD text) may stay in **JSON TEXT** columns on `suite_versions` until size forces object storage.

3. **Product path (testing / pre-launch):** User uploads **requirements + URL** → engine generates the test pack → **persist in SQLite** via **`SuiteRepository`**. That is the source of truth for Studio, Assurance, and Replay. No legacy-user migration is required.

4. **`SuiteStore` JSON** under `.agenteval/suites/` is **optional** (debug export, CLI compatibility, unit tests)—not the onboarding story. `agenteval db import-suites` remains a **developer utility** only, not part of the user flow.

5. **Implementation note:** Transitional dual-write (JSON + SQLite) may exist briefly in code; target is **SQLite-primary writes** when persistence is enabled.

6. **Postgres later:** same logical schema; swap driver and use native `JSONB` where SQLite uses `TEXT` JSON. No sharding until measured need (data-storage skill: single relational node first).

## Consequences

**Positive**

- Trajectory replay and assurance UI read **persisted** `execution_steps`, not reconstructed client fiction.
- Workspace-scoped agents and runs align with SaaS PRD and `agenteval.app` onboarding.
- One query model for “latest run”, “runs for agent”, “failures in last N runs”.

**Negative**

- Tests need DB fixtures or in-memory SQLite; avoid coupling product UX to filesystem layout.
- SQLite write concurrency limited (one writer); fine for v1; API run endpoint serializes per process or uses queue if needed.

**Not in v1 schema**

- Full OTel span ingest (separate table later: `trace_spans` with OpenInference shape)
- Billing meters, SSO identity provider tables (add with auth slice)

## Implementation status (2026-09-24)

- Implemented as decided: SQLite-primary writes via `SuiteRepository`, WAL and
  foreign keys enabled (`db/connection.py`), JSON `SuiteStore` only when SQLite
  is disabled.
- Tenancy tables (`users`, `workspace_members`, `api_keys`, `audit_events`) are
  defined in `schema.sql` but no code writes to them; they are speculative until
  the auth slice.
- The schema models storage, not the domain: requirements are stored as a text
  blob plus fingerprint, with no Requirement or Acceptance criterion entity.
- Open question for ADR-005: Inspect writes its own eval logs. We must decide
  whether SQLite stays the product source of truth (mirrored from Inspect via
  a logging hook) or Inspect logs become primary.

## References

- Physical schema and DDL: [persistence-schema.md](../design/persistence-schema.md)
- Current models: `agenteval/planning/models.py` (`SuiteRunReport`, `TestCaseResult`, `ExecutionStep`)
