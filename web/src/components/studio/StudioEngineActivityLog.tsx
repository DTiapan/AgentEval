import React, { useEffect, useRef } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { WorkflowActivityEntry } from "@/types";
import { cn } from "@/lib/utils";

function formatLogTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false,
    });
  } catch {
    return "--:--:--";
  }
}

function levelClass(level: WorkflowActivityEntry["level"]): string {
  switch (level) {
    case "ok":
      return "text-emerald-600 dark:text-emerald-400";
    case "warn":
      return "text-amber-600 dark:text-amber-400";
    case "error":
      return "text-rose-600 dark:text-rose-400";
    default:
      return "text-muted-foreground";
  }
}

interface StudioEngineActivityLogProps {
  entries: WorkflowActivityEntry[];
  loading?: boolean;
  waitingSeconds?: number;
  className?: string;
}

/**
 * Terminal-style log for suite preview. Client lines are request metadata;
 * server lines come from POST /v1/suites/preview `activity_log`.
 */
export const StudioEngineActivityLog: React.FC<StudioEngineActivityLogProps> = ({
  entries,
  loading = false,
  waitingSeconds = 0,
  className,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [entries.length, waitingSeconds, loading]);

  return (
    <Card
      className={cn(
        "border border-border bg-card shadow-xs flex flex-col overflow-hidden min-h-[280px]",
        className,
      )}
    >
      <CardHeader className="py-2.5 px-4 border-b border-border bg-muted/30 flex flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex items-center gap-1.5" aria-hidden>
            <span className="h-2 w-2 rounded-full bg-rose-500/70" />
            <span className="h-2 w-2 rounded-full bg-amber-500/70" />
            <span className="h-2 w-2 rounded-full bg-emerald-500/70" />
          </div>
          <span className="font-mono text-[11px] text-muted-foreground truncate">
            engine-activity.log
          </span>
        </div>
        {loading ? (
          <span className="font-mono text-[10px] text-primary tabular-nums shrink-0">
            {waitingSeconds}s
          </span>
        ) : null}
      </CardHeader>
      <CardContent className="p-0 flex-1 flex flex-col min-h-0">
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto p-3 font-mono text-[11px] leading-relaxed bg-[#0d1117] text-[#c9d1d9] dark:bg-[#010409] max-h-[min(420px,50vh)]"
          role="log"
          aria-live="polite"
          aria-busy={loading}
        >
          {entries.length === 0 && !loading ? (
            <p className="text-muted-foreground">No engine activity yet.</p>
          ) : (
            <ul className="space-y-1">
              {entries.map((entry, i) => (
                <li key={`${entry.ts}-${i}`} className="flex gap-2">
                  <span className="text-[#6e7681] shrink-0 tabular-nums">
                    {formatLogTime(entry.ts)}
                  </span>
                  <span className={cn("shrink-0 uppercase w-10", levelClass(entry.level))}>
                    {entry.level}
                  </span>
                  <span className="break-words">{entry.message}</span>
                </li>
              ))}
              {loading ? (
                <li className="flex gap-2 text-[#8b949e]">
                  <span className="shrink-0 tabular-nums">
                    {formatLogTime(new Date().toISOString())}
                  </span>
                  <span className="shrink-0 w-10">…</span>
                  <span className="hf-pulse-soft">
                    Waiting for engine response (scenario compile, LLM synthesis, ranking)…
                  </span>
                </li>
              ) : null}
            </ul>
          )}
        </div>
        <p className="px-3 py-2 text-[10px] text-muted-foreground border-t border-border bg-muted/20">
          Lines marked after the request are recorded on the server during preview.
        </p>
      </CardContent>
    </Card>
  );
};
