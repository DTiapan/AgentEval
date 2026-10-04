import React from "react";

const LINES = [
  { kind: "cmd", text: "agenteval preview --prd requirements.md --agent demo-agent" },
  { kind: "ok", text: "Parsed 12 capabilities from PRD" },
  { kind: "ok", text: "Synthesized 47 user scenarios (scenario-first)" },
  { kind: "ok", text: "Optimized pack → 10 tests (set cover + P0 floors)" },
  { kind: "dim", text: "Ready to freeze · evidence-backed run on POST /v1/suites" },
] as const;

/**
 * Hero product preview — crisp terminal chrome (animate skill: CSS entry, transform+opacity).
 */
export const LandingHeroTerminal: React.FC = () => {
  return (
    <div className="hf-terminal-shell rounded-lg border border-border bg-card shadow-xs overflow-hidden">
      <div className="flex items-center gap-2 border-b border-border bg-muted/40 px-3 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/25" aria-hidden />
        <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/25" aria-hidden />
        <span className="h-2.5 w-2.5 rounded-full bg-muted-foreground/25" aria-hidden />
        <span className="ml-1 font-mono text-[10px] text-muted-foreground">studio — preview</span>
      </div>
      <div className="relative bg-[oklch(0.12_0.01_280)] dark:bg-[oklch(0.14_0.012_280)] px-4 py-4 sm:px-5 sm:py-5 min-h-[220px]">
        <div className="space-y-2 font-mono text-[11px] sm:text-xs leading-relaxed">
          {LINES.map((line, index) => (
            <div
              key={line.text}
              className={`hf-terminal-line flex gap-2 ${line.kind === "cmd" ? "text-primary-foreground/95" : ""}`}
              style={{ "--hf-line": index } as React.CSSProperties}
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
          <div
            className="hf-terminal-line hf-terminal-cursor-row flex items-center gap-2 pt-1"
            style={{ "--hf-line": LINES.length } as React.CSSProperties}
          >
            <span className="inline-flex gap-1.5" aria-hidden>
              <span className="hf-verdict-chip hf-verdict-pass">PASS</span>
              <span className="hf-verdict-chip hf-verdict-fail">FAIL</span>
              <span className="hf-verdict-chip hf-verdict-unv">UNVERIFIABLE</span>
            </span>
            <span className="hf-terminal-cursor" aria-hidden />
          </div>
        </div>
        <div className="mt-4 h-1 w-full overflow-hidden rounded-full bg-white/10">
          <div className="hf-terminal-progress h-full rounded-full bg-primary" />
        </div>
      </div>
    </div>
  );
};
