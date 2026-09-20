---
name: craft-promote
description: >-
  Promote a universal engineering-ledger lesson (LL) into a new Craft-native skill.
  Use when LL scope is universal, promotion candidate is yes, and the pattern should
  apply across projects. Checks for duplicates against Addy pack before creating skill.
---

# Craft Promote

Convert **universal** ledger lessons into reusable Craft skills. This creates **new** Craft-native workflows — never copies Addy skill bodies.

Criteria: [promotion-criteria.md](../engineering-ledger/references/promotion-criteria.md)

---

## When to use

- LL entry has `Scope: universal` and `Promotion candidate: yes`
- Same pattern appeared in ≥2 projects OR user explicitly requests promotion
- Pattern is not covered by existing Addy skill

## When NOT to use

- `Scope: project` lessons (stay in project ledger)
- Duplicate of Addy skill (update `using-craft` router to link Addy instead)
- One-off incident with no general mechanism

---

## Workflow

### 1. Extract from LL entry

From project `docs/engineering-ledger/lessons.md`, gather:

- Title → skill name (kebab-case)
- General lesson → skill purpose
- Root cause / fix → workflow steps
- Evidence → verification gate
- What went wrong → anti-patterns table

### 2. Dedup check

```bash
bash skills/craft-promote/scripts/check-duplicate.sh "<proposed-skill-name>"
bash skills/craft-promote/scripts/check-duplicate.sh "<key phrase from general lesson>"
```

If duplicate found in Addy → **stop**. Add router row in `using-craft` pointing to existing skill; mark LL `promoted-via-link: <skill-name>`.

### 3. Scaffold skill

Create `skills/<kebab-name>/SKILL.md`:

```markdown
---
name: <kebab-name>
description: >-
  <one line — triggers for agent>
---

# <Title>

## When to use
...

## When NOT to use
...

## Workflow
1. ...

## Verification
- [ ] ...

## Anti-patterns
| Don't | Do instead |
...

## Originating lessons
- LL-### from <project/repo> (YYYY-MM-DD)
```

Optional: `references/` for long examples.

### 4. Register skill

- Add to [README.md](../../README.md) skills table
- Add to `craft.manifest.yaml` under `craft_native`
- Add router row in `using-craft/SKILL.md` if phase-specific

### 5. Update source LL

In project ledger, set:

```markdown
- **Status:** promoted
- **Promoted to:** craft/skills/<kebab-name>
```

---

## Verification gate

- [ ] SKILL.md has frontmatter, triggers, workflow, verification, anti-patterns
- [ ] Dedup script run; no Addy overlap (or linked instead)
- [ ] Originating LL ids cited
- [ ] README + manifest updated
- [ ] No copied text from upstream packs

---

## Anti-patterns

| Don't | Do instead |
|-------|------------|
| Fork Addy skill into Craft | Reference Addy in router |
| Promote without verification gate | Write testable exit criteria |
| Delete original LL | Mark promoted; keep history |
