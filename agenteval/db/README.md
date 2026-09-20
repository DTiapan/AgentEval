# AgentEval database (SQLite v1)

- **DDL:** `schema.sql`
- **Design doc:** [docs/design/persistence-schema.md](../../docs/design/persistence-schema.md)
- **ADR:** [docs/decisions/ADR-004-sqlite-local-persistence.md](../../docs/decisions/ADR-004-sqlite-local-persistence.md)

Apply locally:

```bash
sqlite3 .agenteval/agenteval.db < agenteval/db/schema.sql
```

`SuiteRepository` is wired from `SuiteWorkflow` when SQLite is enabled:

```bash
export AGENTEVAL_USE_SQLITE=1
# optional: export AGENTEVAL_DATABASE_URL=sqlite:///.agenteval/agenteval.db
```

**Product flow (testing):** PRD + URL → preview/freeze/run via API → rows in SQLite (`suite_versions`, `assurance_runs`, `execution_steps`). Start the console with:

```bash
agenteval serve --with-ui
```

SQLite is **on by default** (`--no-sqlite` only for filesystem-only debugging). The header **SQLite** badge reflects `/health` → `persistence.sqlite_enabled`.

### Developer-only: import from JSON

Not part of user onboarding. For local fixtures or copying an old `.agenteval/suites` tree:

```bash
agenteval db import-suites
```
