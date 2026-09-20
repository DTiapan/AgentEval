# Phase model

Phases are **project-defined** in `phases.md`. This reference is the default template for greenfield systems (e.g. RAG platform).

## Default phases

```
Shape → Spec/ADR → Build → Verify → Ship
```

| Phase | Entry criteria | Exit gate (evidence) |
|-------|----------------|----------------------|
| **Shape** | Idea approved | AP-### written; problem + non-goals stated |
| **Spec / ADR** | Shape done | SPEC or ADR for each architectural fork |
| **Build** | Spec/ADR for slice | Tests green for touched modules |
| **Verify** | Build done | Benchmark, smoke, or manual checklist in ledger |
| **Ship** | Verify done | CI green; INDEX updated; rollback noted |

## Status values

`planned` | `in_progress` | `blocked` | `done`

## Blocked protocol

When blocked, append to INDEX:

- blocker (fact, not guess)
- owner
- what was tried (link LL if lesson-worthy)

## Zero-to-one emphasis

For **0→1**, weight these ledger artifacts heavily:

1. **Problem framing** (Shape) — who, pain, success metric
2. **Component map** (AP) — what to build vs leverage OSS
3. **First proof** (Verify) — smallest real dataset / demo that proves thesis
4. **Lessons** (LL) — what you'd tell your past self

Code volume is not a phase gate.
