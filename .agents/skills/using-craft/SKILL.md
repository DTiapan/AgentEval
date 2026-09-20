---
name: using-craft
description: >-
  Lifecycle router for Craft: pick exactly one phase-appropriate skill from upstream
  packs (Addy agent-skills, optional Superpowers). Read before non-trivial work.
  Use when starting features, unsure which skill applies, onboarding Craft, or
  adding Craft-native skills. Never copy upstream skill bodies into Craft.
---

# Using Craft

**Craft is the router + memory layer.** Implementation lives in upstream packs installed locally — see [craft.manifest.yaml](../../craft.manifest.yaml).

Full lifecycle map: [docs/lifecycle-map.md](../../docs/lifecycle-map.md)

---

## Before anything else (non-trivial work)

1. **Read ledger** — follow `engineering-ledger` read loop (`docs/engineering-ledger/INDEX.md` in target project).
2. **Identify phase** — Shape | Spec | ADR | Plan | Build | Debug | Verify | Review | Ship.
3. **Load exactly one primary skill** from table below (read full SKILL.md from disk).
4. **End session** — `engineering-ledger` write loop.

---

## When NOT to load any skill

Skip process skills for:

- Greetings, thanks, meta chat
- Single-file lookups ("where is X defined?")
- Config/env questions with a direct answer
- One-line typo fixes with zero design choice

---

## Anti-drift rules

| Rule | Detail |
|------|--------|
| One skill per phase | Never stack `interview-me` + `spec-driven-development` + `implement` |
| User slash wins | `/grill-me`, `/implement`, project AGENTS.md overrides win |
| No skill hoarding | Do not read Superpowers `using-superpowers` "1% chance" behavior |
| Reference only | Never copy upstream SKILL.md into Craft or project repos |
| Missing skill | Run manifest install, then read — do not improvise workflow |

---

## Resolve skill path

Search in order:

1. `.agents/skills/<name>/SKILL.md` (project-local, from `craft-install.sh` in project root)
2. `~/.agents/skills/<name>/SKILL.md` (user-global fallback)
3. Superpowers plugin cache (optional skills only)

If missing:

```bash
cd /path/to/your/project
bash /path/to/craft/scripts/craft-install.sh --profile all
```

---

## Phase → primary skill

| Phase | Primary skill | Pack | Optional ledger |
|-------|---------------|------|-----------------|
| Shape | `interview-me` if underspecified; else `idea-refine` | Addy | Create AP-### |
| Spec | `spec-driven-development` | Addy | DR-### for forks |
| ADR | `documentation-and-adrs` | Addy | Link DR ↔ ADR |
| Plan | `planning-and-task-breakdown` | Addy | AP ↔ tasks |
| Build | `incremental-implementation` | Addy | Update AP status; use for plan tickets too |
| Build (tests) | `test-driven-development` | Addy | Same session as build slice |
| Debug | `debugging-and-error-recovery` | Addy | LL-### after root cause |
| Verify | `constraint-driven-development` | Addy | `phases.md` evidence |
| Review | `code-review-and-quality` | Addy | INDEX session |
| Ship | `shipping-and-launch` | Addy | Rollback note in INDEX |

### Domain overlays (replace primary for that work)

| Work | Skill |
|------|-------|
| UI only | `frontend-ui-engineering` |
| Auth / input / secrets | `security-and-hardening` |
| Public API design | `api-and-interface-design` |
| Perf regression | `performance-optimization` |
| CI pipeline | `ci-cd-and-automation` |
| Project rules file | `context-engineering` |
| Commits / branches | `git-workflow-and-versioning` |

### Superpowers (optional — use instead of stacking Addy)

| When | Skill |
|------|-------|
| Greenfield creative exploration | `brainstorming` |
| Stuck bug, unknown layer | `systematic-debugging` |
| Before claiming "done" | `verification-before-completion` |

---

## Craft-native skills

| Skill | When |
|-------|------|
| **engineering-ledger** | Every non-trivial session (read + write) |
| **using-craft** | Routing, adding skills, structure questions |
| **craft-adopt** | Bootstrap Craft into a new project |
| **craft-promote** | Universal LL → new Craft skill |

---

## Adding a new Craft-native skill

Only for patterns **you** distilled (not forks of Addy):

1. Confirm [promotion-criteria.md](../engineering-ledger/references/promotion-criteria.md) or explicit user request
2. Run `craft-promote/scripts/check-duplicate.sh <term>`
3. Create `skills/<kebab-name>/SKILL.md` with triggers, workflow, verification, anti-patterns
4. Update [README.md](../../README.md) and `craft.manifest.yaml` `craft_native` list
5. Commit: `feat(skills): add <name> — <one line why>`

---

## Skill quality bar

Every Craft-native skill must define:

- **Triggers** — when to load (and when not to)
- **Workflow** — numbered steps with gates
- **Artifacts** — files produced and where
- **Verification** — how to know it was followed
- **Anti-patterns** — agent shortcuts to reject

---

## Initialize Craft in a Project

Like `git init`, initialize Craft directly in your target project repository:

```bash
cd /path/to/your/project
bash /path/to/craft/scripts/craft-install.sh --profile all
```

All skills and ledger templates will reside self-contained inside `.agents/skills/` and `docs/engineering-ledger/` in that project.

---

## Relationship to other packs

| Pack | Craft role |
|------|------------|
| addyosmani/agent-skills | Implementation engine — **referenced, not copied** |
| Superpowers | Optional debug/brainstorm/verify delegates |
| documentation-and-adrs | Irreversible forks below ledger DR layer |
| engineering-ledger | Running memory Craft owns |

Update upstream: `npx skills update addyosmani/agent-skills` — then re-run verify-deps if router behavior changed.
