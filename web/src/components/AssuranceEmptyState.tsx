import React from "react";
import { FlaskConical, Play, PlusCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { navigateConsoleView } from "@/lib/console-route";

type Variant = "no-suites" | "no-run";

type AssuranceEmptyStateProps = {
  variant: Variant;
  agentId?: string;
  packSize?: number;
  onExecuteRun?: () => void;
  isRunning?: boolean;
};

export const AssuranceEmptyState: React.FC<AssuranceEmptyStateProps> = ({
  variant,
  agentId,
  packSize,
  onExecuteRun,
  isRunning,
}) => {
  if (variant === "no-suites") {
    return (
      <Card className="border-border bg-card shadow-xs">
        <CardContent className="flex flex-col items-center justify-center py-16 px-6 text-center">
          <FlaskConical className="mb-4 h-10 w-10 text-muted-foreground/50" />
          <h2 className="text-sm font-semibold text-foreground">No assurance suites yet</h2>
          <p className="mt-2 max-w-md text-xs text-muted-foreground">
            Create a frozen test pack in Studio from your PRD and agent HTTP endpoint. Runs and
            reports use engine state only — nothing is simulated here.
          </p>
          <Button
            type="button"
            className="mt-6"
            onClick={() => navigateConsoleView("studio")}
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            Open Studio
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-card shadow-xs">
      <CardContent className="flex flex-col items-center justify-center py-16 px-6 text-center">
        <Play className="mb-4 h-10 w-10 text-primary/80" />
        <h2 className="text-sm font-semibold text-foreground">Ready to run assurance</h2>
        <p className="mt-2 max-w-md text-xs text-muted-foreground">
          Suite <span className="font-mono text-foreground">{agentId}</span> is frozen with{" "}
          <span className="font-mono text-foreground">{packSize ?? 0}</span> tests. Execute a run
          against your target endpoint to populate verdicts, coverage, and the HTML report.
        </p>
        {onExecuteRun && (
          <Button
            type="button"
            className="mt-6"
            onClick={onExecuteRun}
            disabled={isRunning}
          >
            {isRunning ? (
              <span className="animate-pulse">Running…</span>
            ) : (
              <>
                <Play className="mr-2 h-4 w-4 fill-current" />
                Execute Run
              </>
            )}
          </Button>
        )}
      </CardContent>
    </Card>
  );
};
