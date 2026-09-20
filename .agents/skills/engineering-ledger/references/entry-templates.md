# Entry templates

Copy blocks into the appropriate file above the `## Archive` marker.

## DR template

```markdown
### DR-NNN — Title
- **Date:** YYYY-MM-DD
- **Status:** proposed | accepted | superseded
- **Supersedes:** DR-NNN (optional)
- **Context:** Situation forcing a choice
- **Options:**
  1. Option A — pros / cons
  2. Option B — pros / cons
- **Decision:** What we chose
- **Rationale:** Why (evidence, not vibe)
- **Tradeoffs accepted:** What we gave up
- **Links:** commit, PR, ADR, benchmark
```

## LL template

```markdown
### LL-NNN — Title
- **Date:** YYYY-MM-DD
- **Status:** open | resolved | promoted
- **Scope:** project | universal
- **Promotion candidate:** yes | no
- **Category:** correctness | performance | process | tooling
- **What happened:** Observable symptom
- **Hypothesis:** What we thought
- **Evidence:** What proved/disproved it
- **Root cause:** Actual mechanism
- **Fix:** What changed
- **General lesson:** Reusable principle
- **Links:** DR-NNN, commit, test
```

## AP template

```markdown
### AP-NNN — Title
- **Date:** YYYY-MM-DD
- **Status:** planned | in_progress | done | cancelled
- **Goal:** One sentence outcome
- **Problem framing:** Restate the problem in your words
- **Components to attack:**
  1. Component — why this order
  2. ...
- **Out of scope:** Explicit exclusions
- **Done when:** Verifiable checklist
- **Links:** phase, ADR, PR
```

## INDEX session block

```markdown
## YYYY-MM-DD — Session title
**Phase:** Shape | Spec | Build | Verify | Ship  
**Summary:** 2–4 sentences  
**Decisions:** DR-NNN  
**Lessons:** LL-NNN  
**Next:** Single next action + gate  
**Blockers:** None | description  
```
