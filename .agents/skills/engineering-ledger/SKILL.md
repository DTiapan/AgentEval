---
name: engineering-ledger
description: >-
  Maintain a progressive engineering thought-process ledger (phases, attack plans,
  tactical decisions, lessons learned). Read before non-trivial work; append before
  ending a session. Use when starting features, debugging hard problems, finishing
  sprints, or when the user asks to capture reasoning, trade-offs, or lessons.
---

# Engineering Ledger

Capture **how** the project was built — not just the diff. Code shows *what*; this ledger shows *why*, *what we rejected*, and *what we learned*.

## When to use

- Starting a feature, sprint, or phase
- Choosing between approaches (libraries, architecture seams, optimization targets)
- After a bug, failed approach, or benchmark surprise
- End of session / before branch switch / before handoff
- User says: "log this decision", "capture lessons", "update the ledger", "what did we learn"

## When NOT to use

- Trivial one-line fixes with no design choice
- Pure questions with no project change
- Duplicating an ADR — link to ADR instead (see [references/adr-vs-ledger.md](references/adr-vs-ledger.md))

## Ledger location (default)

`docs/engineering-ledger/` in the **target project** (not in the craft repo):

| File | ID prefix | Purpose |
|------|-----------|---------|
| `INDEX.md` | — | Timeline + active phase + links |
| `phases.md` | PH- | North-star phase status and gates |
| `attack-plans.md` | AP- | Component attack strategy per unit of work |
| `decisions.md` | DR- | Tactical decisions (reversible) |
| `lessons.md` | LL- | Blameless lessons, failed hypotheses |

Scaffold from [templates/](templates/) if missing.

---

## Phase routing

For which upstream skill to load after the read loop, follow **`using-craft`** (reference-only router). Craft never copies Addy skill bodies.

---

## Read loop (mandatory before non-trivial work)

1. Read `INDEX.md` — current phase, last session summary, open questions.
2. Read active `AP-###` in `attack-plans.md` if one exists.
3. Scan `decisions.md` Active index for conflicts with the planned approach.
4. If conflict: **stop**, cite DR id, ask user how to proceed (respect / supersede).

Do not skip because "I remember the context."

---

## Write loop (mandatory before ending substantive work)

1. **Attack plan** — if new unit of work: add `AP-###` (goal, components, order, done-when).
2. **Decision** — if you chose between options: append `DR-###` (see template).
3. **Lesson** — if something failed, surprised, or generalized: append `LL-###` with **Scope** (`project` | `universal`) and **Promotion candidate**.
4. **Phase** — if a gate cleared: update `phases.md` status + evidence (tests, benchmark, ADR link).
5. **INDEX** — one paragraph: what happened, what's next, blockers.

Append only. Never delete entries. Supersede with `Supersedes: DR-###` / `Superseded-by: DR-###`.

---

## Entry formats

Full templates: [references/entry-templates.md](references/entry-templates.md)

### Decision (DR) — minimum fields

```markdown
### DR-003 — Batched benchmark ingest at 128
- **Date:** 2026-09-13
- **Status:** accepted
- **Context:** 10k BEIR ingest took ~13 min one-doc-at-a-time
- **Options:** (1) batch embed+upsert (2) --fast mock mode (3) both
- **Decision:** batch_size=128 + optional --fast for 100k+
- **Rationale:** ONNX dispatch overhead dominated; batching 160× Qdrant round-trips
- **Tradeoffs accepted:** Benchmark ingest path bypasses dedup at scale
- **Links:** commit 2ea19cb, ADR-013
```

### Lesson (LL) — minimum fields

```markdown
### LL-002 — BEIR doc_id must survive ingest
- **Date:** 2026-09-13
- **Status:** resolved
- **Scope:** universal
- **Promotion candidate:** yes
- **Category:** correctness
- **What happened:** 0% HitRate@5 on SciFact — hashed doc_id broke qrel match
- **Root cause:** ingest_text hashed source_uri, not BEIR id
- **Fix:** pass doc_id through ingest_text; relevant_sources fallback
- **General lesson:** Benchmark labels must match indexed metadata, not convenience hashes
```

**Scope:** `project` = stays in this repo. `universal` = candidate for `craft-promote` (see [references/promotion-criteria.md](references/promotion-criteria.md)).

### Attack plan (AP)

```markdown
### AP-001 — Sample corpus + rerank metrics
- **Status:** done
- **Goal:** Prove full pipeline quality story on real formats
- **Components:** PDF/DOCX sample, rerank HitRate@5, config defaults, CI gate
- **Order:** corpus → rerank metrics → config → CI
- **Done when:** 93 tests green, README table updated
```

---

## Phase model

See [references/phase-model.md](references/phase-model.md). Default gates:

| Phase | Gate (examples) |
|-------|-----------------|
| Shape | Problem framed, AP written, out-of-scope listed |
| Spec / ADR | ADR or spec exists for forks |
| Build | Tests green for touched seams |
| Verify | Benchmark or smoke evidence recorded in ledger |
| Ship | CI green, ledger INDEX updated |

---

## Promotion to ADR

Promote DR → ADR when **any** of:

- Reversal would require migration or multi-day rework
- Choice affects multiple teams or external contracts
- User explicitly requests ADR

Create ADR in project's `docs/decisions/`; link both ways.

---

## Anti-patterns

| Don't | Do instead |
|-------|------------|
| Dump chat transcripts into the ledger | Curated DR/LL with ids |
| Rewrite old entries | Append superseding DR |
| Skip ledger because ADRs exist | ADRs = forks; ledger = narrative |
| Log every file edit | Log choices with alternatives |
| Start coding before read loop | Read INDEX + active AP first |

---

## Verification

Before claiming ledger work complete:

- [ ] INDEX reflects current state
- [ ] New entries have sequential ids
- [ ] LL entries include Scope; universal lessons mark Promotion candidate
- [ ] Active index sections updated at top of decisions/lessons files
- [ ] Links to commits, ADRs, or PRs where applicable
- [ ] Phase status in `phases.md` matches evidence (tests, benchmark, CI)
