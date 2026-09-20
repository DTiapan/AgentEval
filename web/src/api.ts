const API_BASE = "";

export type SuiteListItem = {
  agent_id: string;
  suite_version: number;
  requirements_fingerprint: string;
  endpoint_profile: string;
  pack_size: number;
  pool_size: number;
  has_latest_run: boolean;
};

export type CandidateTest = {
  id: string;
  name: string;
  category: string;
  user_prompt: string;
  expected_behavior: string;
};

export type TestPack = {
  tests: CandidateTest[];
  requirements_fingerprint: string;
};

export type SuiteRunReport = {
  run_id: string;
  agent_id: string;
  suite_version: number;
  passed: number;
  failed: number;
  unverifiable: number;
  results: {
    test_id: string;
    verdict: string;
    rationale: string;
  }[];
};

export type PreviewResponse = {
  agent_card: { id: string; name: string };
  requirements_fingerprint: string;
  candidate_pool: unknown[];
  optimized_pack: TestPack;
  coverage: { axes: Record<string, number>; critical_uncovered: string[] };
};

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
}): Promise<{ agent_id: string; optimized_pack_size: number }> {
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

export async function getSuiteDetail(agentId: string): Promise<{
  optimized_pack: TestPack;
  latest_run: SuiteRunReport | null;
}> {
  const res = await fetch(`${API_BASE}/v1/suites/${encodeURIComponent(agentId)}`);
  return parseJson(res);
}
