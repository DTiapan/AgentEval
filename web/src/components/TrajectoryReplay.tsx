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
import { Separator } from "@/components/ui/separator";
import { CodeViewer } from "@/components/ui/code-viewer";
import { loadReplaySession, navigateToAssurance, type ReplaySession } from "@/lib/replay-session";
import {
  buildTrajectoryFromResult,
  panelContentForStep,
  type TrajectoryStep,
} from "@/lib/trajectory";
import { DEMO_AGENT_ID } from "@/lib/product";

interface TrajectoryReplayProps {
  onMissingSession?: () => void;
}

export const TrajectoryReplay: React.FC<TrajectoryReplayProps> = ({
  onMissingSession,
}) => {
  const [session, setSession] = useState<ReplaySession | null>(() => loadReplaySession());
  const [stepIndex, setStepIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const model = useMemo(
    () => (session ? buildTrajectoryFromResult(session.test) : null),
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
  const currentStep: TrajectoryStep = steps[stepIndex];
  const panels = panelContentForStep(currentStep);
  const failIndex = model.failStepIndex;
  const agentLabel = session.agentId || DEMO_AGENT_ID;

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
          <Badge variant="outline" className="font-mono text-xs">
            {model.testId}
          </Badge>
          <Badge
            variant={model.verdict === "FAIL" ? "fail" : model.verdict === "PASS" ? "pass" : "warn"}
            className="text-xs"
          >
            {model.verdict}
          </Badge>
        </div>
        <div className="font-mono text-[11px] text-muted-foreground">
          {agentLabel} · run {session.runId.slice(0, 8)}
        </div>
      </div>

      {/* Playback bar */}
      <Card className="mb-6 border-border shadow-xs">
        <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div className="flex items-center gap-1">
            <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => goTo(0)} title="First">
              <ChevronFirst className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => goTo(stepIndex - 1)}
              disabled={stepIndex === 0}
              title="Previous"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="secondary"
              size="icon"
              className="h-8 w-8"
              onClick={() => setIsPlaying((p) => !p)}
              title={isPlaying ? "Pause" : "Play"}
            >
              {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => goTo(stepIndex + 1)}
              disabled={stepIndex >= steps.length - 1}
              title="Next"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="h-8 w-8"
              onClick={() => goTo(steps.length - 1)}
              title="Last"
            >
              <ChevronLast className="h-4 w-4" />
            </Button>
          </div>

          <span className="font-mono text-xs text-foreground">
            Turn {stepIndex + 1} of {steps.length}
          </span>

          <Button
            variant="outline"
            className="gap-2 text-xs font-semibold"
            onClick={() => goTo(failIndex)}
          >
            <FastForward className="h-3.5 w-3.5" />
            Jump to fail
          </Button>
        </CardContent>
      </Card>

      {/* Timeline */}
      <div className="mb-6 overflow-x-auto pb-2">
        <div className="flex min-w-max items-center gap-2">
          {steps.map((step, idx) => {
            const active = idx === stepIndex;
            const failed = step.isFailure;
            return (
              <React.Fragment key={step.id}>
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
                    {step.timelineLabel}
                  </span>
                </button>
                {idx < steps.length - 1 && (
                  <Separator orientation="horizontal" className="w-6 shrink-0 bg-border" />
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
            { title: "Action", body: panels.action, lang: "json" as const },
            { title: "Observation", body: panels.observation, lang: "json" as const },
          ] as const
        ).map((panel) => (
          <Card key={panel.title} className="flex flex-col overflow-hidden border-border shadow-xs">
            <CardHeader className="border-b border-border bg-muted py-2.5 px-4">
              <CardTitle className="text-xs font-semibold uppercase tracking-wider text-foreground">
                {panel.title}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0 flex-1 min-h-[220px]">
              <CodeViewer
                code={panel.body}
                language={panel.lang === "json" ? "json" : "markdown"}
                height="220px"
                readOnly
              />
            </CardContent>
          </Card>
        ))}
      </div>

      <p className="mt-4 text-[11px] text-muted-foreground leading-relaxed">
        Black-box runs seal HTTP request/response evidence; multi-turn steps are reconstructed for
        debugger UX when the engine does not yet emit full trajectory spans.
      </p>
    </div>
  );
};
