import React from "react";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { BuilderStep } from "@/lib/studio-ux-config";

interface StudioFreezeSummaryProps {
  agentId: string;
  packTestCount: number;
  endpoint: string;
  frozenVersion?: number;
  packProvenance: string | null;
  previewTestCount?: number;
  onEditConnection: () => void;
  onEditPreview: () => void;
}

export const StudioFreezeSummary: React.FC<StudioFreezeSummaryProps> = ({
  agentId,
  packTestCount,
  endpoint,
  frozenVersion,
  packProvenance,
  previewTestCount,
  onEditConnection,
  onEditPreview,
}) => {
  return (
    <div className="rounded-lg border border-primary/25 bg-primary/5 p-4 space-y-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-foreground">Ready to freeze</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Persist this pack to the engine for Assurance runs and regression diff.
          </p>
        </div>
        {packProvenance && (
          <Badge variant="outline" className="font-mono text-[10px]">
            {packProvenance}
          </Badge>
        )}
      </div>
      <dl className="grid gap-2 text-xs sm:grid-cols-2">
        <div>
          <dt className="text-muted-foreground">Agent</dt>
          <dd className="font-mono font-medium text-foreground">{agentId}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Pack size</dt>
          <dd className="font-mono font-medium text-foreground tabular-nums">
            {packTestCount || previewTestCount || 0} tests
            {frozenVersion != null ? ` · v${frozenVersion}` : ""}
          </dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-muted-foreground">Target endpoint</dt>
          <dd className="font-mono text-[11px] break-all text-foreground">{endpoint || "n/a"}</dd>
        </div>
      </dl>
      <div className="flex flex-wrap gap-2 pt-1">
        <Button type="button" variant="outline" size="sm" className="h-8 text-[11px]" onClick={onEditConnection}>
          <Pencil className="h-3 w-3 mr-1.5" aria-hidden />
          Edit connection
        </Button>
        <Button type="button" variant="ghost" size="sm" className="h-8 text-[11px]" onClick={onEditPreview}>
          Back to preview
        </Button>
      </div>
    </div>
  );
};

export function studioCardTitleForStep(step: BuilderStep): string {
  switch (step) {
    case 1:
      return "Name your agent";
    case 2:
      return "Connect & specify";
    case 3:
      return "Preview & tune pack";
    case 4:
      return "Freeze regression pack";
    default:
      return "Agent specification";
  }
}
