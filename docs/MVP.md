# AgentEval MVP (v0.2 product slice)

> **Goal:** One end-to-end path on Web Console + SQLite — no demo fiction on console surfaces ([no-demo-ui-data](../.cursor/rules/no-demo-ui-data.mdc), [DR-021](engineering-ledger/decisions.md#active-index)).

## User journey

1. **Studio** — Paste or upload PRD; set **agent id** + **HTTP endpoint URL**.
2. **Create suite** — `POST /v1/suites` freezes optimized pack + stores PRD in SQLite.
3. **Assurance** — `POST /v1/suites/{id}/runs` executes frozen pack (black-box HTTP).
4. **Results** — Verdicts, coverage, trajectories from API; **HTML report** download/open.

Tests are **generated at create/freeze**, not regenerated on each run ([DR-010](engineering-ledger/decisions.md#active-index)).

## Incremental delivery

| Slice | Scope | Status |
|-------|--------|--------|
| **M1** | Honest console (single workspace, no demo defaults on Studio/Assurance) | Done |
| **M2** | PRD file import + MVP flow strip + create requires endpoint | Done |
| **M3** | Post-create → Assurance only on new suite; clearer button labels | Done |
| **M4** | Report download + in-app embed (`ReportEmbedFrame`, frame headers) | Done |
| **M5** | Workspace API filter (when multi-tenant) | Roadmap |

## Verify MVP (manual)

```bash
cd web && npm run build && cd ..
agenteval serve
```

1. Open `/#/console/studio` — empty PRD unless you load an example or existing suite.
2. Create suite with PRD + `http://127.0.0.1:<port>/...` (see `examples/blackbox/`).
3. Assurance → **Execute Run** → see results from API.
4. Open or download HTML report for that run.

```bash
curl -s http://127.0.0.1:8766/v1/suites | jq '.suites | length'
curl -s http://127.0.0.1:8766/v1/suites/<agent_id>/runs/latest | jq '.passed, .failed'
```

## Out of scope for MVP

Multi-workspace SaaS, auth, harness YAML, gap-loop pool generation, CLI onboarding, OTel ingest.
