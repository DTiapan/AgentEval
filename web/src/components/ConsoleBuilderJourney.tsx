import React, { useMemo } from "react";
import { BuilderStepper } from "@/components/BuilderStepper";
import {
  type BuilderStep,
  type BuilderStepCompletion,
  deriveBuilderCompletion,
  navigateStudioBuilderStep,
} from "@/lib/studio-builder";
import { ASSURANCE_JOURNEY_UX } from "@/lib/studio-ux-config";
import { navigateConsoleView } from "@/lib/console-route";
import { Button } from "@/components/ui/button";
import { Play } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ConsoleBuilderJourneyProps {
  mode: "studio" | "assurance";
  studioStep?: BuilderStep;
  completion: BuilderStepCompletion;
  onStudioStepChange?: (step: BuilderStep) => void;
  agentLabel?: string;
  onAssurancePrimaryAction?: () => void;
  assurancePrimaryDisabled?: boolean;
  assurancePrimaryLoading?: boolean;
}

export const ConsoleBuilderJourney: React.FC<ConsoleBuilderJourneyProps> = ({
  mode,
  studioStep = 1,
  completion,
  onStudioStepChange,
  agentLabel,
  onAssurancePrimaryAction,
  assurancePrimaryDisabled,
  assurancePrimaryLoading,
}) => {
  const currentStep = mode === "assurance" ? 5 : studioStep;

  const handleStep = (step: BuilderStep) => {
    if (step === 5) {
      navigateConsoleView("assurance");
      return;
    }
    navigateConsoleView("studio");
    navigateStudioBuilderStep(step);
    onStudioStepChange?.(step);
  };

  return (
    <div className="mb-4">
      {mode === "assurance" && (
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-foreground">
                {ASSURANCE_JOURNEY_UX.headline}
              </h1>
              {agentLabel && (
                <Badge variant="outline" className="font-mono text-[10px]">
                  {agentLabel}
                </Badge>
              )}
            </div>
            <p className="text-xs text-muted-foreground mt-1 max-w-2xl">
              {ASSURANCE_JOURNEY_UX.subtitle}
            </p>
            <p className="text-[11px] text-muted-foreground mt-1 max-w-2xl">
              {ASSURANCE_JOURNEY_UX.description}
            </p>
            {onAssurancePrimaryAction && (
              <p className="text-[11px] text-muted-foreground mt-2">{ASSURANCE_JOURNEY_UX.primaryHint}</p>
            )}
          </div>
          <div className="flex flex-col gap-2 sm:items-end shrink-0">
            {onAssurancePrimaryAction && (
              <Button
                type="button"
                size="sm"
                disabled={assurancePrimaryDisabled || assurancePrimaryLoading}
                onClick={onAssurancePrimaryAction}
              >
                {assurancePrimaryLoading ? (
                  <span className="animate-pulse">{ASSURANCE_JOURNEY_UX.primaryAction}…</span>
                ) : (
                  <>
                    <Play className="h-3.5 w-3.5 fill-current mr-1.5" aria-hidden />
                    {ASSURANCE_JOURNEY_UX.primaryAction}
                  </>
                )}
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="text-xs"
              onClick={() => {
                navigateConsoleView("studio");
                navigateStudioBuilderStep(4);
              }}
            >
              {ASSURANCE_JOURNEY_UX.backToStudioLabel}
            </Button>
          </div>
        </div>
      )}
      <BuilderStepper
        currentStep={currentStep}
        completion={completion}
        onStepChange={handleStep}
      />
    </div>
  );
};

export function useAssuranceBuilderCompletion(input: {
  agentId: string;
  endpointUrl?: string | null;
  requirementsText?: string | null;
  hasFrozenManifest: boolean;
  hasAssuranceRun: boolean;
}): BuilderStepCompletion {
  return useMemo(
    () =>
      deriveBuilderCompletion({
        agentId: input.agentId,
        endpointUrl: input.endpointUrl ?? "",
        requirementsText: input.requirementsText ?? "",
        hasPreview: input.hasFrozenManifest,
        hasFrozenManifest: input.hasFrozenManifest,
        hasAssuranceRun: input.hasAssuranceRun,
      }),
    [input],
  );
}
