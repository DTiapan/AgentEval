import React, { useEffect, useState } from "react";
import {
  AlertOctagon,
  AlertTriangle,
  ArrowUpRight,
  CheckCircle,
  Download,
  ChevronRight,
  Code,
  Code2,
  Copy,
  ExternalLink,
  LayoutTemplate,
  Play,
  RefreshCw,
  Search,
  Waypoints,
  XCircle,
} from "lucide-react";
import {
  downloadSuiteReport,
  extendSuiteGaps,
  getSuiteDetail,
  getSuiteReportUrl,
  runSuite,
} from "../api";
import { useWorkspace } from "../context/WorkspaceContext";
import { SuiteDetailResult, SuiteRunReport, TestCaseResult } from "../types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable";
import { CodeViewer } from "@/components/ui/code-viewer";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from "@/components/ui/table";
import { SAMPLE_AGENT_ENDPOINT_PLACEHOLDER } from "@/lib/mvp-defaults";
import { openTrajectoryReplay } from "@/lib/replay-session";
import { navigateConsoleView } from "@/lib/console-route";
import { AssuranceEmptyState } from "@/components/AssuranceEmptyState";
import { ReportEmbedFrame } from "@/components/ReportEmbedFrame";

function useConsoleTheme(): "light" | "dark" {
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    document.documentElement.classList.contains("dark") ? "dark" : "light",
  );
  useEffect(() => {
    const root = document.documentElement;
    const sync = () => setTheme(root.classList.contains("dark") ? "dark" : "light");
    const observer = new MutationObserver(sync);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);
  return theme;
}

export const AssuranceView: React.FC = () => {
  const { activeAgentId, addToast, suites, isLoadingSuites } = useWorkspace();
  const consoleTheme = useConsoleTheme();

  const [suiteDetail, setSuiteDetail] = useState<SuiteDetailResult | null>(null);
  const [latestRun, setLatestRun] = useState<SuiteRunReport | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [isExtendingGaps, setIsExtendingGaps] = useState(false);
  const [isLoadingDetail, setIsLoadingDetail] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterVerdict, setFilterVerdict] = useState<"ALL" | "PASS" | "FAIL" | "UNVERIFIABLE">("ALL");
  const [selectedTest, setSelectedTest] = useState<TestCaseResult | null>(null);
  const [customEndpoint, setCustomEndpoint] = useState("");
  const [isReportModalOpen, setIsReportModalOpen] = useState(false);
  const [isDownloadingReport, setIsDownloadingReport] = useState(false);
  const [evidenceViewMode, setEvidenceViewMode] = useState<"cards" | "monaco">("cards");

  const loadSuiteData = async (agentId: string) => {
    setIsLoadingDetail(true);
    try {
      const detail = await getSuiteDetail(agentId);
      setSuiteDetail(detail);
      if (detail.manifest.endpoint_profile?.trim()) {
        setCustomEndpoint(detail.manifest.endpoint_profile);
      }
      if (detail.latest_run) {
        setLatestRun(detail.latest_run);
        if (detail.latest_run.results?.length > 0) {
          setSelectedTest(detail.latest_run.results[0]);
        }
      } else {
        setLatestRun(null);
        setSelectedTest(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.warn("Failed to load suite detail", msg);
    } finally {
      setIsLoadingDetail(false);
    }
  };

  useEffect(() => {
    if (activeAgentId) {
      loadSuiteData(activeAgentId);
    }
  }, [activeAgentId]);

  const runCoverage =
    latestRun?.coverage_report ?? suiteDetail?.latest_run?.coverage_report ?? null;
  const hasCoverageGaps =
    (runCoverage?.uncovered_tags?.length ?? 0) > 0 ||
    (runCoverage?.critical_uncovered?.length ?? 0) > 0;

  const handleExtendGaps = async () => {
    if (!activeAgentId) return;
    setIsExtendingGaps(true);
    try {
      const result = await extendSuiteGaps(activeAgentId, { max_add: 5 });
      if (result.noop) {
        addToast({
          type: "info",
          title: "No pack changes",
          message:
            result.remaining_gaps.length > 0
              ? `Gaps remain but no pool tests to add (${result.remaining_gaps.slice(0, 3).join(", ")}…).`
              : "Coverage already satisfied for the executed pack.",
        });
      } else {
        addToast({
          type: "success",
          title: "Gap loop applied",
          message: `v${result.previous_version} → v${result.new_version}: +${result.added_test_ids.length} tests.`,
        });
      }
      await loadSuiteData(activeAgentId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({ type: "error", title: "Extend gaps failed", message: msg });
    } finally {
      setIsExtendingGaps(false);
    }
  };

  const handleRunSuite = async () => {
    if (!activeAgentId) return;
    setIsRunning(true);
    try {
      const report = await runSuite(activeAgentId, customEndpoint.trim() || undefined);
      setLatestRun(report);
      if (report.results?.length > 0) {
        setSelectedTest(report.results[0]);
      }
      addToast({
        type: "success",
        title: "Assurance Run Complete",
        message: `${report.passed} passed, ${report.failed} failed, ${report.unverifiable} unverifiable.`,
      });
      await loadSuiteData(activeAgentId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({
        type: "error",
        title: "Run Failed",
        message: msg,
      });
    } finally {
      setIsRunning(false);
    }
  };

  const handleDownloadReport = async () => {
    if (!activeAgentId || !latestRun) return;
    setIsDownloadingReport(true);
    try {
      await downloadSuiteReport(activeAgentId, latestRun.run_id, { theme: consoleTheme });
      addToast({
        type: "success",
        title: "Report saved",
        message: "HTML report downloaded from engine.",
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({ type: "error", title: "Download failed", message: msg });
    } finally {
      setIsDownloadingReport(false);
    }
  };

  const openReplayForTest = (test: TestCaseResult) => {
    if (!activeAgentId || !latestRun) {
      addToast({
        type: "warning",
        title: "Replay unavailable",
        message: "Complete an assurance run first.",
      });
      return;
    }
    openTrajectoryReplay({
      agentId: activeAgentId,
      runId: latestRun.run_id,
      test,
    });
  };

  const handleOpenReplay = () => {
    if (!selectedTest) {
      addToast({
        type: "warning",
        title: "Replay unavailable",
        message: "Select a test from a completed run first.",
      });
      return;
    }
    openReplayForTest(selectedTest);
  };

  const handleCopyEvidence = () => {
    if (!selectedTest) return;
    const evidence = {
      test_id: selectedTest.test_id,
      verdict: selectedTest.verdict,
      rationale: selectedTest.rationale,
      user_prompt: selectedTest.observation.user_prompt,
      observed_response: selectedTest.observation.response_text,
      http_status: selectedTest.observation.http_status,
      latency_ms: selectedTest.observation.latency_ms,
    };
    navigator.clipboard.writeText(JSON.stringify(evidence, null, 2));
    addToast({
      type: "info",
      title: "Evidence Copied",
      message: "Test execution evidence copied to clipboard.",
    });
  };

  const results = latestRun?.results ?? [];

  const passCount = results.filter((r) => (r.verdict || "").toUpperCase() === "PASS").length;
  const failCount = results.filter((r) => (r.verdict || "").toUpperCase() === "FAIL").length;
  const unverifiableCount = results.filter((r) => (r.verdict || "").toUpperCase() === "UNVERIFIABLE").length;

  const filteredResults = results.filter((r) => {
    const verdict = (r.verdict || "").toUpperCase();
    const matchesFilter =
      filterVerdict === "ALL" || verdict === filterVerdict;
    const testId = r.test_id || "";
    const prompt = r.observation?.user_prompt || "";
    const matchesSearch =
      searchQuery === "" ||
      testId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      prompt.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const totalTests = results.length;
  const passRate =
    totalTests > 0 ? Math.round(((latestRun?.passed ?? 0) / totalTests) * 100) : 0;
  const avgLatency =
    totalTests > 0
      ? (
          results.reduce((acc, r) => acc + (r.observation?.latency_ms || 0), 0) /
          totalTests
        ).toFixed(1)
      : "0.0";

  const sortedLatencies = [...results.map((r) => r.observation?.latency_ms || 0)].sort(
    (a, b) => a - b
  );
  const p95Latency =
    sortedLatencies.length > 0
      ? sortedLatencies[Math.floor(sortedLatencies.length * 0.95)].toFixed(1)
      : "0.0";

  const diff = latestRun?.run_diff;
  const baselineRunId = diff?.baseline_run_id || diff?.previous_run_id || "";
  const changes = Array.isArray(diff?.changes) ? diff.changes : [];
  const regressionsList = Array.isArray(diff?.regressions)
    ? diff.regressions
    : changes.filter((c) => c.kind === "REGRESSED").map((c) => c.test_id);
  const fixesList = Array.isArray(diff?.fixes)
    ? diff.fixes
    : changes.filter((c) => c.kind === "FIXED").map((c) => c.test_id);
  const unchangedCount =
    typeof diff?.same_verdict_count === "number"
      ? diff.same_verdict_count
      : changes.filter((c) => c.kind === "STABLE").length;

  const showNoSuitesEmpty = !isLoadingSuites && suites.length === 0;
  const showNoRunEmpty =
    Boolean(activeAgentId) && !isLoadingDetail && suiteDetail !== null && !latestRun;

  const evidenceJson = selectedTest
    ? JSON.stringify(
        {
          test_id: selectedTest.test_id,
          verdict: selectedTest.verdict,
          rationale: selectedTest.rationale,
          telemetry: {
            latency_ms: selectedTest.observation?.latency_ms,
            http_status: selectedTest.observation?.http_status,
          },
          observation: selectedTest.observation,
        },
        null,
        2
      )
    : `// Select a test case to view its sealed execution JSON trace.`;

  if (showNoSuitesEmpty) {
    return (
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <h1 className="text-xl font-bold tracking-tight text-foreground mb-2">Assurance Runs</h1>
        <p className="text-xs text-muted-foreground mb-6">
          No suites in the engine yet. Start in Studio with a PRD and agent URL.
        </p>
        <AssuranceEmptyState variant="no-suites" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {/* Top Action & Control Bar */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Assurance Runs
            </h1>
            {activeAgentId && (
              <Badge variant="outline" className="font-mono text-xs border-border bg-muted text-foreground">
                {activeAgentId} (v{suiteDetail?.manifest?.version ?? 1})
              </Badge>
            )}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {activeAgentId
              ? suiteDetail
                ? `Frozen pack v${suiteDetail.manifest.version} · ${suiteDetail.optimized_pack?.tests?.length ?? 0} tests · target ${suiteDetail.manifest.endpoint_profile?.trim() || "not set in manifest"}`
                : "Loading suite from engine…"
              : "Select or create a suite in Studio to run assurance against your agent endpoint."}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Target Endpoint Input */}
          <div className="flex items-center gap-2 rounded-md border border-border bg-card px-2.5 py-1.5 text-xs font-mono text-foreground">
            <span className="text-muted-foreground shrink-0">Target:</span>
            <Input
              type="text"
              value={customEndpoint}
              onChange={(e) => setCustomEndpoint(e.target.value)}
              className="h-7 w-56 border-0 bg-transparent px-0 font-mono text-xs shadow-none focus-visible:ring-0"
              placeholder={SAMPLE_AGENT_ENDPOINT_PLACEHOLDER}
            />
          </div>

          {/* Run Suite Button */}
          <Button
            variant="default"
            onClick={handleRunSuite}
            disabled={isRunning || !activeAgentId}
            className="cursor-pointer"
          >
            {isRunning ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1.5" />
            ) : (
              <Play className="h-3.5 w-3.5 fill-current mr-1.5" />
            )}
            <span>Execute Run</span>
          </Button>

          {activeAgentId && latestRun && hasCoverageGaps && (
            <Button
              variant="secondary"
              onClick={handleExtendGaps}
              disabled={isExtendingGaps || isRunning}
              className="cursor-pointer"
              title="Append pool tests targeting uncovered tags (B5 gap loop)"
            >
              {isExtendingGaps ? (
                <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1.5" />
              ) : (
                <Waypoints className="h-3.5 w-3.5 mr-1.5" />
              )}
              <span>Close gaps</span>
            </Button>
          )}

          {/* HTML Report Trigger */}
          {activeAgentId && latestRun && (
            <>
              <Button
                variant="outline"
                onClick={handleDownloadReport}
                disabled={isDownloadingReport}
                className="cursor-pointer"
              >
                {isDownloadingReport ? (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1.5" />
                ) : (
                  <Download className="h-3.5 w-3.5 mr-1.5" />
                )}
                <span>Download report</span>
              </Button>
              <Button
                variant="outline"
                onClick={() => setIsReportModalOpen(true)}
                className="cursor-pointer"
              >
                <span>View report</span>
                <ArrowUpRight className="h-3.5 w-3.5 ml-1 text-muted-foreground" />
              </Button>
            </>
          )}
        </div>
      </div>

      {showNoRunEmpty && (
        <div className="mb-6">
          <AssuranceEmptyState
            variant="no-run"
            agentId={activeAgentId ?? undefined}
            packSize={suiteDetail?.optimized_pack?.tests?.length}
            onExecuteRun={handleRunSuite}
            isRunning={isRunning}
          />
        </div>
      )}

      {/* KPI Metric Strip - Styled matching Screenshots 2 & 3 */}
      <div className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {/* Pass Rate */}
        <Card className="p-4 border-border bg-card shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Pass Rate
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold font-mono ${
                passRate >= 80
                  ? "text-emerald-500"
                  : passRate >= 50
                  ? "text-amber-500"
                  : "text-rose-500"
              }`}
            >
              {totalTests > 0 ? `${passRate}%` : "—"}
            </span>
            <span className="text-xs text-muted-foreground">
              {latestRun?.passed ?? 0}/{totalTests}
            </span>
          </div>
        </Card>

        {/* Total Tests */}
        <Card className="p-4 border-border bg-card shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Pack Tests
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              {suiteDetail?.optimized_pack?.tests?.length ?? totalTests}
            </span>
            <span className="text-xs text-muted-foreground">frozen</span>
          </div>
        </Card>

        {/* Failed Invariants */}
        <Card className="p-4 border-border bg-card shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Failures
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold font-mono ${
                (latestRun?.failed ?? 0) > 0 ? "text-rose-500" : "text-foreground"
              }`}
            >
              {latestRun?.failed ?? 0}
            </span>
            <span className="text-xs text-muted-foreground">violations</span>
          </div>
        </Card>

        {/* Unverifiable */}
        <Card className="p-4 border-border bg-card shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Unverifiable
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span
              className={`text-2xl font-bold font-mono ${
                (latestRun?.unverifiable ?? 0) > 0 ? "text-amber-500" : "text-foreground"
              }`}
            >
              {latestRun?.unverifiable ?? 0}
            </span>
            <span className="text-xs text-muted-foreground">unprovable</span>
          </div>
        </Card>

        {/* Average Latency */}
        <Card className="p-4 border-border bg-card shadow-xs">
          <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Avg Latency
          </span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-foreground">
              {avgLatency}
            </span>
            <span className="text-xs text-muted-foreground">ms</span>
          </div>
          <div className="mt-1 text-[11px] font-mono text-muted-foreground">
            p95: {p95Latency} ms
          </div>
        </Card>
      </div>

      {/* Regression Diff Alert */}
      {diff && baselineRunId && (
        <div
          className={`mb-6 rounded-lg border p-4 shadow-xs ${
            regressionsList.length > 0
              ? "border-rose-500/30 bg-rose-500/10"
              : "border-border bg-card"
          }`}
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-3">
              <span className="text-xs font-semibold text-foreground">
                Regression Diff vs Run {baselineRunId.slice(0, 8)}:
              </span>
              {regressionsList.length > 0 ? (
                <Badge variant="fail" className="text-xs font-semibold">
                  ⚠️ {regressionsList.length} Regressions{regressionsList.length <= 2 ? `: ${regressionsList.join(", ")}` : ""}
                </Badge>
              ) : (
                <Badge variant="pass" className="text-xs font-semibold">
                  ✓ 0 Regressions
                </Badge>
              )}
              {fixesList.length > 0 && (
                <Badge variant="pass" className="text-xs font-semibold">
                  ✨ {fixesList.length} Fixed{fixesList.length <= 2 ? `: ${fixesList.join(", ")}` : ""}
                </Badge>
              )}
            </div>
            <span className="font-mono text-xs text-muted-foreground">
              {unchangedCount} unchanged
            </span>
          </div>
        </div>
      )}

      {showNoRunEmpty ? null : (
      <ResizablePanelGroup
        direction="horizontal"
        className="min-h-[580px] gap-5"
      >
        {/* Left Resizable Panel: Test Cases Explorer Table */}
        <ResizablePanel defaultSize={55} minSize={35} className="flex flex-col gap-3 overflow-y-auto">
          {/* Column Header */}
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Test Cases Explorer
              </h2>
              <Badge variant="outline" className="font-mono text-[10px] text-muted-foreground">
                Left Pane
              </Badge>
            </div>
          </div>

          <Card className="flex flex-col overflow-hidden border-border bg-card shadow-xs">
            {/* Filter Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-muted/30 p-3">
              {/* Verdict Pills */}
              <div className="flex items-center gap-1">
                {(
                  [
                    { key: "ALL", label: `All (${totalTests})` },
                    { key: "FAIL", label: `Fail (${failCount})` },
                    { key: "PASS", label: `Pass (${passCount})` },
                    { key: "UNVERIFIABLE", label: `Unverifiable (${unverifiableCount})` },
                  ] as const
                ).map((v) => (
                  <Button
                    key={v.key}
                    variant={filterVerdict === v.key ? "secondary" : "ghost"}
                    size="sm"
                    onClick={() => setFilterVerdict(v.key)}
                    className={`h-7 px-2.5 text-xs cursor-pointer ${
                      filterVerdict === v.key
                        ? "bg-primary text-primary-foreground font-semibold shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    {v.label}
                  </Button>
                ))}
              </div>

              {/* Search Input */}
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Search prompt or ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-44 pl-8 h-8 text-xs"
                />
              </div>
            </div>

            {/* Ready-Made Shadcn Table Structure */}
            <Table>
              <TableHeader>
                <TableRow className="border-border bg-muted/20">
                  <TableHead className="w-[90px]">Verdict</TableHead>
                  <TableHead>Test ID & Input Prompt</TableHead>
                  <TableHead className="text-right w-[80px]">Latency</TableHead>
                  <TableHead className="w-[30px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredResults.length > 0 ? (
                  filteredResults.map((r) => {
                    const isSelected = selectedTest?.test_id === r.test_id;
                    const isPass = r.verdict === "PASS";
                    const isFail = r.verdict === "FAIL";
                    const testDef = suiteDetail?.optimized_pack?.tests?.find(
                      (t) => t.id === r.test_id
                    );
                    const capId = testDef?.capability_id || "general";

                    return (
                      <TableRow
                        key={r.test_id}
                        onClick={() => setSelectedTest(r)}
                        className={`cursor-pointer ${
                          isSelected
                            ? "bg-muted/70 border-l-2 border-primary"
                            : "hover:bg-muted/40"
                        }`}
                      >
                        <TableCell>
                          <Badge
                            variant={isPass ? "pass" : isFail ? "fail" : "warn"}
                            className="text-[10px] gap-1"
                          >
                            {isPass ? (
                              <CheckCircle className="h-3 w-3" />
                            ) : isFail ? (
                              <XCircle className="h-3 w-3" />
                            ) : (
                              <AlertTriangle className="h-3 w-3" />
                            )}
                            {r.verdict}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="font-mono text-xs font-semibold text-foreground">
                            {r.test_id}
                          </div>
                          <div className="mt-0.5 line-clamp-1 text-xs text-muted-foreground">
                            &quot;{r.observation.user_prompt}&quot;
                          </div>
                          <div className="mt-1 flex items-center gap-1.5 font-mono text-[11px] text-muted-foreground">
                            <span className="text-foreground">cap: {capId}</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-mono text-xs text-muted-foreground">
                          {Math.round(r.observation.latency_ms)}ms
                        </TableCell>
                        <TableCell>
                          {isFail ? (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              title="Trajectory replay (jump to fail)"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSelectedTest(r);
                                openReplayForTest(r);
                              }}
                            >
                              <Waypoints className="h-3.5 w-3.5 text-primary" />
                            </Button>
                          ) : (
                            <ChevronRight className="h-4 w-4 text-muted-foreground" />
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                ) : (
                  <TableRow>
                    <TableCell colSpan={4} className="h-40 text-center">
                      <div className="flex flex-col items-center justify-center">
                        <AlertOctagon className="mb-2 h-8 w-8 text-muted-foreground/40" />
                        <p className="text-sm font-medium text-foreground">No test results found</p>
                        <p className="mt-0.5 text-xs text-muted-foreground">
                          {results.length === 0
                            ? 'Click "Execute Run" to test the agent against this frozen suite.'
                            : "No tests match current filter or search criteria."}
                        </p>
                      </div>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </ResizablePanel>

        {/* Ready-Made Draggable Resize Handle */}
        <ResizableHandle withHandle />

        {/* Right Resizable Panel: Execution Evidence Inspector */}
        <ResizablePanel defaultSize={45} minSize={30} className="flex flex-col gap-3 overflow-y-auto">
          {/* Column Header */}
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <h2 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                Execution Evidence Inspector
              </h2>
              <Badge variant="outline" className="font-mono text-[10px] text-muted-foreground">
                Right Pane
              </Badge>
            </div>
            {/* View Mode Toggle: Formatted Cards vs Monaco JSON */}
            <div className="flex items-center gap-1 rounded-md border border-border bg-muted/40 p-0.5">
              <button
                onClick={() => setEvidenceViewMode("cards")}
                className={`flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer ${
                  evidenceViewMode === "cards"
                    ? "bg-card text-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                title="Structured Cards View"
              >
                <LayoutTemplate className="h-3 w-3" />
                <span>Card View</span>
              </button>
              <button
                onClick={() => setEvidenceViewMode("monaco")}
                className={`flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer ${
                  evidenceViewMode === "monaco"
                    ? "bg-card text-foreground font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground"
                }`}
                title="Monaco JSON View"
              >
                <Code2 className="h-3 w-3" />
                <span>Monaco JSON</span>
              </button>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card flex flex-col overflow-hidden shadow-xs">
            <div className="flex items-center justify-between border-b border-border bg-muted/30 px-4 py-2.5">
              <div className="flex items-center gap-2">
                <Code className="h-4 w-4 text-muted-foreground" />
                <span className="text-xs font-semibold text-foreground">
                  {evidenceViewMode === "monaco" ? "evidence-trace.json" : "Sealed Evidence Inspector"}
                </span>
              </div>
              {selectedTest && (
                <div className="flex items-center gap-2">
                  <Button
                    variant={
                      (selectedTest.verdict || "").toUpperCase() === "FAIL"
                        ? "default"
                        : "outline"
                    }
                    size="sm"
                    onClick={handleOpenReplay}
                    className="h-6 px-2 text-[10px] cursor-pointer"
                    title={
                      (selectedTest.verdict || "").toUpperCase() === "FAIL"
                        ? "Open trajectory replay (jump-to-fail available)"
                        : "Open thin HTTP replay (passed test)"
                    }
                  >
                    <Waypoints className="h-3 w-3 mr-1" />
                    <span>Trajectory replay</span>
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopyEvidence}
                    className="h-6 px-2 text-[10px] font-mono cursor-pointer"
                    title="Copy Evidence JSON"
                  >
                    <Copy className="h-3 w-3 mr-1" />
                    <span>Copy JSON</span>
                  </Button>
                  <Badge variant="outline" className="font-mono text-[11px]">
                    HTTP {selectedTest.observation?.http_status ?? 200}
                  </Badge>
                </div>
              )}
            </div>

            <div className="flex-1 p-4 space-y-4 overflow-y-auto max-h-[520px] bg-card">
              {evidenceViewMode === "monaco" ? (
                /* Ready-Made Monaco JSON Inspector */
                <CodeViewer
                  code={evidenceJson}
                  language="json"
                  height="380px"
                  readOnly={true}
                />
              ) : selectedTest ? (
                <>
                  {/* Rationale / Verdict Explanation */}
                  <div>
                    <div className="mb-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                      Deterministic Verdict Rationale
                    </div>
                    <div className="rounded-lg border border-border bg-muted/30 p-3 text-xs leading-relaxed text-foreground">
                      {selectedTest.rationale || "No specific rationale recorded."}
                    </div>
                  </div>

                  {/* Sent Prompt */}
                  <div>
                    <div className="mb-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                      Sent User Prompt
                    </div>
                    <div className="rounded-lg border border-border bg-muted/30 p-3 font-mono text-xs text-foreground leading-relaxed">
                      {selectedTest.observation?.user_prompt || "No prompt recorded"}
                    </div>
                  </div>

                  {/* Target Agent Response */}
                  <div>
                    <div className="mb-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                      Target Agent Observed Response
                    </div>
                    <div className="rounded-lg border border-border bg-muted/30 p-3 font-mono text-xs text-primary leading-relaxed max-h-48 overflow-y-auto">
                      {selectedTest.observation?.response_text ||
                        (selectedTest.observation?.raw_json
                          ? JSON.stringify(selectedTest.observation.raw_json, null, 2)
                          : "No response recorded")}
                    </div>
                  </div>

                  {/* Telemetry Metrics */}
                  <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-muted-foreground">
                    <div className="rounded border border-border bg-card p-2 shadow-xs">
                      Latency:{" "}
                      <span className="text-foreground">
                        {(selectedTest.observation?.latency_ms ?? 0).toFixed(2)} ms
                      </span>
                    </div>
                    <div className="rounded border border-border bg-card p-2 shadow-xs">
                      Status:{" "}
                      <span className="text-foreground">
                        {selectedTest.observation?.http_status ?? 200} OK
                      </span>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex h-64 flex-col items-center justify-center text-center">
                  <Code className="mb-2 h-8 w-8 text-muted-foreground/40" />
                  <p className="text-xs text-muted-foreground">
                    Select a test case to inspect its request payload, observed response, and verification proof.
                  </p>
                </div>
              )}
            </div>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
      )}

      {/* Standalone HTML Report In-App Modal with Shadcn Dialog */}
      <Dialog open={isReportModalOpen} onOpenChange={setIsReportModalOpen}>
        <DialogContent
          className="max-w-6xl h-[90vh] p-0 flex flex-col bg-card border-border overflow-hidden sm:max-w-6xl"
        >
        {activeAgentId && latestRun ? (
          <>
            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-border bg-muted/30 px-5 py-3.5">
              <div className="flex items-center gap-3">
                <Badge variant="secondary" className="font-mono text-xs">
                  REPORT
                </Badge>
                <h3 className="text-sm font-semibold text-foreground font-mono">
                  {activeAgentId} — Run {latestRun.run_id.slice(0, 8)}
                </h3>
              </div>
              <div className="flex items-center gap-2 pr-6">
                <a
                  href={getSuiteReportUrl(activeAgentId, latestRun.run_id, {
                    theme: consoleTheme,
                  })}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs font-medium text-foreground hover:bg-muted transition-colors"
                >
                  <span>Open in New Tab</span>
                  <ExternalLink className="h-3.5 w-3.5" />
                </a>
              </div>
            </div>

            <ReportEmbedFrame
              agentId={activeAgentId}
              runId={latestRun.run_id}
              theme={consoleTheme}
              active={isReportModalOpen}
            />
          </>
        ) : (
          <div className="p-8 text-center text-sm text-muted-foreground">
            Run assurance first to view a report.
            <Button
              type="button"
              variant="link"
              className="mt-2"
              onClick={() => {
                setIsReportModalOpen(false);
                navigateConsoleView("studio");
              }}
            >
              Go to Studio
            </Button>
          </div>
        )}
        </DialogContent>
      </Dialog>
    </div>
  );
};
