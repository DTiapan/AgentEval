import React from "react";
import { ClipboardCheck } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { CriterionVerdictSummary } from "@/types";

interface AssuranceRequirementsSignoffProps {
  criterionVerdicts: CriterionVerdictSummary[];
  statementForRequirement: (stableId: string) => string;
  hasRun: boolean;
  hasRequirements: boolean;
}

export const AssuranceRequirementsSignoff: React.FC<AssuranceRequirementsSignoffProps> = ({
  criterionVerdicts,
  statementForRequirement,
  hasRun,
  hasRequirements,
}) => {
  if (!hasRequirements) {
    return (
      <Card className="border-border bg-card shadow-xs p-8 text-center">
        <p className="text-sm text-muted-foreground">
          No requirements loaded for this suite. Freeze a pack in Studio with a PRD that defines
          capabilities.
        </p>
      </Card>
    );
  }

  if (!hasRun || criterionVerdicts.length === 0) {
    return (
      <Card className="border-border bg-card shadow-xs p-8 text-center">
        <ClipboardCheck className="mx-auto mb-3 h-9 w-9 text-muted-foreground/50" aria-hidden />
        <p className="text-sm font-medium text-foreground">Sign-off needs a completed run</p>
        <p className="mt-2 text-xs text-muted-foreground max-w-md mx-auto">
          Execute an assurance run on the <span className="font-medium">Test runs</span> tab. Per-criterion
          verdicts are persisted from the engine (same data as{" "}
          <code className="font-mono text-[11px]">GET /v1/suites/…/requirements</code>).
        </p>
      </Card>
    );
  }

  return (
    <Card className="border-border bg-card shadow-xs overflow-hidden">
      <div className="border-b border-border bg-muted/30 px-4 py-3">
        <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
          Requirements sign-off (engine)
        </h2>
        <p className="mt-1 text-xs text-muted-foreground">
          Per-criterion verdicts from the latest run for release review.
        </p>
      </div>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Requirement</TableHead>
            <TableHead>Criterion</TableHead>
            <TableHead className="w-[100px]">Test</TableHead>
            <TableHead className="w-[110px]">Verdict</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {criterionVerdicts.map((cv) => (
            <TableRow key={`${cv.criterion_id}-${cv.test_id}`}>
              <TableCell className="text-xs max-w-[240px]">
                <span className="font-mono text-[10px] text-muted-foreground block">
                  {cv.requirement_stable_id}
                </span>
                {statementForRequirement(cv.requirement_stable_id)}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">{cv.criterion_stable_id}</TableCell>
              <TableCell className="font-mono text-[11px]">{cv.test_id}</TableCell>
              <TableCell>
                <Badge
                  variant={
                    cv.verdict === "PASS" ? "pass" : cv.verdict === "FAIL" ? "fail" : "outline"
                  }
                  className="text-[10px]"
                >
                  {cv.verdict}
                </Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  );
};
