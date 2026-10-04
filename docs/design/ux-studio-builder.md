# Studio — builder-first UX (Alex / U1)

> **Canonical onboarding stepper:** Name agent → Requirements & endpoint → Preview pack → Freeze suite → Run & CI gate.  
> **Code source of truth for copy:** `web/src/lib/studio-ux-config.ts`  
> **Step logic & deep links:** `web/src/lib/studio-builder.ts` (`#/console/studio/1` … `5`)

## Persona intent

**Alex (Senior AI Reliability Engineer)** — paste PRD + secured HTTP endpoint, preview set-cover pack, freeze, run regression in Assurance.

## Useful guidance (in-product)

- **Checklist** per step — what is done vs still needed (`studio-builder-useful.ts`).
- **Blocker copy** on disabled primary actions (endpoint, PRD, preview before freeze).
- **Suggested next step** when the user is on an earlier step but already qualifies.
- **Assurance** — primary **Execute Run** in the journey header until the first run; KPI/explorer hidden until then.
- **CI release gate** banner on Assurance after first run (`AssuranceCIGateBanner`) — blocked on failures or regressions vs baseline.

## Progressive disclosure

| Step | Primary surface | Advanced drawer |
|------|-----------------|-----------------|
| 1 | Agent ID | — |
| 2 | Endpoint, auth, PRD import | Domain packs, optimizer ceiling (k) |
| 3 | Tier cards, inspector (no connect form) | Re-preview after ceiling change |
| 4 | Freeze summary + persist CTA | Gap loop (after Assurance run) |
| 5 | Assurance Runs (separate tab) | — |

## Components (Phase 2 layout)

| Component | Role |
|-----------|------|
| `BuilderStepper` | Step navigation + completion from engine state |
| `StudioStepUsefulPanel` | Headline, checklist, blockers, demo fast path |
| `StudioAdvancedDrawer` | Optional tuning (packs, k, gap loop) |
| `StudioFreezeSummary` | Step 4 summary-first freeze panel |
| `StudioRunStepCard` | Step 5 handoff to Assurance |
| `StudioBuilderFooter` | Single primary CTA per step |
| `ConsoleBuilderJourney` | Shared stepper on Studio + Assurance |
| `AssuranceCIGateBanner` | Release gate from run + regression diff |

`Studio.tsx` still hosts inspector/coverage panels; extract further when adding new pack editors.

## Data provenance (no demo fiction)

Step completion derives only from:

- Form fields (agent ID, endpoint, PRD text)
- `POST /v1/suites/preview` → preview pack
- `GET /v1/suites/{id}` → frozen manifest / latest run
- Assurance run artifacts for gap loop eligibility

## Related docs

- [STITCH_PROMPTS.md](STITCH_PROMPTS.md) — stepper labels for design tools
- [ux-wireframes.md](ux-wireframes.md) — split-pane Studio + Assurance wireframes (§3–4)
