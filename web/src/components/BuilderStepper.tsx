import React from "react";
import { Check } from "lucide-react";
import {
  BUILDER_STEPS,
  type BuilderStep,
  type BuilderStepCompletion,
  canOpenBuilderStep,
  isStepComplete,
} from "@/lib/studio-builder";
import { cn } from "@/lib/utils";

interface BuilderStepperProps {
  currentStep: BuilderStep;
  completion: BuilderStepCompletion;
  onStepChange: (step: BuilderStep) => void;
}

export const BuilderStepper: React.FC<BuilderStepperProps> = ({
  currentStep,
  completion,
  onStepChange,
}) => {
  return (
    <nav aria-label="Suite setup progress" className="mb-0">
      <ol className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        {BUILDER_STEPS.map(({ step, label, shortLabel }, index) => {
          const complete = isStepComplete(step, completion);
          const isCurrent = currentStep === step;
          const reachable = canOpenBuilderStep(step, completion);
          const isLast = index === BUILDER_STEPS.length - 1;

          return (
            <li
              key={step}
              className={cn(
                "flex flex-1 min-w-0 items-start gap-2 sm:flex-col sm:items-stretch",
                !isLast && "sm:pr-2",
              )}
            >
              <div className="flex items-center gap-2 sm:w-full">
                <button
                  type="button"
                  disabled={!reachable}
                  onClick={() => reachable && onStepChange(step)}
                  aria-current={isCurrent ? "step" : undefined}
                  aria-label={
                    complete
                      ? `${label}, completed`
                      : isCurrent
                        ? `${label}, current step`
                        : reachable
                          ? `Go to ${label}`
                          : `${label}, not available yet`
                  }
                  className={cn(
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition-[color,background-color,border-color] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
                    complete && !isCurrent
                      ? "border-primary/40 bg-primary/10 text-primary"
                      : isCurrent
                        ? "border-primary bg-primary text-primary-foreground"
                        : reachable
                          ? "border-border bg-card text-muted-foreground hover:border-primary/40 hover:text-foreground"
                          : "border-border/60 bg-muted/30 text-muted-foreground/60 cursor-not-allowed",
                  )}
                >
                  {complete && !isCurrent ? (
                    <Check className="h-4 w-4" aria-hidden />
                  ) : (
                    <span className="font-mono tabular-nums">{step}</span>
                  )}
                </button>
                <div className="min-w-0 sm:hidden">
                  <p
                    className={cn(
                      "text-xs font-medium truncate",
                      isCurrent ? "text-foreground" : "text-muted-foreground",
                    )}
                  >
                    {shortLabel}
                  </p>
                </div>
                {!isLast && (
                  <div
                    className="hidden sm:block flex-1 h-px bg-border mt-4 mx-1 min-w-[8px]"
                    aria-hidden
                  />
                )}
              </div>
              <div className="hidden sm:block pl-0 pt-1 min-w-0">
                <p
                  className={cn(
                    "text-[11px] font-medium leading-tight",
                    isCurrent ? "text-foreground" : "text-muted-foreground",
                  )}
                >
                  <span className="font-mono text-[10px] text-muted-foreground mr-1">
                    {step}.
                  </span>
                  {label}
                </p>
              </div>
            </li>
          );
        })}
      </ol>
    </nav>
  );
};
