export type BuilderStep = 1 | 2 | 3 | 4 | 5;

export type StudioBuilderStepUx = {
  step: BuilderStep;
  label: string;
  shortLabel: string;
  /** One-line goal for the step header */
  headline: string;
  /** Supporting copy under the stepper */
  description: string;
  /** Primary footer CTA label (step 5 uses in-card actions) */
  primaryAction?: string;
  /** Empty-state copy for the right-hand inspector */
  inspectorEmpty?: string;
};

/** Canonical builder flow — keep in sync with docs/design/ux-studio-builder.md */
export const STUDIO_BUILDER_STEP_UX: StudioBuilderStepUx[] = [
  {
    step: 1,
    label: "Name agent",
    shortLabel: "Agent",
    headline: "Identify the agent under test",
    description:
      "Choose a stable agent ID. It becomes the suite key in the API and Assurance runs.",
    primaryAction: "Continue",
    inspectorEmpty:
      "Name your agent first. Connection, PRD, and pack preview come in the next steps.",
  },
  {
    step: 2,
    label: "Requirements & endpoint",
    shortLabel: "Connect",
    headline: "Connect PRD and HTTP target",
    description:
      "Paste or import capabilities, set the outbound endpoint, and configure auth. Use Advanced for optimizer ceiling and gap loop.",
    primaryAction: "Preview pack",
    inspectorEmpty:
      "Complete connection details, then preview to generate tests from the engine.",
  },
  {
    step: 3,
    label: "Preview pack",
    shortLabel: "Preview",
    headline: "Review optimized pack",
    description:
      "Tune tiers and test ceiling, inspect CandidateTest JSON, then continue to freeze.",
    primaryAction: "Continue to freeze",
    inspectorEmpty: "Run Preview pack to load engine-generated tests in the inspector.",
  },
  {
    step: 4,
    label: "Freeze suite",
    shortLabel: "Freeze",
    headline: "Persist regression pack",
    description:
      "Freeze writes the pack to the engine. After a run, use Advanced or coverage gaps to extend the pool.",
    primaryAction: "Freeze suite",
    inspectorEmpty: "Frozen or preview tests appear here once a pack exists.",
  },
  {
    step: 5,
    label: "Run & CI gate",
    shortLabel: "Run",
    headline: "Execute assurance and gate release",
    description:
      "Run against the frozen pack, compare regressions vs baseline, and export evidence.",
  },
];

export const STUDIO_ADVANCED_UX = {
  title: "Advanced",
  description: "Optional tuning. Does not block the happy path.",
  sections: {
    domainPacks: {
      title: "Domain packs",
      hint: "Merge pack mandatory requirements at freeze (engine env + selection).",
    },
    optimizer: {
      title: "Optimizer ceiling (k)",
      hint: "Set-cover budget before preview. Re-run preview after changes.",
    },
    gapLoop: {
      title: "Coverage gap loop",
      hint: "Requires a completed Assurance run and uncovered critical tags.",
      action: "Close gaps from pool",
    },
  },
} as const;

export const ASSURANCE_JOURNEY_UX = {
  headline: "Assurance Runs",
  subtitle: "Black-box regression telemetry and deterministic invariant evidence.",
  description: "Step 5: execute against the frozen pack, then read pass rate, regression diff, and evidence.",
  backToStudioLabel: "Edit suite in Studio",
  primaryAction: "Execute Run",
  reportAction: "View HTML report",
  primaryHint: "Runs hit your target endpoint; verdicts and reports come from persisted engine output.",
  tabRuns: "Test runs & evidence",
  tabSignoff: "Requirements sign-off",
} as const;

export const ASSURANCE_CI_GATE_UX = {
  title: "CI release gate",
  statusOpen: "Open",
  statusBlocked: "Blocked",
  blockOnUnverifiable: false,
  open: (passRate: number) =>
    `No failing tests or regressions vs baseline. Pass rate ${passRate}%. Safe to promote when your policy matches.`,
  blockedFailures: (n: number) =>
    `${n} failing test${n === 1 ? "" : "s"}. Fix invariant violations before release.`,
  blockedRegressions: (n: number) =>
    `${n} regression${n === 1 ? "" : "s"} vs baseline. Resolve or accept drift before release.`,
  blockedUnverifiable: (n: number) =>
    `${n} unverifiable result${n === 1 ? "" : "s"}. Evidence missing; treat as policy risk.`,
} as const;

export function studioStepUx(step: BuilderStep): StudioBuilderStepUx {
  const found = STUDIO_BUILDER_STEP_UX.find((s) => s.step === step);
  if (!found) {
    return STUDIO_BUILDER_STEP_UX[0];
  }
  return found;
}

export function inspectorEmptyCopy(step: BuilderStep): string {
  return studioStepUx(step).inspectorEmpty ?? STUDIO_BUILDER_STEP_UX[1].inspectorEmpty!;
}
