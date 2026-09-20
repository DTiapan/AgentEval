---
name: craft-adopt
description: >-
  Bootstrap Craft into a target project: scaffold engineering ledger, wire AGENTS.md,
  install domain skill profiles, verify upstream skills are installed locally. Use when starting a new project,
  onboarding Craft, or user says "adopt craft" / "set up the ledger".
---

# Craft Adopt

One workflow to make a project Craft-ready. **Does not copy upstream skills** — scaffolds project artifacts, installs domain skill profiles, and verifies local installs.

---

## Quick Start: 1-Click Domain Skill Installer

From your Craft clone, run the unified installer for any domain profile (`saas`, `engineering`, `product`, `uiux`, `all`):

```bash
# 1-Click Install for specific domain profile
bash scripts/craft-install.sh --profile saas --project-dir /path/to/project

# Or install all profiles
bash scripts/craft-install.sh --profile all
```

---

## When to use

- New greenfield or brownfield project adopting Craft
- User says: "adopt craft", "set up engineering ledger", "bootstrap craft", "install craft skills"
- After cloning Craft on a new machine (verify deps or setup domain profiles)

## When NOT to use

- Questions about what Craft is (read README)
- Adding a new skill to craft repo (use `craft-promote` or manual skill authoring)

---

## Domain Skill Profiles

Craft v0.2.0 organizes skills into purpose-built domain profiles:

| Profile | Focus Area | Key Skills |
|---|---|---|
| **`saas`** | SaaS, billing, marketing, multi-tenancy | API Design, Security, Frontend, UI/UX Pro, Launch |
| **`engineering`** | Production architecture & core dev | TDD, Security, Observability, Performance, CI/CD, Git |
| **`product`** | 0 to 1 discovery & PRD authoring | Idea Refine, Interview Me, Spec-Driven Dev, Task Breakdown |
| **`uiux`** | UI/UX & design systems | UI/UX Pro Max, Frontend UI, Browser DevTools, Web Guidance |

---

## Workflow

### 1. Verify machine dependencies & install profile

Run the 1-click installer:

```bash
bash scripts/craft-install.sh --profile saas
```

Or verify existing dependencies:

```bash
bash $CRAFT/skills/craft-adopt/scripts/verify-deps.sh
```

### 2. Scaffold ledger in target project

```bash
TARGET=/path/to/project
CRAFT=/path/to/craft   # local clone path

mkdir -p "$TARGET/docs/engineering-ledger"
mkdir -p "$TARGET/docs/decisions"

cp "$CRAFT/skills/engineering-ledger/templates/"* "$TARGET/docs/engineering-ledger/"
```

Initialize `INDEX.md` with project name, date, phase `Shape`, and link to AGENTS.md.

### 3. Wire AGENTS.md

Append (do not replace existing content):

```markdown
## Craft (orchestration + ledger)

- Non-trivial work: read `docs/engineering-ledger/INDEX.md` first.
- Route phases via `using-craft` skill (reference-only — do not copy Addy skills into this repo).
- Append DR/LL/INDEX before ending substantive sessions.
- Irreversible forks: ADR in `docs/decisions/` per `documentation-and-adrs`.
```

### 4. Optional project manifest pointer

Create `$TARGET/craft.project.yaml`:

```yaml
craft_version: "0.2.0"
profiles:
  - saas
  - engineering
ledger_path: docs/engineering-ledger
adr_path: docs/decisions
manifest_ref: DTiapan/craft craft.manifest.yaml
```

### 5. Initialize phases.md

Set first phase row to `in_progress` for current work (usually Shape or Build for brownfield).

---

## Verification gate

Before claiming adopt complete:

- [ ] `docs/engineering-ledger/` has INDEX, phases, attack-plans, decisions, lessons
- [ ] `docs/decisions/` exists (may be empty)
- [ ] AGENTS.md mentions Craft + ledger path
- [ ] `verify-deps.sh` passes (or 1-click installer executed)
- [ ] No upstream SKILL.md files copied into project

---

## Anti-patterns

| Don't | Do instead |
|-------|------------|
| Vendor Addy skills into `.agents/skills/` in git | Use `craft-install.sh` or `npx skills add` on each machine |
| Replace entire AGENTS.md | Append Craft section |
| Skip ledger on brownfield | Backfill INDEX with current phase + recent decisions |

---

## Artifacts

| File | Location |
|------|----------|
| Ledger scaffold | `docs/engineering-ledger/*` |
| ADR directory | `docs/decisions/` |
| Project pointer | `craft.project.yaml` (optional) |
| AGENTS.md section | Target project root |

See also [docs/adoption.md](../../docs/adoption.md).
