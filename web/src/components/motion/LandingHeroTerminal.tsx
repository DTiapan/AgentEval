import React from "react";

const LINES = [
  { kind: "cmd", text: "agenteval preview --prd requirements.md --agent demo-agent" },
  { kind: "ok", text: "Parsed 12 capabilities from PRD" },
  { kind: "ok", text: "Synthesized 47 user scenarios (scenario-first)" },
  { kind: "ok", text: "Optimized pack → 10 tests (set cover + P0 floors)" },
  { kind: "dim", text: "Ready to freeze · evidence-backed run on POST /v1/suites" },
] as const;

/** Static hero terminal. Lines are visible immediately. */
export const LandingHeroTerminal: React.FC = () => {
  return (
    <div className="rounded-lg border border-border bg-card shadow-xs overflow-hidden">
      <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-3 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/25" aria-hidden />
        <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/25" aria-hidden />
        <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/25" aria-hidden />
        <span className="ml-1 font-mono text-[10px] text-muted-foreground">studio: preview</span>
      </div>
      <div className="relative bg-[#0d1117] px-4 py-4 text-[#c9d1d9] sm:px-5 sm:py-5 min-h-[220px] dark:bg-[#010409]">
        <div className="space-y-2 font-mono text-[11px] sm:text-xs leading-relaxed">
          {LINES.map((line) => (
            <div
              key={line.text}
              className={`flex gap-2 ${line.kind === "cmd" ? "text-primary-foreground/95" : ""}`}
            >
              {line.kind === "cmd" ? (
                <span className="text-primary shrink-0 select-none">›</span>
              ) : line.kind === "ok" ? (
                <span className="text-emerald-400 shrink-0 select-none">✓</span>
              ) : (
                <span className="text-muted-foreground shrink-0 select-none">·</span>
              )}
              <span
                className={
                  line.kind === "dim"
                    ? "text-muted-foreground"
                    : line.kind === "ok"
                      ? "text-emerald-100/90"
                      : "text-foreground/90"
                }
              >
                {line.text}
              </span>
            </div>
          ))}
          <div className="flex items-center gap-2 pt-1">
            <span className="inline-flex gap-1.5" aria-hidden>
              <span className="rounded-sm border border-emerald-500/40 bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-emerald-300">
                PASS
              </span>
              <span className="rounded-sm border border-destructive/40 bg-destructive/15 px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-destructive">
                FAIL
              </span>
              <span className="rounded-sm border border-amber-500/40 bg-amber-500/15 px-1.5 py-0.5 text-[9px] font-semibold tracking-wide text-amber-300">
                UNVERIFIABLE
              </span>
            </span>
          </div>
        </div>
        <div className="mt-4 h-1 w-full overflow-hidden rounded-full bg-white/10">
          <div className="h-full w-full rounded-full bg-primary" />
        </div>
      </div>
    </div>
  );
};
