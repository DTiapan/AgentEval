import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Code2,
  Copy,
  Eye,
  LayoutTemplate,
  Play,
  RefreshCw,
  Save,
  Terminal,
  Upload,
} from "lucide-react";
import {
  extendSuiteGaps,
  getSuiteDetail,
  initSuite,
  listDomainPacks,
  previewSuite,
  probeAgentEndpoint,
  syncSuite,
} from "../api";
import { useWorkspace } from "../context/WorkspaceContext";
import { CandidateTest, CoverageReport, SuiteDetailResult, SuitePreviewResult } from "../types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { CodeViewer } from "@/components/ui/code-viewer";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatTestTabLabel } from "@/lib/format-test-label";
import { EMPTY_PRD_TEMPLATE, SAMPLE_AGENT_ENDPOINT_PLACEHOLDER } from "@/lib/mvp-defaults";
import { navigateConsoleView } from "@/lib/console-route";
import {
  PRD_FILE_ACCEPT,
  agentIdFromPrdFilename,
  readPrdFile,
} from "@/lib/read-prd-file";

export const Studio: React.FC = () => {
  const { addToast, refreshSuites, setActiveAgentId, activeAgentId } = useWorkspace();

  const [agentId, setAgentId] = useState("");
  const [endpointUrl, setEndpointUrl] = useState("");
  const [requirementsText, setRequirementsText] = useState(EMPTY_PRD_TEMPLATE);
  const [maxTests, setMaxTests] = useState(10);
  const [selectedTier, setSelectedTier] = useState<"ALL" | "P0" | "P1" | "P2">("ALL");
  const [selectedTestIds, setSelectedTestIds] = useState<string[]>([]);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isLoadingFrozen, setIsLoadingFrozen] = useState(false);
  const [isSavingSuite, setIsSavingSuite] = useState(false);
  const [isExtendingGaps, setIsExtendingGaps] = useState(false);
  /** Live preview from POST /v1/suites/preview (unsaved). */
  const [previewData, setPreviewData] = useState<SuitePreviewResult | null>(null);
  /** Frozen pack from GET /v1/suites/{agent_id} (persisted engine state). */
  const [frozenDetail, setFrozenDetail] = useState<SuiteDetailResult | null>(null);
  const [activeTestIndex, setActiveTestIndex] = useState(0);
  const [activeBottomTab, setActiveBottomTab] = useState<"gaps" | "floors" | "compression">("gaps");
  const [terminalViewMode, setTerminalViewMode] = useState<"cards" | "monaco">("cards");
  const prdFileInputRef = useRef<HTMLInputElement>(null);
  const [justCreatedPack, setJustCreatedPack] = useState(false);
  const [availablePacks, setAvailablePacks] = useState<{ id: string; display_name: string }[]>(
    [],
  );
  const [enabledDomainPacks, setEnabledDomainPacks] = useState<string[]>([]);

  useEffect(() => {
    listDomainPacks()
      .then((body) => {
        setAvailablePacks(
          body.packs.map((p) => ({ id: p.id, display_name: p.display_name || p.name })),
        );
      })
      .catch(() => setAvailablePacks([]));
  }, []);

  const loadFrozenSuite = useCallback(async (id: string) => {
    if (!id.trim()) {
      setFrozenDetail(null);
      return;
    }
    setIsLoadingFrozen(true);
    try {
      const detail = await getSuiteDetail(id);
      setFrozenDetail(detail);
      if (detail.manifest.endpoint_profile) {
        setEndpointUrl(detail.manifest.endpoint_profile);
      }
      if (detail.requirements_text?.trim()) {
        setRequirementsText(detail.requirements_text);
      }
      setPreviewData(null);
      setActiveTestIndex(0);
      if (detail.optimized_pack?.tests) {
        setSelectedTestIds(detail.optimized_pack.tests.map((t) => t.id));
      }
    } catch {
      setFrozenDetail(null);
    } finally {
      setIsLoadingFrozen(false);
    }
  }, []);

  const handleSelectTier = (tier: "ALL" | "P0" | "P1" | "P2") => {
    setSelectedTier(tier);
    if (tier === "ALL") {
      if (previewData?.optimized_pack?.tests) {
        setSelectedTestIds(previewData.optimized_pack.tests.map((t) => t.id));
      }
      return;
    }
    const proj = previewData?.marginal_curve?.find((p) => p.tier === tier);
    if (proj) {
      setMaxTests(proj.target_test_count);
    }
    const pool = previewData?.candidate_pool ?? previewData?.optimized_pack?.tests ?? [];
    const tierHierarchy = tier === "P0" ? ["P0"] : tier === "P1" ? ["P0", "P1"] : ["P0", "P1", "P2"];
    const matching = pool
      .filter((t) => tierHierarchy.includes(t.priority_tier || "P1"))
      .map((t) => t.id);
    if (matching.length > 0) {
      setSelectedTestIds(matching);
    }
  };

  useEffect(() => {
    if (!activeAgentId) {
      setFrozenDetail(null);
      setPreviewData(null);
      setJustCreatedPack(false);
      setAgentId("");
      setEndpointUrl("");
      setRequirementsText(EMPTY_PRD_TEMPLATE);
      setSelectedTestIds([]);
      setActiveTestIndex(0);
      return;
    }
    setAgentId(activeAgentId);
    setPreviewData(null);
    loadFrozenSuite(activeAgentId);
  }, [activeAgentId, loadFrozenSuite]);

  const optimizedPack = previewData?.optimized_pack ?? frozenDetail?.optimized_pack ?? null;
  const coverageReport: CoverageReport | null | undefined =
    previewData?.coverage ?? frozenDetail?.coverage ?? null;
  const candidatePoolSize =
    previewData?.candidate_pool?.length ?? frozenDetail?.candidate_pool_size ?? 0;
  const packProvenance = previewData
    ? "preview"
    : frozenDetail
      ? `frozen v${frozenDetail.manifest.version}`
      : null;

  const handlePreview = async () => {
    if (!requirementsText.trim() || !agentId.trim()) {
      addToast({
        type: "error",
        title: "Validation Error",
        message: "Agent ID and Requirements text are required.",
      });
      return;
    }

    setIsLoadingPreview(true);
    try {
      const data = await previewSuite({
        requirements_text: requirementsText,
        agent_id: agentId,
        endpoint_url: endpointUrl.trim() || undefined,
        max_tests: maxTests,
        target_tier: selectedTier !== "ALL" ? selectedTier : undefined,
        selected_test_ids: selectedTestIds.length > 0 ? selectedTestIds : undefined,
      });
      setPreviewData(data);
      setActiveTestIndex(0);
      setFrozenDetail(null);
      if (data.optimized_pack?.tests) {
        setSelectedTestIds(data.optimized_pack.tests.map((t) => t.id));
      }
      addToast({
        type: "success",
        title: "Preview Synthesized",
        message: `Generated ${data.candidate_pool?.length ?? 0} candidate tests, optimized to ${data.optimized_pack?.tests?.length ?? 0}.`,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({
        type: "error",
        title: "Preview Failed",
        message: msg,
      });
    } finally {
      setIsLoadingPreview(false);
    }
  };

  const handleExtendGaps = async () => {
    if (!agentId.trim() || !frozenDetail?.latest_run) {
      addToast({
        type: "warning",
        title: "Run assurance first",
        message: "Gap loop needs a completed assurance run with coverage.",
      });
      return;
    }
    setIsExtendingGaps(true);
    try {
      const result = await extendSuiteGaps(agentId, { max_add: 5 });
      if (result.noop) {
        addToast({
          type: "info",
          title: "No pack changes",
          message: "No additional pool tests could close the reported gaps.",
        });
      } else {
        addToast({
          type: "success",
          title: "Gap loop applied",
          message: `Added ${result.added_test_ids.length} tests (v${result.new_version}).`,
        });
      }
      await refreshSuites();
      await loadFrozenSuite(agentId);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({ type: "error", title: "Extend gaps failed", message: msg });
    } finally {
      setIsExtendingGaps(false);
    }
  };

  const handlePrdFileSelected = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    try {
      const text = await readPrdFile(file);
      setRequirementsText(text);
      setPreviewData(null);
      if (!agentId.trim()) {
        const suggested = agentIdFromPrdFilename(file.name);
        if (suggested) setAgentId(suggested);
      }
      addToast({
        type: "success",
        title: "PRD imported",
        message: `${file.name} (${text.length} chars). Preview or freeze when ready.`,
      });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({ type: "error", title: "Import failed", message: msg });
    }
  };

  const handleSaveSuite = async () => {
    if (!requirementsText.trim() || !agentId.trim()) {
      addToast({
        type: "error",
        title: "Validation Error",
        message: "Agent ID and requirements (PRD) are required.",
      });
      return;
    }
    if (!frozenDetail?.manifest && !endpointUrl.trim()) {
      addToast({
        type: "error",
        title: "Endpoint required",
        message: "Set the target HTTP endpoint before freezing a new suite.",
      });
      return;
    }

    setIsSavingSuite(true);
    let createdNewSuite = false;
    try {
      const endpoint = endpointUrl.trim() || undefined;
      const targetTier = selectedTier !== "ALL" ? selectedTier : undefined;
      const selectedIds = selectedTestIds.length > 0 ? selectedTestIds : undefined;
      if (frozenDetail?.manifest) {
        const sync = await syncSuite(agentId, {
          requirements_text: requirementsText,
          endpoint_url: endpoint,
          max_tests: maxTests,
          enabled_domain_packs: enabledDomainPacks,
          target_tier: targetTier,
          selected_test_ids: selectedIds,
        });
        if (sync.noop) {
          addToast({
            type: "info",
            title: "No changes",
            message: "Requirements and capabilities match the frozen pack (v" + sync.new_version + ").",
          });
        } else {
          const removed =
            sync.removed_capabilities.length > 0
              ? ` Removed caps: ${sync.removed_capabilities.join(", ")}.`
              : "";
          const added =
            sync.added_capabilities.length > 0
              ? ` Added caps: ${sync.added_capabilities.join(", ")}.`
              : "";
          addToast({
            type: "success",
            title: "Pack updated",
            message: `v${sync.previous_version} → v${sync.new_version} (${sync.pack_size} tests).${removed}${added}`,
          });
        }
      } else {
        const result = await initSuite({
          requirements_text: requirementsText,
          agent_id: agentId,
          endpoint_url: endpoint,
          max_tests: maxTests,
          force_new_version: false,
          enabled_domain_packs: enabledDomainPacks,
          target_tier: targetTier,
          selected_test_ids: selectedIds,
        });
        createdNewSuite = true;
        addToast({
          type: "success",
          title: "Suite created",
          message: `${result.agent_id} frozen with ${result.optimized_pack_size} tests. Review the pack, then run assurance.`,
        });
      }
      await refreshSuites();
      setActiveAgentId(agentId);
      setPreviewData(null);
      await loadFrozenSuite(agentId);
      setJustCreatedPack(createdNewSuite);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({
        type: "error",
        title: frozenDetail ? "Sync Failed" : "Save Failed",
        message: msg,
      });
    } finally {
      setIsSavingSuite(false);
    }
  };

  const [isProbing, setIsProbing] = useState(false);
  const [probeStatus, setProbeStatus] = useState<{ ok: boolean; text: string } | null>(null);

  const handleCopyPrompt = () => {
    if (!currentTest) return;
    navigator.clipboard.writeText(currentTest.user_prompt);
    addToast({
      type: "info",
      title: "Prompt Copied",
      message: `Copied prompt for ${currentTest.id}`,
    });
  };

  const handleProbeEndpoint = async () => {
    const url = endpointUrl.trim();
    if (!url) return;
    if (!url.includes("/chat")) {
      addToast({
        type: "warning",
        title: "Check endpoint path",
        message: "Agent endpoints expect a path like http://127.0.0.1:8770/chat (include /chat).",
      });
    }
    setIsProbing(true);
    setProbeStatus(null);
    try {
      const result = await probeAgentEndpoint(url);
      const latency = Math.round(result.latency_ms);
      if (result.reachable) {
        setProbeStatus({ ok: true, text: `HTTP ${result.http_status} (${latency}ms)` });
        addToast({
          type: "success",
          title: "Endpoint reachable",
          message: `Engine probe: HTTP ${result.http_status} in ${latency}ms`,
        });
      } else {
        const detail = result.error || `HTTP ${result.http_status}`;
        setProbeStatus({ ok: false, text: "Unreachable" });
        addToast({
          type: "error",
          title: "Probe failed",
          message: detail,
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setProbeStatus({ ok: false, text: "Unreachable" });
      addToast({
        type: "error",
        title: "Probe failed",
        message: msg,
      });
    } finally {
      setIsProbing(false);
    }
  };

  const capabilityCount = (requirementsText.match(/^[-*]\s+.+$/gm) || []).length;

  const currentTest: CandidateTest | undefined =
    optimizedPack?.tests?.[activeTestIndex];

  /** Frozen/preview pack test — same JSON shape as GET /v1/suites (no fictional TS harness). */
  const testCaseJson = currentTest
    ? JSON.stringify(currentTest, null, 2)
    : "{\n  \"message\": \"Select a test case to view engine CandidateTest JSON.\"\n}";

  const packTestCount = optimizedPack?.tests?.length ?? 0;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {justCreatedPack && frozenDetail && (
        <div className="mb-5 flex flex-col gap-3 rounded-md border border-primary/30 bg-primary/5 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-foreground">
              Suite frozen — {packTestCount} test{packTestCount === 1 ? "" : "s"}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Review each case in the inspector, then run them against your agent in Assurance.
            </p>
          </div>
          <Button
            type="button"
            className="shrink-0"
            onClick={() => navigateConsoleView("assurance")}
          >
            <Play className="mr-2 h-3.5 w-3.5 fill-current" />
            Go to Assurance
          </Button>
        </div>
      )}
      {/* Two Balanced Columns matching Shadcn Dashboard Cards Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (5 Cols): Specification & Settings */}
        <div className="lg:col-span-5 flex flex-col gap-5">
          {/* Core Configuration & Requirements Card */}
          <Card className="border border-border bg-card shadow-xs">
            <CardHeader className="p-4 pb-2 border-b border-border/50">
              <CardTitle className="text-xs font-semibold text-foreground">
                Agent Specification & Ceiling
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 p-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="min-w-0">
                  <label className="mb-1.5 block text-xs font-medium text-foreground">
                    Agent ID
                  </label>
                  <Input
                    type="text"
                    value={agentId}
                    onChange={(e) => setAgentId(e.target.value)}
                    onBlur={() => {
                      const id = agentId.trim();
                      if (!id) return;
                      setPreviewData(null);
                      setActiveAgentId(id);
                      loadFrozenSuite(id);
                    }}
                    placeholder="e.g. refund-agent"
                    className="font-mono text-xs w-full"
                  />
                </div>
                <div className="min-w-0 sm:col-span-2">
                  <div className="mb-1.5 flex items-center justify-between gap-2">
                    <label className="text-xs font-medium text-foreground shrink-0">
                      Target Endpoint
                    </label>
                    {probeStatus && (
                      <span
                        className={`font-mono text-[10px] ${
                          probeStatus.ok ? "text-emerald-600 dark:text-emerald-400" : "text-amber-600 dark:text-amber-400"
                        }`}
                      >
                        {probeStatus.text}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-1.5 min-w-0">
                    <Input
                      type="url"
                      value={endpointUrl}
                      onChange={(e) => setEndpointUrl(e.target.value)}
                      placeholder={SAMPLE_AGENT_ENDPOINT_PLACEHOLDER}
                      className="font-mono text-xs flex-1 min-w-0"
                      spellCheck={false}
                    />
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={handleProbeEndpoint}
                      disabled={isProbing || !endpointUrl.trim()}
                      className="h-9 px-3 shrink-0"
                      title="Probe endpoint reachability"
                    >
                      {isProbing ? <RefreshCw className="h-3 w-3 animate-spin" /> : "Probe"}
                    </Button>
                  </div>
                </div>
              </div>

              {/* PRD Editor */}
              <div>
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <label className="text-xs font-medium text-foreground">
                    PRD / Capabilities Markdown
                  </label>
                  <div className="flex items-center gap-2">
                    <input
                      ref={prdFileInputRef}
                      type="file"
                      accept={PRD_FILE_ACCEPT}
                      className="hidden"
                      onChange={handlePrdFileSelected}
                    />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-[10px] px-2"
                      onClick={() => prdFileInputRef.current?.click()}
                    >
                      <Upload className="h-3 w-3 mr-1" />
                      Import file
                    </Button>
                    <div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground">
                      {capabilityCount > 0 && (
                        <span className="text-primary font-semibold">
                          {capabilityCount} capabilities •
                        </span>
                      )}
                      <span>{requirementsText.length} chars</span>
                    </div>
                  </div>
                </div>
                <Textarea
                  value={requirementsText}
                  onChange={(e) => setRequirementsText(e.target.value)}
                  rows={11}
                  className="font-mono text-xs leading-relaxed"
                  placeholder="# Paste Agent PRD or Capability Manifest..."
                />
              </div>

              {availablePacks.length > 0 && (
                <div className="space-y-2 pt-1 border-t border-border pt-3">
                  <span className="text-xs font-medium text-foreground">Domain packs</span>
                  <div className="flex flex-col gap-2">
                    {availablePacks.map((pack) => (
                      <label
                        key={pack.id}
                        className="flex items-center gap-2 text-xs text-muted-foreground cursor-pointer"
                      >
                        <input
                          type="checkbox"
                          className="rounded border-border"
                          checked={enabledDomainPacks.includes(pack.id)}
                          onChange={(e) => {
                            setEnabledDomainPacks((prev) =>
                              e.target.checked
                                ? [...prev, pack.id]
                                : prev.filter((id) => id !== pack.id),
                            );
                          }}
                        />
                        <span>{pack.display_name}</span>
                        <span className="font-mono text-[10px] opacity-70">({pack.id})</span>
                      </label>
                    ))}
                  </div>
                </div>
              )}

              {/* Assurance Budget & Priority Tiers */}
              {previewData?.marginal_curve && previewData.marginal_curve.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-border">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-foreground">
                      Assurance Budget & Tiers
                    </span>
                    <button
                      type="button"
                      onClick={() => handleSelectTier("ALL")}
                      className={`text-[10px] font-mono px-2 py-0.5 rounded transition-colors cursor-pointer ${
                        selectedTier === "ALL"
                          ? "bg-primary/15 text-primary font-bold border border-primary/30"
                          : "text-muted-foreground hover:text-foreground border border-border"
                      }`}
                    >
                      All Tiers
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                    {previewData.marginal_curve.map((proj) => {
                      const isSelected = selectedTier === proj.tier;
                      return (
                        <button
                          key={proj.tier}
                          type="button"
                          onClick={() => handleSelectTier(proj.tier)}
                          className={`flex flex-col text-left p-2.5 rounded-lg border transition-all cursor-pointer ${
                            isSelected
                              ? "border-primary bg-primary/10 shadow-xs ring-1 ring-primary/40"
                              : "border-border bg-card/60 hover:bg-muted/40 hover:border-border/80"
                          }`}
                        >
                          <div className="flex items-center justify-between w-full mb-1">
                            <span
                              className={`text-[10px] font-bold font-mono px-1.5 py-0.2 rounded border ${
                                proj.tier === "P0"
                                  ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20"
                                  : proj.tier === "P1"
                                    ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
                                    : "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
                              }`}
                            >
                              {proj.tier}
                            </span>
                            <span className="text-[11px] font-mono font-bold text-foreground">
                              {Math.round(proj.projected_coverage_pct * 100)}%
                            </span>
                          </div>
                          <span className="text-xs font-medium text-foreground truncate">
                            {proj.label}
                          </span>
                          <span className="text-[10px] font-mono text-muted-foreground mt-1">
                            {proj.target_test_count} tests • ~{(proj.estimated_latency_ms / 1000).toFixed(0)}s
                          </span>
                          <span className="text-[10px] text-muted-foreground">
                            Floors: {proj.mandatory_floors_covered}/{proj.mandatory_floors_total}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Optimizer Slider */}
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-foreground">
                    Optimizer Ceiling (k tests)
                  </span>
                  <span className="font-mono text-xs font-bold text-primary">
                    {maxTests} tests
                  </span>
                </div>
                <Slider
                  min={3}
                  max={Math.max(25, Math.min(100, candidatePoolSize || 25))}
                  step={1}
                  value={[maxTests]}
                  onValueChange={(vals) => {
                    setMaxTests(vals[0]);
                    if (selectedTier !== "ALL") setSelectedTier("ALL");
                  }}
                  className="py-1"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                  <span>Fast (3)</span>
                  <span>Target ({maxTests})</span>
                  <span>Max ({Math.max(25, Math.min(100, candidatePoolSize || 25))})</span>
                </div>
              </div>

              {/* Actions */}
              <div className="mt-2 flex gap-3">
                <Button
                  variant="outline"
                  onClick={handlePreview}
                  disabled={isLoadingPreview}
                  className="flex-1 h-10 text-xs"
                >
                  {isLoadingPreview ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" />
                  ) : (
                    <Eye className="h-3.5 w-3.5 mr-2" />
                  )}
                  <span>Preview Pack</span>
                </Button>

                <Button
                  variant="default"
                  onClick={handleSaveSuite}
                  disabled={isSavingSuite}
                  className="flex-1 h-10 text-xs shadow-xs"
                >
                  {isSavingSuite ? (
                    <RefreshCw className="h-3.5 w-3.5 animate-spin mr-2" />
                  ) : (
                    <Save className="h-3.5 w-3.5 mr-2" />
                  )}
                  <span>{frozenDetail ? "Update pack" : "Create suite"}</span>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column (7 Cols): The Code & Verification Terminal */}
        <div className="lg:col-span-7 flex flex-col gap-5">
          <Card className="border border-border bg-card shadow-xs flex flex-col overflow-hidden">
            {/* Terminal Top Window Bar */}
            <div className="flex items-center justify-between border-b border-border bg-muted/30 px-4 py-3">
              {/* Window Controls */}
              <div className="flex items-center gap-2">
                <div className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
                <div className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
                <div className="h-2.5 w-2.5 rounded-full bg-muted-foreground/30" />
                <span className="ml-2 font-mono text-xs text-muted-foreground">
                  {terminalViewMode === "monaco" ? "test-case.json" : "test-inspector"}
                </span>
              </div>

              <div className="flex items-center gap-2">
                {/* View Mode Toggle */}
                <div className="flex items-center gap-1 rounded-md border border-border bg-card p-0.5">
                  <button
                    onClick={() => setTerminalViewMode("cards")}
                    className={`flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer ${
                      terminalViewMode === "cards"
                        ? "bg-muted text-foreground font-semibold shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                    title="Structured Assertion Cards View"
                  >
                    <LayoutTemplate className="h-3 w-3" />
                    <span>Card View</span>
                  </button>
                  <button
                    onClick={() => setTerminalViewMode("monaco")}
                    className={`flex items-center gap-1.5 rounded px-2 py-0.5 text-[11px] font-medium transition-colors cursor-pointer ${
                      terminalViewMode === "monaco"
                        ? "bg-muted text-foreground font-semibold shadow-xs"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                    title="Raw CandidateTest JSON from API"
                  >
                    <Code2 className="h-3 w-3" />
                    <span>JSON</span>
                  </button>
                </div>

                {currentTest && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCopyPrompt}
                    className="h-6 px-2 text-[10px] font-mono"
                    title="Copy active test prompt"
                  >
                    <Copy className="h-3 w-3 mr-1" />
                    <span>Copy Prompt</span>
                  </Button>
                )}
                {optimizedPack?.tests && (
                  <Badge variant="outline" className="font-mono text-[11px]">
                    {optimizedPack.tests.length} tests
                    {packProvenance ? ` · ${packProvenance}` : ""}
                  </Badge>
                )}
                {(isLoadingFrozen || isLoadingPreview) && (
                  <RefreshCw className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
                )}
              </div>
            </div>

            {/* Test pack: vertical list + detail (Card View) or Monaco */}
            <div className="flex min-h-[420px] max-h-[min(72vh,640px)] flex-col bg-card">
              {optimizedPack?.tests && optimizedPack.tests.length > 0 ? (
                <>
                  <div
                    className="shrink-0 border-b border-border bg-muted/10 px-3 py-2"
                    role="listbox"
                    aria-label="Optimized test pack"
                  >
                    <div className="mb-2 flex items-center justify-between px-1">
                      <p className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
                        Test cases ({optimizedPack.tests.length})
                        {selectedTestIds.length > 0 && (
                          <span className="text-primary font-semibold ml-1.5">
                            ({selectedTestIds.length} included)
                          </span>
                        )}
                      </p>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => setSelectedTestIds(optimizedPack.tests.map((t) => t.id))}
                          className="text-[10px] font-mono text-muted-foreground hover:text-foreground cursor-pointer"
                        >
                          Select All
                        </button>
                        <span className="text-muted-foreground/40">•</span>
                        <button
                          type="button"
                          onClick={() => setSelectedTestIds([])}
                          className="text-[10px] font-mono text-muted-foreground hover:text-foreground cursor-pointer"
                        >
                          Clear
                        </button>
                      </div>
                    </div>
                    <div className="max-h-[220px] space-y-1.5 overflow-y-auto pr-1">
                      {optimizedPack.tests.map((test, idx) => {
                        const label = formatTestTabLabel(test, idx);
                        const selected = activeTestIndex === idx;
                        const isIncluded =
                          selectedTestIds.length === 0 || selectedTestIds.includes(test.id);
                        const tier = test.priority_tier || "P1";
                        return (
                          <div
                            key={test.id}
                            role="option"
                            aria-selected={selected}
                            onClick={() => setActiveTestIndex(idx)}
                            className={`flex w-full items-center gap-2.5 rounded-md border px-3 py-2 text-left font-mono text-xs leading-snug transition-colors cursor-pointer ${
                              selected
                                ? "border-primary bg-primary/5 text-foreground shadow-xs ring-1 ring-primary/25"
                                : "border-border bg-card text-muted-foreground hover:border-border/80 hover:bg-muted/30 hover:text-foreground"
                            } ${!isIncluded ? "opacity-50" : ""}`}
                          >
                            <input
                              type="checkbox"
                              checked={isIncluded}
                              onChange={(e) => {
                                e.stopPropagation();
                                setSelectedTestIds((prev) => {
                                  const currentList =
                                    prev.length === 0 ? optimizedPack.tests.map((t) => t.id) : prev;
                                  return currentList.includes(test.id)
                                    ? currentList.filter((id) => id !== test.id)
                                    : [...currentList, test.id];
                                });
                              }}
                              className="rounded border-border h-3.5 w-3.5 text-primary focus:ring-primary shrink-0 cursor-pointer"
                              title="Include in test suite"
                            />
                            <span
                              className={`shrink-0 text-[10px] font-bold font-mono px-1 py-0.2 rounded border ${
                                tier === "P0"
                                  ? "bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20"
                                  : tier === "P1"
                                    ? "bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20"
                                    : "bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20"
                              }`}
                            >
                              {tier}
                            </span>
                            <span className="line-clamp-1 flex-1">{label}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto p-5">
                    {terminalViewMode === "monaco" ? (
                      <CodeViewer
                        code={testCaseJson}
                        language="json"
                        height="320px"
                        readOnly={true}
                      />
                    ) : currentTest ? (
                      <div className="space-y-4" aria-live="polite">
                        <div className="flex flex-wrap items-center gap-2">
                          <span
                            className={`text-[10px] font-bold font-mono px-2 py-0.5 rounded border ${
                              currentTest.priority_tier === "P0"
                                ? "bg-rose-500/15 text-rose-700 dark:text-rose-400 border-rose-500/30"
                                : currentTest.priority_tier === "P1"
                                  ? "bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/30"
                                  : "bg-purple-500/15 text-purple-700 dark:text-purple-400 border-purple-500/30"
                            }`}
                          >
                            Tier: {currentTest.priority_tier || "P1"}
                          </span>
                          <Badge variant="outline" className="font-mono text-[10px]">
                            cap: {currentTest.capability_id}
                          </Badge>
                          <Badge variant="outline" className="font-mono text-[10px]">
                            persona: {currentTest.persona_id}
                          </Badge>
                          <Badge variant="outline" className="font-mono text-[10px]">
                            category: {currentTest.category}
                          </Badge>
                          {currentTest.is_mandatory && (
                            <Badge variant="warn" className="text-[10px]">
                              Mandatory floor
                            </Badge>
                          )}
                        </div>

                        <div>
                          <div className="mb-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                            Input Prompt (Sent to Target Agent Endpoint)
                          </div>
                          <div className="rounded-lg border border-border bg-muted/20 p-3.5 font-mono text-xs text-foreground leading-relaxed">
                            {currentTest.user_prompt}
                          </div>
                        </div>

                        <div>
                          <div className="mb-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                            Expected Observable Behavior (Verification Criterion)
                          </div>
                          <div className="rounded-lg border-l-2 border-primary border-y border-r border-border bg-primary/5 p-3.5 font-mono text-xs text-foreground leading-relaxed">
                            {currentTest.expected_behavior}
                          </div>
                        </div>

                        {currentTest.rationale && (
                          <div className="text-xs text-muted-foreground">
                            <span className="font-semibold text-foreground">
                              Hypothesis rationale:
                            </span>{" "}
                            {currentTest.rationale}
                          </div>
                        )}
                      </div>
                    ) : null}
                  </div>
                </>
              ) : (
                <div className="flex flex-1 flex-col items-center justify-center p-5 text-center">
                  <Terminal className="mb-3 h-10 w-10 text-muted-foreground/40" />
                  <p className="text-sm font-medium text-foreground">No test pack generated yet</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Freeze a suite or run &quot;Preview Pack&quot; to load tests from the engine API.
                  </p>
                </div>
              )}
            </div>

            {/* Bottom Issues / Set-Cover Drawer */}
            <div className="border-t border-border bg-muted/20">
              <Tabs
                value={activeBottomTab}
                onValueChange={(v) =>
                  setActiveBottomTab(v as "gaps" | "floors" | "compression")
                }
                className="w-full"
              >
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
                  <TabsList className="h-auto bg-transparent border-0 p-0 gap-1">
                    <TabsTrigger value="gaps" className="text-xs px-2.5 py-1">
                      Coverage Breakdown
                    </TabsTrigger>
                    <TabsTrigger value="floors" className="text-xs px-2.5 py-1">
                      Mandatory Floors
                    </TabsTrigger>
                    <TabsTrigger value="compression" className="text-xs px-2.5 py-1">
                      Set-Cover Stats
                    </TabsTrigger>
                  </TabsList>
                </div>

                <div className="p-4 text-xs max-h-44 overflow-y-auto">
                  {!coverageReport ? (
                    <div className="text-muted-foreground italic">
                      No coverage data yet. Load a frozen suite or run Preview Pack via the API.
                    </div>
                  ) : (
                    <>
                  <TabsContent value="gaps" className="mt-0">
                    <div className="space-y-2.5">
                      <div className="grid grid-cols-3 gap-2.5">
                        {Object.entries(coverageReport.axes).map(([axis, ratio]) => (
                          <div
                            key={axis}
                            className="rounded border border-border bg-card p-2.5 shadow-xs"
                          >
                            <div className="flex justify-between text-[11px]">
                              <span className="text-muted-foreground">{axis}</span>
                              <span className="font-mono font-bold text-foreground">
                                {Math.round(ratio * 100)}%
                              </span>
                            </div>
                            <div className="mt-1.5 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                              <div
                                className="h-full rounded-full bg-primary transition-all duration-300"
                                style={{ width: `${Math.round(ratio * 100)}%` }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                      {coverageReport.critical_uncovered?.length > 0 && (
                        <div className="flex flex-col gap-2 rounded border border-amber-500/30 bg-amber-500/10 p-2.5 text-amber-700 dark:text-amber-400">
                          <div className="flex items-center gap-2">
                            <AlertCircle className="h-4 w-4 shrink-0" />
                            <span>
                              Critical uncovered tags:{" "}
                              {coverageReport.critical_uncovered.join(", ")}
                            </span>
                          </div>
                          {frozenDetail?.latest_run && (
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              className="h-8 w-fit text-xs"
                              disabled={isExtendingGaps}
                              onClick={handleExtendGaps}
                            >
                              {isExtendingGaps ? (
                                <RefreshCw className="h-3.5 w-3.5 animate-spin mr-1.5" />
                              ) : null}
                              Close gaps from pool
                            </Button>
                          )}
                        </div>
                      )}
                    </div>
                  </TabsContent>
                  <TabsContent value="floors" className="mt-0">
                    {!coverageReport ? (
                      <p className="text-xs text-muted-foreground">
                        Preview or load a frozen pack to see mandatory floor coverage from the engine.
                      </p>
                    ) : (coverageReport.critical_uncovered?.length ?? 0) === 0 ? (
                      <div className="flex items-center gap-2 text-foreground text-xs">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        <span>No mandatory gaps in the selected pack (optimizer coverage).</span>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {coverageReport.critical_uncovered.map((gap) => (
                          <div key={gap} className="flex items-center gap-2 text-foreground text-xs">
                            <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
                            <span className="font-mono">{gap}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </TabsContent>
                  <TabsContent value="compression" className="mt-0">
                    <div className="space-y-1.5 font-mono text-muted-foreground">
                      <div>
                        Candidate pool:{" "}
                        <span className="text-foreground font-semibold">
                          {candidatePoolSize}
                        </span>
                      </div>
                      <div>
                        Optimized pack:{" "}
                        <span className="text-primary font-bold">
                          {optimizedPack?.tests?.length ?? 0} tests
                        </span>
                      </div>
                      <div className="text-[11px] text-muted-foreground">
                        Algorithm: Weighted greedy set-cover with mandatory floors
                      </div>
                    </div>
                  </TabsContent>
                    </>
                  )}
                </div>
              </Tabs>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
};
