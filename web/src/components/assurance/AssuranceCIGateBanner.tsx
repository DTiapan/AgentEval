import React from "react";
import { ShieldCheck, ShieldX } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { ASSURANCE_CI_GATE_UX } from "@/lib/studio-ux-config";

interface AssuranceCIGateBannerProps {
  failedCount: number;
  regressionCount: number;
  unverifiableCount: number;
  passRate: number;
}

export const AssuranceCIGateBanner: React.FC<AssuranceCIGateBannerProps> = ({
  failedCount,
  regressionCount,
  unverifiableCount,
  passRate,
}) => {
  const blocked =
    failedCount > 0 || regressionCount > 0 || (unverifiableCount > 0 && ASSURANCE_CI_GATE_UX.blockOnUnverifiable);

  const copy = blocked
    ? regressionCount > 0
      ? ASSURANCE_CI_GATE_UX.blockedRegressions(regressionCount)
      : failedCount > 0
        ? ASSURANCE_CI_GATE_UX.blockedFailures(failedCount)
        : ASSURANCE_CI_GATE_UX.blockedUnverifiable(unverifiableCount)
    : ASSURANCE_CI_GATE_UX.open(passRate);

  return (
    <div
      className={`mb-6 rounded-lg border p-4 shadow-xs flex flex-wrap items-center gap-3 ${
        blocked
          ? "border-rose-500/30 bg-rose-500/10"
          : "border-emerald-500/30 bg-emerald-500/10"
      }`}
      role="status"
    >
      {blocked ? (
        <ShieldX className="h-5 w-5 text-rose-600 dark:text-rose-400 shrink-0" aria-hidden />
      ) : (
        <ShieldCheck className="h-5 w-5 text-emerald-600 dark:text-emerald-400 shrink-0" aria-hidden />
      )}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-foreground">{ASSURANCE_CI_GATE_UX.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{copy}</p>
      </div>
      <Badge variant={blocked ? "fail" : "pass"} className="text-[10px] font-mono uppercase">
        {blocked ? ASSURANCE_CI_GATE_UX.statusBlocked : ASSURANCE_CI_GATE_UX.statusOpen}
      </Badge>
    </div>
  );
};
