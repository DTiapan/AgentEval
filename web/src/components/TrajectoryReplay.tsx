import React, { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ChevronFirst,
  ChevronLast,
  ChevronLeft,
  ChevronRight,
  FastForward,
  Pause,
  Play,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CodeViewer } from "@/components/ui/code-viewer";
import { loadReplaySession, navigateToAssurance, type ReplaySession } from "@/lib/replay-session";
import {
  panelContentForStep,
  trajectoryFromResult,
} from "@/lib/trajectory";
import type { ExecutionStep } from "@/types";
import { DEMO_AGENT_ID } from "@/lib/product";
import { useWorkspace } from "@/context/WorkspaceContext";

function panelEditorHeight(text: string): string {
  const lines = Math.max(1, text.split("\n").length);
  const px = Math.min(220, Math.max(88, lines * 18 + 28));
  return `${px}px`;
}

interface TrajectoryReplayProps {
  onMissingSession?: () => void;
}

export const TrajectoryReplay: React.FC<TrajectoryReplayProps> = ({
  onMissingSession,
}) => {
  const { activeAgentId, setActiveAgentId } = useWorkspace();
  const [session, setSession] = useState<ReplaySession | null>(() => loadReplaySession());
  const [stepIndex, setStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const model = useMemo(
    () => (session ? trajectoryFromResult(session.test) : null),
    [session]
  );

  useEffect(() => {
    if (!session) {
      onMissingSession?.();
    }
  }, [session, onMissingSession]);

  useEffect(() => {
    if (!isPlaying || !model) return;
    const timer = window.setInterval(() => {
      setStepIndex((idx) => {
        if (idx >= model.steps.length - 1) {
          setIsPlaying(false);
          return idx;
        }
        return idx + 1;
      });
    }, 900);
    return () => window.clearInterval(timer);
  }, [isPlaying, model]);

  useEffect(() => {
    setSession(loadReplaySession());
  }, []);

  useEffect(() => {
    if (session?.agentId && session.agentId !== activeAgentId) {
      setActiveAgentId(session.agentId);
    }
  }, [session?.agentId, activeAgentId, setActiveAgentId]);

  if (!session || !model) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-sm text-muted-foreground">No replay session loaded.</p>
        <Button variant="outline" className="mt-4" onClick={navigateToAssurance}>
          Back to Assurance Runs
        </Button>
      </div>
    );
  }

  const steps = model.steps;
  const hasTrajectory = steps.length > 0;
  if (!hasTrajectory) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16 text-center">
        <p className="text-sm font-medium text-foreground">No sealed trajectory on this result</p>
        <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
          This run was saved before per-step traces were recorded. Execute the suite again from
          Assurance Runs, then open replay on the new result.
        </p>
        <Button variant="outline" className="mt-4" onClick={navigateToAssurance}>
          Back to Assurance Runs
        </Button>
      </div>
    );
  }

  const currentStep: ExecutionStep = steps[stepIndex];
  const panels = panelContentForStep(currentStep);
  const failIndex = model.failStepIndex;
  const canJumpToFail = failIndex !== null && model.verdict === "FAIL";
  const agentLabel = session.agentId || DEMO_AGENT_ID;
  const shortTestId =
    model.testId.length > 40 ? `${model.testId.slice(0, 38)}…` : model.testId;

  const goTo = (idx: number) => {
    setStepIndex(Math.max(0, Math.min(steps.length - 1, idx)));
  };

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <button
        type="button"
        onClick={navigateToAssurance}
        className="mb-4 flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Assurance Runs
      </button>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-xl font-bold tracking-tight">Trajectory replay</h1>
          <Badge
            variant="outline"
            className="font-mono text-xs max-w-[min(100%,28rem)] truncate"
            title={model.testId}
          >
            {shortTestId}
          </Badge>
          <Badge
            variant={model.verdict === "FAIL" ? "fail" : model.verdict === "PASS" ? "pass" : "warn"}
            className="text-xs"
          >
            {model.verdict}
          </Badge>
        </div>
        <div className="font-mono text-[11px] text-muted-foreground text-right">
          <div>Agent: {agentLabel}</div>
          <div>Run {session.runId.slice(0, 8)}</div>
        </div>
      </div>

      {/* Playback bar */}
      <Card className="mb-6 border-border shadow-xs">
        <CardContent className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
          <div className="flex items-center gap-1 sm:justify-start">
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => goTo(0)}
              title="First turn"
              aria-label="First turn"
            >
              <ChevronFirst className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => goTo(stepIndex - 1)}
              disabled={stepIndex === 0}
              title="Previous turn"
              aria-label="Previous turn"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              className="h-8 w-8"
              onClick={() => setIsPlaying((p) => !p)}
              title={isPlaying ? "Pause" : "Play"}
              aria-label={isPlaying ? "Pause playback" : "Play playback"}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => goTo(stepIndex + 1)}
              disabled={stepIndex >= steps.length - 1}
              title="Next turn"
              aria-label="Next turn"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => goTo(steps.length - 1)}
              title="Last turn"
              aria-label="Last turn"
            >
              <ChevronLast className="h-4 w-4" />
            </Button>
          </div>

          <span className="font-mono text-xs text-foreground text-center">
            Turn {stepIndex + 1} of {steps.length}
          </span>

          <div className="flex sm:justify-end">
            {canJumpToFail ? (
              <Button
                variant="default"
                className="gap-2 text-xs font-semibold w-full sm:w-auto"
                onClick={() => failIndex !== null && goTo(failIndex)}
                title="Jump to the failing invariant step"
              >
                <FastForward className="h-3.5 w-3.5" />
                Jump to fail
              </Button>
            ) : (
              <span className="hidden sm:block text-[11px] text-muted-foreground text-right pr-1">
                No failure step (run passed)
              </span>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      <div className="mb-6 overflow-x-auto pb-2">
        <div className="flex min-w-max items-center gap-2">
          {steps.map((step, idx) => {
            const active = idx === stepIndex;
            const failed = step.is_failure;
            return (
              <React.Fragment key={step.step_id}>
                <button
                  type="button"
                  onClick={() => goTo(idx)}
                  className={`flex flex-col items-center gap-1 rounded-md px-2 py-1.5 text-center transition-colors cursor-pointer min-w-[88px] ${
                    active
                      ? "bg-primary/10 ring-1 ring-primary"
                      : "hover:bg-muted/60"
                  }`}
                >
                  <span
                    className={`h-2.5 w-2.5 rounded-full ${
                      failed
                        ? "bg-rose-500"
                        : active
                        ? "bg-primary"
                        : "bg-muted-foreground/40"
                    }`}
                  />
                  <span className="text-[10px] font-medium leading-tight text-foreground">
                    {step.label}
                  </span>
                </button>
                {idx < steps.length - 1 && (
                  <div className="h-px w-6 shrink-0 bg-border self-center mt-[-12px]" aria-hidden />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Thought / Action / Observation */}
      <div className="grid gap-4 lg:grid-cols-3">
        {(
          [
            { title: "Thought", body: panels.thought, lang: "markdown" as const },
            { title: "Action", body: panels.action, lang: "markdown" as const },
            {
              title:
                currentStep.kind === "user_message"
                  ? "User prompt"
                  : currentStep.kind === "http_response"
                    ? "Agent response"
                    : currentStep.kind === "invariant_check"
                      ? "Scorer verdict"
                      : "Observation",
              body: panels.observation,
              lang:
                currentStep.kind === "tool_call"
                  ? ("json" as const)
                  : ("markdown" as const),
            },
          ] as const
        ).map((panel) => {
          const emphasized =
            panels.emphasis === panel.title.toLowerCase() ||
            (panels.emphasis === "observation" && panel.title === "Observation") ||
            (panels.emphasis === "thought" && panel.title === "Thought") ||
            (panels.emphasis === "action" && panel.title === "Action");
          return (
          <Card
            key={panel.title}
            className={`flex flex-col overflow-hidden border-border shadow-xs ${
              emphasized ? "ring-1 ring-primary/40" : ""
            }`}
          >
            <CardHeader className="border-b border-border bg-muted py-2.5 px-4">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-foreground">
                {panel.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 flex-1">
              <CodeViewer
                code={panel.body}
                language={panel.lang === "json" ? "json" : "markdown"}
                height={panelEditorHeight(panel.body)}
                readOnly
              />
            </CardContent>
          </Card>
          );
        })}
      </div>

      <p className="mt-4 text-[11px] text-muted-foreground leading-relaxed">
        Steps are persisted at run time from sealed HTTP observation and scorer output (
        <span className="font-mono">TestCaseResult.trajectory</span>). Tool and thought steps appear
        only when present in the agent JSON payload.
      </p>
    </div>
  );
};
