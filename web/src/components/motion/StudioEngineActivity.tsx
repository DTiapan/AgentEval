import React, { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { usePrefersReducedMotion } from "@/hooks/usePrefersReducedMotion";

export type StudioEngineActivityMode = "preview" | "freeze";

const PREVIEW_PHASES = [
  "Parsing requirements into capabilities",
  "Synthesizing user scenarios from your PRD",
  "Ranking candidates and optimizing pack",
] as const;

const FREEZE_PHASES = [
  "Fingerprinting requirements",
  "Persisting frozen suite to engine",
  "Finalizing coverage map",
] as const;

interface StudioEngineActivityProps {
  mode: StudioEngineActivityMode;
  active: boolean;
  className?: string;
}

/**
 * Loading choreography for suite preview / freeze.
 * Motion patterns adapted from HyperFrames CSS stagger + shimmer (hyperframes-animation).
 */
export const StudioEngineActivity: React.FC<StudioEngineActivityProps> = ({
  mode,
  active,
  className = "",
}) => {
  const reducedMotion = usePrefersReducedMotion();
  const phases = mode === "freeze" ? FREEZE_PHASES : PREVIEW_PHASES;
  const [phaseIndex, setPhaseIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      setPhaseIndex(0);
      return;
    }
    if (reducedMotion) return;
    const timer = window.setInterval(() => {
      setPhaseIndex((i) => (i + 1) % phases.length);
    }, 2400);
    return () => window.clearInterval(timer);
  }, [active, reducedMotion, phases.length]);

  if (!active) return null;

  const label = phases[phaseIndex];

  return (
    <div
      role="status"
      aria-live="polite"
      aria-busy="true"
      className={`hf-engine-activity relative overflow-hidden rounded-md border border-primary/20 bg-primary/5 px-3 py-2 ${className}`}
    >
      <div className="hf-shimmer-track pointer-events-none absolute inset-0" aria-hidden />
      <div className="relative flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary hf-pulse-soft" aria-hidden />
          <p className="truncate text-[11px] text-foreground">
            <span className="font-medium">
              {mode === "freeze" ? "Freezing suite" : "Generating pack"}
            </span>
            <span className="text-muted-foreground font-mono"> · {label}…</span>
          </p>
        </div>
        <div className="hf-stagger-dots flex shrink-0 items-center gap-1" aria-hidden>
          {[0, 1, 2].map((i) => (
            <span key={i} className="hf-stagger-dot" style={{ "--hf-i": i } as React.CSSProperties} />
          ))}
        </div>
      </div>
    </div>
  );
};
