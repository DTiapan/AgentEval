import React from "react";
import { Sparkles } from "lucide-react";
import type { BuilderStep } from "@/lib/studio-ux-config";
import { studioStepUx } from "@/lib/studio-ux-config";
import type { StudioChecklistItem } from "@/lib/studio-builder-useful";
import { Button } from "@/components/ui/button";

interface StudioStepUsefulPanelProps {
  step: BuilderStep;
  checklist: StudioChecklistItem[];
  blocker: string | null;
  suggestedStep?: BuilderStep | null;
  onGoToSuggested?: () => void;
  onLoadDemo?: () => void;
}

/** Lightweight hints only — no large cards when the step is ready or complete. */
export const StudioStepUsefulPanel: React.FC<StudioStepUsefulPanelProps> = ({
  step,
  checklist,
  blocker,
  suggestedStep,
  onGoToSuggested,
  onLoadDemo,
}) => {
  const ux = studioStepUx(step);
  const requiredPending = checklist.filter((c) => !c.done && c.id !== "probe");
  const probePending = checklist.find((c) => c.id === "probe" && !c.done);

  if (blocker && requiredPending.length > 0) {
    return (
      <p
        className="mb-3 text-xs text-amber-900 dark:text-amber-100 bg-amber-500/10 border border-amber-500/25 rounded-md px-3 py-2"
        role="status"
      >
        <span className="font-medium">Before {ux.primaryAction ?? "continuing"}:</span> {blocker}
      </p>
    );
  }

  if (requiredPending.length > 0) {
    return (
      <p className="mb-3 text-xs text-muted-foreground" role="status">
        <span className="text-foreground font-medium">Still needed:</span>{" "}
        {requiredPending.map((c) => c.label).join(" · ")}
        {probePending ? (
          <span className="text-muted-foreground/80"> · Probe optional</span>
        ) : null}
      </p>
    );
  }

  if (step === 1 && onLoadDemo) {
    return (
      <div className="mb-3">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-[11px] gap-1.5 text-muted-foreground hover:text-foreground"
          onClick={onLoadDemo}
        >
          <Sparkles className="h-3 w-3" aria-hidden />
          Load demo agent
        </Button>
      </div>
    );
  }

  if (suggestedStep && onGoToSuggested && suggestedStep !== step) {
    return (
      <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
        <span>Ready for the next step.</span>
        <Button type="button" variant="link" size="sm" className="h-auto p-0 text-xs" onClick={onGoToSuggested}>
          Continue to {studioStepUx(suggestedStep).label}
        </Button>
      </div>
    );
  }

  return null;
};
