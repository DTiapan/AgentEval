import React from "react";
import { Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { studioStepUx } from "@/lib/studio-ux-config";
import type { SuiteDetailResult } from "@/types";

interface StudioRunStepCardProps {
  agentId: string;
  packTestCount: number;
  frozenDetail: SuiteDetailResult | null;
  endpointUrl: string;
  onOpenAssurance: () => void;
  onEditFrozenPack: () => void;
}

export const StudioRunStepCard: React.FC<StudioRunStepCardProps> = ({
  agentId,
  packTestCount,
  frozenDetail,
  endpointUrl,
  onOpenAssurance,
  onEditFrozenPack,
}) => {
  const ux = studioStepUx(5);

  return (
    <Card className="border border-border bg-card shadow-xs">
      <CardHeader className="p-5 border-b border-border/50">
        <CardTitle className="text-base font-semibold">{ux.headline}</CardTitle>
        <p className="text-xs text-muted-foreground mt-1">{ux.description}</p>
      </CardHeader>
      <CardContent className="p-5 space-y-4">
        {!frozenDetail?.manifest ? (
          <p className="text-sm text-muted-foreground">
            Freeze a suite in step 4 before running assurance against your agent endpoint.
          </p>
        ) : (
          <>
            <dl className="grid gap-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground text-xs">Agent</dt>
                <dd className="font-mono font-medium">{agentId}</dd>
              </div>
              <div>
                <dt className="text-muted-foreground text-xs">Frozen pack</dt>
                <dd className="font-mono font-medium tabular-nums">
                  v{frozenDetail.manifest.version} · {packTestCount} test
                  {packTestCount === 1 ? "" : "s"}
                </dd>
              </div>
              <div className="sm:col-span-2">
                <dt className="text-muted-foreground text-xs">Endpoint</dt>
                <dd className="font-mono text-xs break-all">
                  {frozenDetail.manifest.endpoint_profile || endpointUrl || "n/a"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground text-xs">Last assurance run</dt>
                <dd className="font-mono text-xs">
                  {frozenDetail.latest_run?.run_id ?? "No runs yet. Start in Assurance."}
                </dd>
              </div>
            </dl>
            <div className="flex flex-wrap gap-3 pt-2">
              <Button type="button" onClick={onOpenAssurance}>
                <Play className="mr-2 h-3.5 w-3.5 fill-current" aria-hidden />
                Open Assurance Runs
              </Button>
              <Button type="button" variant="outline" onClick={onEditFrozenPack}>
                Edit frozen pack
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};
