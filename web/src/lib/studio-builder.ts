import { STUDIO_BUILDER_STEP_UX, type BuilderStep } from "@/lib/studio-ux-config";

export type { BuilderStep };

export const BUILDER_STEPS = STUDIO_BUILDER_STEP_UX.map(
  ({ step, label, shortLabel }) => ({ step, label, shortLabel }),
);

export type BuilderStepCompletion = {
  step1: boolean;
  step2: boolean;
  step3: boolean;
  step4: boolean;
  step5: boolean;
};

export function deriveBuilderCompletion(input: {
  agentId: string;
  endpointUrl: string;
  requirementsText: string;
  hasPreview: boolean;
  hasFrozenManifest: boolean;
  hasAssuranceRun: boolean;
}): BuilderStepCompletion {
  const step1 = input.agentId.trim().length > 0;
  const step2 =
    step1 &&
    input.endpointUrl.trim().length > 0 &&
    input.requirementsText.trim().length > 0;
  const step3 = step2 && (input.hasPreview || input.hasFrozenManifest);
  const step4 = step2 && input.hasFrozenManifest;
  const step5 = step4 && input.hasAssuranceRun;

  return { step1, step2, step3, step4, step5 };
}

export function isStepComplete(
  step: BuilderStep,
  completion: BuilderStepCompletion,
): boolean {
  switch (step) {
    case 1:
      return completion.step1;
    case 2:
      return completion.step2;
    case 3:
      return completion.step3;
    case 4:
      return completion.step4;
    case 5:
      return completion.step5;
    default:
      return false;
  }
}

/** Furthest step the user may jump to (completed steps + next incomplete). */
export function maxReachableStep(completion: BuilderStepCompletion): BuilderStep {
  if (!completion.step1) return 1;
  if (!completion.step2) return 2;
  if (!completion.step3) return 3;
  if (!completion.step4) return 4;
  return 5;
}

export function canOpenBuilderStep(
  target: BuilderStep,
  completion: BuilderStepCompletion,
): boolean {
  return target <= maxReachableStep(completion);
}

export function readStudioBuilderStepFromHash(): BuilderStep | null {
  if (typeof window === "undefined") return null;
  const hash = window.location.hash.replace(/^#/, "");
  const match = hash.match(/\/studio\/([1-5])(?:\/)?$/);
  if (!match) return null;
  return Number(match[1]) as BuilderStep;
}

export function hashForStudioBuilderStep(step: BuilderStep): string {
  return `#/console/studio/${step}`;
}

export function navigateStudioBuilderStep(step: BuilderStep): void {
  window.location.hash = hashForStudioBuilderStep(step);
}

export function inferInitialBuilderStep(completion: BuilderStepCompletion): BuilderStep {
  const fromHash = readStudioBuilderStepFromHash();
  if (fromHash && canOpenBuilderStep(fromHash, completion)) {
    return fromHash;
  }
  if (!completion.step1) return 1;
  if (!completion.step2) return 2;
  if (!completion.step3) return 3;
  if (!completion.step4) return 4;
  return 5;
}
