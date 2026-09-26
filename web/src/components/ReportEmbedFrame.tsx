import React, { useEffect, useState } from "react";
import { AlertCircle, RefreshCw } from "lucide-react";
import { getSuiteReportUrl } from "../api";
import { Button } from "@/components/ui/button";

type ReportEmbedFrameProps = {
  agentId: string;
  runId: string;
  theme: "light" | "dark";
  active: boolean;
};

/** In-app report viewer — loads GET /v1/suites/{id}/report?embed=true only when modal is open. */
export const ReportEmbedFrame: React.FC<ReportEmbedFrameProps> = ({
  agentId,
  runId,
  theme,
  active,
}) => {
  const [loadState, setLoadState] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [reloadToken, setReloadToken] = useState(0);

  const src =
    active
      ? `${getSuiteReportUrl(agentId, runId, { embed: true, theme })}&_r=${reloadToken}`
      : undefined;

  useEffect(() => {
    if (!active) {
      setLoadState("idle");
      return;
    }
    setLoadState("loading");
  }, [active, agentId, runId, theme, reloadToken]);

  if (!active) {
    return null;
  }

  return (
    <div className="relative flex min-h-0 flex-1 flex-col bg-background">
      {loadState === "loading" && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )}
      {loadState === "error" && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-background p-6 text-center">
          <AlertCircle className="h-8 w-8 text-amber-500" />
          <p className="text-sm text-foreground">Report could not load in the viewer.</p>
          <p className="text-xs text-muted-foreground font-mono max-w-md break-all">{src}</p>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => setReloadToken((n) => n + 1)}
          >
            Retry
          </Button>
        </div>
      )}
      {src && (
        <iframe
          key={`${agentId}-${runId}-${reloadToken}`}
          src={src}
          title="AgentEval assurance report"
          className="min-h-[65vh] h-full w-full flex-1 border-0"
          onLoad={() => setLoadState("ready")}
          onError={() => setLoadState("error")}
        />
      )}
    </div>
  );
};
