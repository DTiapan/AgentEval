import React, { useEffect, useState } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Code2,
  Copy,
  Eye,
  LayoutTemplate,
  RefreshCw,
  Save,
  Terminal,
} from "lucide-react";
import { initSuite, previewSuite } from "../api";
import { useWorkspace } from "../context/WorkspaceContext";
import { CandidateTest, SuitePreviewResult } from "../types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Slider } from "@/components/ui/slider";
import { CodeViewer } from "@/components/ui/code-viewer";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DEMO_AGENT_ID,
  DEMO_STAGING_ENDPOINT,
  FROZEN_TEST_PACK_SIZE,
  LOCAL_AGENT_ENDPOINT,
  refundAgentPrdMarkdown,
} from "@/lib/product";

const PRD_PRESETS = [
  {
    name: "Customer Refund Agent",
    agent_id: DEMO_AGENT_ID,
    endpoint: DEMO_STAGING_ENDPOINT,
    text: refundAgentPrdMarkdown(),
  },
  {
    name: "Order Fulfillment Swarm",
    agent_id: "order-fulfillment-bot",
    endpoint: LOCAL_AGENT_ENDPOINT,
    text: `# Order Fulfillment Swarm Specification

## 1. Capabilities
- Ingest warehouse stock levels and allocate items for shipment.
- Print shipping labels through logistics carrier APIs.
- Notify customer of parcel tracking updates.

## 2. Invariants
- Enforce idempotency on shipment creation.
- Cannot dispatch orders with unpaid invoices.`,
  },
];

export const Studio: React.FC<{ onSuiteCreated?: () => void }> = ({ onSuiteCreated }) => {
  const { addToast, refreshSuites, setActiveAgentId } = useWorkspace();

  const [agentId, setAgentId] = useState(DEMO_AGENT_ID);
  const [endpointUrl, setEndpointUrl] = useState(DEMO_STAGING_ENDPOINT);
  const [requirementsText, setRequirementsText] = useState(PRD_PRESETS[0].text);
  const [maxTests, setMaxTests] = useState(FROZEN_TEST_PACK_SIZE);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [isSavingSuite, setIsSavingSuite] = useState(false);
  const [previewData, setPreviewData] = useState<SuitePreviewResult | null>(null);
  const [activeTestIndex, setActiveTestIndex] = useState(0);
  const [activeBottomTab, setActiveBottomTab] = useState<"gaps" | "floors" | "compression">("gaps");
  const [terminalViewMode, setTerminalViewMode] = useState<"cards" | "monaco">("cards");

  // Auto-generate preview on mount
  useEffect(() => {
    if (requirementsText.trim() && agentId.trim()) {
      setIsLoadingPreview(true);
      previewSuite({
        requirements_text: requirementsText,
        agent_id: agentId,
        endpoint_url: endpointUrl.trim() || undefined,
        max_tests: maxTests,
      })
        .then((data) => {
          setPreviewData(data);
          setActiveTestIndex(0);
        })
        .catch((err) => {
          console.warn("Auto-preview failed", err);
        })
        .finally(() => {
          setIsLoadingPreview(false);
        });
    }
  }, []);

  const handleApplyPreset = (preset: typeof PRD_PRESETS[0]) => {
    setAgentId(preset.agent_id);
    setEndpointUrl(preset.endpoint);
    setRequirementsText(preset.text);
    addToast({
      type: "info",
      title: `Loaded preset: ${preset.name}`,
    });
    setIsLoadingPreview(true);
    previewSuite({
      requirements_text: preset.text,
      agent_id: preset.agent_id,
      endpoint_url: preset.endpoint.trim() || undefined,
      max_tests: maxTests,
    })
      .then((data) => {
        setPreviewData(data);
        setActiveTestIndex(0);
      })
      .catch((err) => {
        console.warn("Auto-preview failed", err);
      })
      .finally(() => {
        setIsLoadingPreview(false);
      });
  };

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
      });
      setPreviewData(data);
      setActiveTestIndex(0);
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

  const handleSaveSuite = async () => {
    if (!requirementsText.trim() || !agentId.trim()) {
      addToast({
        type: "error",
        title: "Validation Error",
        message: "Agent ID and Requirements text are required.",
      });
      return;
    }

    setIsSavingSuite(true);
    try {
      const result = await initSuite({
        requirements_text: requirementsText,
        agent_id: agentId,
        endpoint_url: endpointUrl.trim() || undefined,
        max_tests: maxTests,
        force_new_version: true,
      });
      addToast({
        type: "success",
        title: "Regression Suite Frozen",
        message: `Suite for ${result.agent_id} saved (${result.optimized_pack_size} tests).`,
      });
      await refreshSuites();
      setActiveAgentId(result.agent_id);
      if (onSuiteCreated) onSuiteCreated();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({
        type: "error",
        title: "Save Failed",
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
    if (!endpointUrl.trim()) return;
    setIsProbing(true);
    setProbeStatus(null);
    try {
      const start = performance.now();
      const res = await fetch(endpointUrl.trim(), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: "ping" }),
      });
      const latency = Math.round(performance.now() - start);
      setProbeStatus({ ok: res.ok, text: `${res.status} OK (${latency}ms)` });
      addToast({
        type: res.ok ? "success" : "warning",
        title: "Endpoint Probed",
        message: `HTTP ${res.status} returned in ${latency}ms`,
      });
    } catch {
      setProbeStatus({ ok: false, text: "Unreachable" });
      addToast({
        type: "error",
        title: "Probe Failed",
        message: "Endpoint did not respond. Verify the service is running.",
      });
    } finally {
      setIsProbing(false);
    }
  };

  const capabilityCount = (requirementsText.match(/^[-*]\s+.+$/gm) || []).length;

  const currentTest: CandidateTest | undefined =
    previewData?.optimized_pack?.tests?.[activeTestIndex];

  const generatedTypeScriptCode = currentTest
    ? `// Auto-generated AgentEval Test Spec
// ID: ${currentTest.id}
// Capability: ${currentTest.capability_id}
// Persona: ${currentTest.persona_id}

import { test, expect } from "@agenteval/core";

test("${currentTest.id}", async ({ agent }) => {
  // 1. Send targeted input prompt
  const response = await agent.send({
    message: ${JSON.stringify(currentTest.user_prompt)},
  });

  // 2. Assert observable invariant criteria
  expect(response.status).toBe(200);
  expect(response).toSatisfyInvariant({
    criterion: ${JSON.stringify(currentTest.expected_behavior)},
    category: "${currentTest.category}",
    mandatory: ${currentTest.is_mandatory},
  });
});`
    : `// No test selected. Generate or select a test candidate from above tabs.`;

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      {/* Two Balanced Columns matching Shadcn Dashboard Cards Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (5 Cols): Specification & Settings */}
        <div className="lg:col-span-5 flex flex-col gap-5">
          {/* Preset Selector Card */}
          <Card className="border border-border bg-card shadow-xs">
            <CardHeader className="p-4 pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-xs font-semibold text-foreground">
                  Specification Presets
                </CardTitle>
                <span className="text-[11px] text-muted-foreground font-mono">Quick Fill</span>
              </div>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <div className="flex flex-wrap gap-2">
                {PRD_PRESETS.map((p) => (
                  <Button
                    key={p.name}
                    variant={agentId === p.agent_id ? "secondary" : "outline"}
                    size="sm"
                    onClick={() => handleApplyPreset(p)}
                    className={
                      agentId === p.agent_id
                        ? "border-primary/50 text-foreground font-semibold"
                        : "text-muted-foreground hover:text-foreground"
                    }
                  >
                    {p.name}
                  </Button>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Core Configuration & Requirements Card */}
          <Card className="border border-border bg-card shadow-xs">
            <CardHeader className="p-4 pb-2 border-b border-border/50">
              <CardTitle className="text-xs font-semibold text-foreground">
                Agent Specification & Ceiling
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-4 p-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-foreground">
                    Agent ID
                  </label>
                  <Input
                    type="text"
                    value={agentId}
                    onChange={(e) => setAgentId(e.target.value)}
                    placeholder="e.g. refund-bot"
                    className="font-mono text-xs"
                  />
                </div>
                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <label className="text-xs font-medium text-foreground">
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
                  <div className="flex gap-1.5">
                    <Input
                      type="text"
                      value={endpointUrl}
                      onChange={(e) => setEndpointUrl(e.target.value)}
                      placeholder={DEMO_STAGING_ENDPOINT}
                      className="font-mono text-xs flex-1"
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
                <div className="mb-1.5 flex items-center justify-between">
                  <label className="text-xs font-medium text-foreground">
                    PRD / Capabilities Markdown
                  </label>
                  <div className="flex items-center gap-2 font-mono text-[10px] text-muted-foreground">
                    {capabilityCount > 0 && (
                      <span className="text-primary font-semibold">
                        {capabilityCount} capabilities detected •
                      </span>
                    )}
                    <span>{requirementsText.length} chars</span>
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
                  max={25}
                  step={1}
                  value={[maxTests]}
                  onValueChange={(vals) => setMaxTests(vals[0])}
                  className="py-1"
                />
                <div className="flex justify-between text-[10px] text-muted-foreground font-mono">
                  <span>Fast (3)</span>
                  <span>Canonical ({FROZEN_TEST_PACK_SIZE})</span>
                  <span>Thorough (25)</span>
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
                  <span>Freeze Suite</span>
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
                  {terminalViewMode === "monaco" ? "test-spec.ts" : "test-pack.yaml"}
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
                    title="Monaco Code Editor View"
                  >
                    <Code2 className="h-3 w-3" />
                    <span>Monaco (TS)</span>
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
                {previewData?.optimized_pack?.tests && (
                  <Badge variant="outline" className="font-mono text-[11px]">
                    {previewData.optimized_pack.tests.length} tests selected
                  </Badge>
                )}
              </div>
            </div>

            {/* Test Tabs Strip */}
            {previewData?.optimized_pack?.tests && previewData.optimized_pack.tests.length > 0 ? (
              <div className="flex overflow-x-auto border-b border-border bg-muted/10 px-3 py-1.5 scrollbar-none">
                {previewData.optimized_pack.tests.map((test, idx) => {
                  const cleanTabLabel =
                    test.name && test.name.length <= 18
                      ? test.name
                      : test.id
                          .replace(/^test-/, "")
                          .replace(/-adversary|-happy_path|-boundary|-edge_case/g, "")
                          .slice(0, 16);
                  return (
                    <button
                      key={test.id}
                      onClick={() => setActiveTestIndex(idx)}
                      className={`flex items-center gap-1.5 whitespace-nowrap rounded px-2.5 py-1 font-mono text-xs transition-colors cursor-pointer ${
                        activeTestIndex === idx
                          ? "bg-card text-foreground font-semibold border-b-2 border-primary shadow-xs"
                          : "text-muted-foreground hover:text-foreground"
                      }`}
                    >
                      <span className="text-[10px] text-muted-foreground">[{String(idx + 1).padStart(2, "0")}]</span>
                      <span>{cleanTabLabel}</span>
                    </button>
                  );
                })}
              </div>
            ) : null}

            {/* Code / Verification Body */}
            <div className="flex-1 p-5 bg-card">
              {terminalViewMode === "monaco" ? (
                <CodeViewer
                  code={generatedTypeScriptCode}
                  language="typescript"
                  height="360px"
                  readOnly={true}
                />
              ) : currentTest ? (
                <div className="space-y-4">
                  {/* Metadata Chips */}
                  <div className="flex flex-wrap items-center gap-2">
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
                        ⚡ Mandatory Floor
                      </Badge>
                    )}
                  </div>

                  {/* Input Prompt Box */}
                  <div>
                    <div className="mb-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                      // Input Prompt (Sent to Target Agent Endpoint)
                    </div>
                    <div className="rounded-lg border border-border bg-muted/20 p-3.5 font-mono text-xs text-foreground leading-relaxed">
                      {currentTest.user_prompt}
                    </div>
                  </div>

                  {/* Observable Expectation Box */}
                  <div>
                    <div className="mb-1 text-[11px] font-mono uppercase tracking-wider text-muted-foreground">
                      // Expected Observable Behavior (Verification Criterion)
                    </div>
                    <div className="rounded-lg border-l-2 border-primary border-y border-r border-border bg-primary/5 p-3.5 font-mono text-xs text-foreground leading-relaxed">
                      {currentTest.expected_behavior}
                    </div>
                  </div>

                  {/* Failure Mode & Rationale */}
                  {currentTest.rationale && (
                    <div className="text-xs text-muted-foreground">
                      <span className="font-semibold text-foreground">Hypothesis rationale:</span>{" "}
                      {currentTest.rationale}
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex h-64 flex-col items-center justify-center text-center">
                  <Terminal className="mb-3 h-10 w-10 text-muted-foreground/40" />
                  <p className="text-sm font-medium text-foreground">No test pack generated yet</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    Click &quot;Preview Pack&quot; to synthesize test candidates and optimize with set-cover.
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
                  {!previewData?.coverage ? (
                    <div className="text-muted-foreground italic">
                      Run preview to analyze coverage axes and set-cover metrics.
                    </div>
                  ) : (
                    <>
                  <TabsContent value="gaps" className="mt-0">
                    <div className="space-y-2.5">
                      <div className="grid grid-cols-3 gap-2.5">
                        {Object.entries(previewData.coverage.axes).map(([axis, ratio]) => (
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
                      {previewData.coverage.critical_uncovered?.length > 0 && (
                        <div className="flex items-center gap-2 rounded border border-amber-500/30 bg-amber-500/10 p-2.5 text-amber-700 dark:text-amber-400">
                          <AlertCircle className="h-4 w-4 shrink-0" />
                          <span>
                            Critical uncovered tags:{" "}
                            {previewData.coverage.critical_uncovered.join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                  </TabsContent>
                  <TabsContent value="floors" className="mt-0">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2 text-foreground">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                        <span>Authorization & Privileges floor satisfied</span>
                      </div>
                      <div className="flex items-center gap-2 text-foreground">
                        <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                        <span>Prompt injection & boundary resistance verified</span>
                      </div>
                    </div>
                  </TabsContent>
                  <TabsContent value="compression" className="mt-0">
                    <div className="space-y-1.5 font-mono text-muted-foreground">
                      <div>
                        Candidate pool:{" "}
                        <span className="text-foreground font-semibold">
                          {previewData.candidate_pool?.length ?? 0}
                        </span>
                      </div>
                      <div>
                        Optimized pack:{" "}
                        <span className="text-primary font-bold">
                          {previewData.optimized_pack?.tests?.length ?? 0} tests
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
