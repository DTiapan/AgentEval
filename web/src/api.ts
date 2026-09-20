import {
  PreviewResponse,
  SuiteDetailResult,
  SuiteInitResult,
  SuiteListItem,
  SuiteRunReport,
} from "./types";

const API_BASE = "";

async function parseJson<T>(response: Response): Promise<T> {
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail ?? body);
    throw new Error(detail || response.statusText);
  }
  return body as T;
}

export async function fetchHealth(): Promise<{ status: string; version: string }> {
  const res = await fetch(`${API_BASE}/health`);
  return parseJson(res);
}

export async function listSuites(): Promise<SuiteListItem[]> {
  const res = await fetch(`${API_BASE}/v1/suites`);
  const body = await parseJson<{ suites: SuiteListItem[] }>(res);
  return body.suites;
}

export async function getSuiteDetail(agentId: string): Promise<SuiteDetailResult> {
  const res = await fetch(`${API_BASE}/v1/suites/${encodeURIComponent(agentId)}`);
  return parseJson(res);
}

export async function previewSuite(payload: {
  requirements_text: string;
  agent_id: string;
  endpoint_url?: string;
  max_tests?: number;
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

export async function runSuite(
  agentId: string,
  endpointUrl?: string,
): Promise<SuiteRunReport> {
  const res = await fetch(`${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ endpoint_url: endpointUrl || null }),
  });
  return parseJson(res);
}

export async function getLatestRun(agentId: string): Promise<SuiteRunReport> {
  const res = await fetch(`${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/runs/latest`);
  return parseJson(res);
}

export function getSuiteReportUrl(agentId: string, runId?: string): string {
  const params = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
  return `${API_BASE}/v1/suites/${encodeURIComponent(agentId)}/report${params}`;
}
