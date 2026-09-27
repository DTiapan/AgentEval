import {
  PreviewResponse,
  SuiteDetailResult,
  SuiteInitResult,
  SuiteListItem,
  SuiteRunReport,
  SuiteGapLoopResult,
  SuiteSyncResult,
} from "./types";
import { formatApiErrorBody } from "@/lib/api-error";

const API_BASE = "";

async function parseJson<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(formatApiErrorBody(body, response.statusText || "Request failed"));
  }
  return body as T;
}

export type EnginePersistence = {
  sqlite_enabled: boolean;
  database_path: string | null;
  suite_root: string;
};

export type EngineHealth = {
  status: string;
  version: string;
  persistence?: EnginePersistence;
};

export async function fetchHealth(): Promise<EngineHealth> {
  const res = await fetch(`${API_BASE}/health`);
  return parseJson(res);
}

export async function listDomainPacks() {
  const res = await fetch(`${API_BASE}/v1/packs`);
  return parseJson<import("./types").DomainPackListResult>(res);
}

export async function listSuites(): Promise<SuiteListItem[]> {
  const res = await fetch(`${API_BASE}/v1/suites`);
  const body = await parseJson<{ suites: SuiteListItem[] }>(res);
  return body.suites;
}

/** Server-side POST probe (same as engine black-box runner; no browser CORS). */
export type EngineEndpointProbeResult = {
  endpoint_url: string;
  reachable: boolean;
  http_status: number;
  latency_ms: number;
  error?: string;
};

export async function probeAgentEndpoint(
  endpointUrl: string,
): Promise<EngineEndpointProbeResult> {
  const res = await fetch(`${API_BASE}/v1/endpoints/probe`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint_url: endpointUrl }),
  });
  return parseJson(res);
}

export async function getSuiteDetail(agentId: string): Promise<SuiteDetailResult> {
  const res = await fetch(`${API_BASE}/v1/suites/${encodeURIComponent(agentId)}`);
  return parseJson(res);
}

export async function getSuiteRequirements(agentId: string) {
  const res = await fetch(
    `${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/requirements`,
  );
  return parseJson<import("./types").SuiteRequirementsResult>(res);
}

export async function previewSuite(payload: {
  requirements_text: string;
  agent_id: string;
  endpoint_url?: string;
  max_tests?: number;
  target_tier?: string;
  selected_test_ids?: string[];
}): Promise<PreviewResponse> {
  const res = await fetch(`${API_BASE}/v1/suites/preview`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      probe_endpoint: Boolean(payload.endpoint_url),
      max_tests: payload.max_tests ?? 10,
      ...payload,
    }),
  });
  return parseJson(res);
}

export async function initSuite(payload: {
  requirements_text: string;
  agent_id: string;
  endpoint_url?: string;
  max_tests?: number;
  force_new_version?: boolean;
  enabled_domain_packs?: string[];
  target_tier?: string;
  selected_test_ids?: string[];
}): Promise<SuiteInitResult> {
  const res = await fetch(`${API_BASE}/v1/suites`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      probe_endpoint: Boolean(payload.endpoint_url),
      max_tests: payload.max_tests ?? 10,
      force_new_version: payload.force_new_version ?? false,
      ...payload,
    }),
  });
  return parseJson(res);
}

export async function extendSuiteGaps(
  agentId: string,
  payload?: { max_add?: number; run_id?: string },
): Promise<SuiteGapLoopResult> {
  const res = await fetch(
    `${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/extend-gaps`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        max_add: payload?.max_add ?? 5,
        run_id: payload?.run_id || null,
      }),
    },
  );
  return parseJson(res);
}

export async function syncSuite(
  agentId: string,
  payload: {
    requirements_text: string;
    endpoint_url?: string;
    max_tests?: number;
    enabled_domain_packs?: string[];
    target_tier?: string;
    selected_test_ids?: string[];
  },
): Promise<SuiteSyncResult> {
  const res = await fetch(`${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/sync`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      probe_endpoint: Boolean(payload.endpoint_url),
      max_tests: payload.max_tests ?? 10,
      ...payload,
    }),
  });
  return parseJson(res);
}

export async function runSuite(
  agentId: string,
  endpointUrl?: string,
  auditLogDbPath?: string,
): Promise<SuiteRunReport> {
  const res = await fetch(`${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      endpoint_url: endpointUrl || null,
      audit_log_db_path: auditLogDbPath || null,
    }),
  });
  return parseJson(res);
}

export async function getLatestRun(agentId: string): Promise<SuiteRunReport> {
  const res = await fetch(`${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/runs/latest`);
  return parseJson(res);
}

export function getSuiteReportUrl(
  agentId: string,
  runId?: string,
  options?: { embed?: boolean; theme?: "light" | "dark" },
): string {
  const params = new URLSearchParams();
  if (runId) params.set("run_id", runId);
  if (options?.embed) params.set("embed", "true");
  if (options?.theme) params.set("theme", options.theme);
  const query = params.toString();
  return `${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/report${query ? `?${query}` : ""}`;
}

/** Fetch sealed HTML report from engine and save locally (same payload as GET report). */
export async function downloadSuiteReport(
  agentId: string,
  runId?: string,
  options?: { theme?: "light" | "dark" },
): Promise<void> {
  const url = getSuiteReportUrl(agentId, runId, { theme: options?.theme });
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(formatApiErrorBody(body, res.statusText || "Report download failed"));
  }
  const blob = await res.blob();
  const runSuffix = runId ? `-${runId.slice(0, 8)}` : "";
  const filename = `agenteval-${agentId}${runSuffix}-report.html`;
  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(objectUrl);
}
