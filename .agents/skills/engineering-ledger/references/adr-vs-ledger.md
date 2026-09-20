# ADR vs ledger

| | ADR (`docs/decisions/`) | Ledger DR (`decisions.md`) |
|--|-------------------------|----------------------------|
| **Scope** | Architecture forks | Tactical / reversible |
| **Audience** | Future architects | Future you + agents this week |
| **Format** | Numbered ADR, accepted status | DR-### append-only |
| **Examples** | Qdrant sparse unified, hybrid RRF | batch_size=128, --fast flag |
| **Lifecycle** | Supersede with new ADR | Supersede with new DR + link |

**Rule:** If unsure, start as DR. Promote to ADR when reversal cost is high.

Ledger **links to** ADRs; never copies full ADR text.

Lessons (LL) capture **process and debugging narrative** — neither ADR nor DR replaces a good LL after a surprise.
