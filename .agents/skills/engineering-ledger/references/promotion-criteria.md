# Promotion criteria — LL → Craft skill

When a **universal** lesson should become a Craft-native skill (not a copy of Addy).

---

## Required conditions (all)

1. **Scope:** `universal` on the LL entry
2. **Promotion candidate:** `yes`
3. **Reusability:** Appeared in ≥2 projects **OR** user explicitly requests promotion
4. **Actionable:** Contains verification gate + anti-patterns (Craft skill quality bar)
5. **Non-duplicate:** No existing Addy skill covers the same workflow — link upstream instead

---

## Promotion workflow

Run skill: `craft-promote`

1. Extract `General lesson`, evidence, anti-patterns from LL-###
2. Run `scripts/check-duplicate.sh` against `~/.agents/skills/*/SKILL.md`
3. Scaffold `skills/<kebab-name>/SKILL.md` in craft repo
4. Add `Originating lessons: LL-### (project/repo)` in skill references
5. Update craft README skills table
6. Mark LL status `promoted` with link to new skill

---

## Do not promote when

- Lesson is project-specific (`Scope: project`)
- Lesson duplicates Addy pack (update router table to point at Addy skill)
- Lesson is a one-off incident with no general mechanism
- Verification gate cannot be stated clearly

---

## After promotion

- Keep original LL in project ledger (history)
- Universal pattern now lives in Craft; future projects get it via skill install, not copy-paste
