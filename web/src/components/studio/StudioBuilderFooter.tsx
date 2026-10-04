import React from "react";
import { Eye, RefreshCw, Save } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConsoleStickyActionBar } from "@/components/console/ConsoleStickyActionBar";
import type { BuilderStep } from "@/lib/studio-builder";
import type { BuilderStepCompletion } from "@/lib/studio-builder";
import { studioStepUx } from "@/lib/studio-ux-config";
import type { SuitePreviewResult } from "@/types";
import type { SuiteDetailResult } from "@/types";

interface StudioBuilderFooterProps {
  builderStep: BuilderStep;
  builderCompletion: BuilderStepCompletion;
  stepBlocker: string | null;
  agentId: string;
  isLoadingPreview: boolean;
  isSavingSuite: boolean;
  previewData: SuitePreviewResult | null;
  frozenDetail: SuiteDetailResult | null;
  /** Step 2 gate (endpoint + PRD) — used when running preview from step 3. */
  previewGateBlocker: string | null;
  onBack: () => void;
  onContinueStep1: () => void;
  onPreview: () => void;
  onContinueToFreeze: () => void;
  onFreeze: () => void;
}

export const StudioBuilderFooter: React.FC<StudioBuilderFooterProps> = ({
  builderStep,
  builderCompletion,
  stepBlocker,
  isLoadingPreview,
  isSavingSuite,
  previewData,
  frozenDetail,
  previewGateBlocker,
  onBack,
  onContinueStep1,
  onPreview,
  onContinueToFreeze,
  onFreeze,
}) => {
  return (
    <ConsoleStickyActionBar>
      {stepBlocker && (
        <p
          className="text-[11px] text-muted-foreground sm:max-w-md order-first sm:order-none"
          id="studio-step-blocker"
        >
          {stepBlocker}
        </p>
      )}
      {!stepBlocker && <span className="hidden sm:block sm:flex-1" />}
      <div className="flex flex-wrap items-center justify-end gap-2 sm:ml-auto">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          className="text-xs"
          disabled={builderStep <= 1}
          onClick={onBack}
        >
          Back
        </Button>
        <div className="flex flex-col gap-2 sm:flex-row sm:justify-end">
        {builderStep === 1 && (
          <Button type="button" size="sm" disabled={!builderCompletion.step1} onClick={onContinueStep1}>
            {studioStepUx(1).primaryAction}
          </Button>
        )}
        {builderStep === 2 && (
          <Button
            type="button"
            size="sm"
            onClick={onPreview}
            disabled={isLoadingPreview || Boolean(stepBlocker)}
            aria-describedby={stepBlocker ? "studio-step-blocker" : undefined}
          >
            {isLoadingPreview ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" aria-hidden />
            ) : (
              <Eye className="h-3.5 w-3.5 mr-2" aria-hidden />
            )}
            {studioStepUx(2).primaryAction}
          </Button>
        )}
        {builderStep === 3 &&
          (previewData?.optimized_pack?.tests?.length ||
          frozenDetail?.optimized_pack?.tests?.length ? (
            <>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onPreview}
                disabled={isLoadingPreview || Boolean(previewGateBlocker)}
              >
                {isLoadingPreview ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" aria-hidden />
                ) : (
                  <Eye className="h-3.5 w-3.5 mr-2" aria-hidden />
                )}
                Re-run preview
              </Button>
              <Button type="button" size="sm" onClick={onContinueToFreeze}>
                {studioStepUx(3).primaryAction}
              </Button>
            </>
          ) : (
            <Button
              type="button"
              size="sm"
              onClick={onPreview}
              disabled={isLoadingPreview || Boolean(previewGateBlocker)}
              aria-describedby={previewGateBlocker ? "studio-step-blocker" : undefined}
            >
              {isLoadingPreview ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" aria-hidden />
              ) : (
                <Eye className="h-3.5 w-3.5 mr-2" aria-hidden />
              )}
              {studioStepUx(2).primaryAction}
            </Button>
          ))}
        {builderStep === 4 && (
          <Button
            type="button"
            size="sm"
            onClick={onFreeze}
            disabled={isSavingSuite || Boolean(stepBlocker)}
            aria-describedby={stepBlocker ? "studio-step-blocker" : undefined}
          >
            {isSavingSuite ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" aria-hidden />
            ) : (
              <Save className="h-3.5 w-3.5 mr-2" aria-hidden />
            )}
            {frozenDetail ? "Update pack" : studioStepUx(4).primaryAction}
          </Button>
        )}
        </div>
      </div>
    </ConsoleStickyActionBar>
  );
};
