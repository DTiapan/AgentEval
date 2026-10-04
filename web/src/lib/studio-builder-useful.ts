import type { BuilderStepCompletion } from "@/lib/studio-builder";
import type { BuilderStep } from "@/lib/studio-ux-config";
import { studioStepUx } from "@/lib/studio-ux-config";

export type StudioChecklistItem = {
  id: string;
  label: string;
  done: boolean;
};

export type StudioUsefulContext = {
  agentId: string;
  endpointUrl: string;
  requirementsText: string;
  hasPreview: boolean;
  hasFrozenManifest: boolean;
  probeOk?: boolean;
};

export function buildStudioChecklist(
  step: BuilderStep,
  ctx: StudioUsefulContext,
): StudioChecklistItem[] {
  const agentDone = ctx.agentId.trim().length > 0;
  const endpointDone = ctx.endpointUrl.trim().length > 0;
  const prdDone = ctx.requirementsText.trim().length > 0;

  switch (step) {
    case 1:
      return [{ id: "agent", label: "Agent ID (suite key)", done: agentDone }];
    case 2:
      return [
        { id: "agent", label: "Agent ID", done: agentDone },
        { id: "endpoint", label: "Target HTTP endpoint", done: endpointDone },
        { id: "prd", label: "PRD / capabilities markdown", done: prdDone },
        {
          id: "probe",
          label: "Endpoint probe succeeded",
          done: Boolean(ctx.probeOk),
        },
      ];
    case 3:
      return [
        {
          id: "preview",
          label: "Engine preview pack loaded",
          done: ctx.hasPreview || ctx.hasFrozenManifest,
        },
        {
          id: "inspect",
          label: "Review tests in inspector",
          done: ctx.hasPreview || ctx.hasFrozenManifest,
        },
      ];
    case 4:
      return [
        {
          id: "preview",
          label: "Preview or existing frozen pack",
          done: ctx.hasPreview || ctx.hasFrozenManifest,
        },
        {
          id: "freeze",
          label: "Persist suite to engine",
          done: ctx.hasFrozenManifest,
        },
      ];
    default:
      return [];
  }
}

/** Why the primary footer action is disabled — shown to the user inline. */
export function primaryActionBlocker(
  step: BuilderStep,
  completion: BuilderStepCompletion,
  ctx: StudioUsefulContext,
): string | null {
  const ux = studioStepUx(step);
  if (!ux.primaryAction) return null;

  switch (step) {
    case 1:
      return completion.step1 ? null : "Enter an agent ID to continue.";
    case 2:
      if (!completion.step1) return "Enter an agent ID.";
      if (!ctx.endpointUrl.trim()) return "Set the target HTTP endpoint.";
      if (!ctx.requirementsText.trim()) return "Add PRD or capability markdown.";
      return null;
    case 3:
      if (!completion.step2) {
        return "Complete Requirements & endpoint (step 2) before previewing.";
      }
      return null;
    case 4:
      if (!completion.step2) return "Complete connection and PRD on step Connect.";
      if (!ctx.hasPreview && !ctx.hasFrozenManifest) {
        return "Preview a pack before freezing a new suite.";
      }
      return null;
    default:
      return null;
  }
}

/** Next step to jump to when ahead of prerequisites; never returns `current`. */
export function suggestedStudioStep(
  current: BuilderStep,
  completion: BuilderStepCompletion,
): BuilderStep | null {
  if (current === 1 && completion.step1) return 2;
  // Step 2 complete → use footer "Preview pack", not a duplicate navigation hint
  if (current === 2 && completion.step2) return null;
  if (current === 3 && completion.step3) return 4;
  if (current === 4 && completion.step4) return 5;

  if (current > 1 && !completion.step1) return 1;
  if (current > 2 && !completion.step2) return 2;
  if (current > 3 && !completion.step3) return 3;
  if (current > 4 && !completion.step4) return 4;

  return null;
}
