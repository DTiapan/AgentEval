import { getSuiteDetail } from "@/api";
import type { SuiteDetailResult } from "@/types";

const cache = new Map<string, SuiteDetailResult>();
const inflight = new Map<string, Promise<SuiteDetailResult>>();

/** Deduped GET /v1/suites/{id} — reuse across Studio ↔ Assurance tab switches. */
export async function fetchSuiteDetailCached(
  agentId: string,
  options?: { force?: boolean },
): Promise<SuiteDetailResult> {
  const id = agentId.trim();
  if (!id) {
    throw new Error("agent id is required");
  }
  if (!options?.force) {
    const hit = cache.get(id);
    if (hit) return hit;
    const pending = inflight.get(id);
    if (pending) return pending;
  } else {
    cache.delete(id);
    inflight.delete(id);
  }

  const request = getSuiteDetail(id)
    .then((detail) => {
      cache.set(id, detail);
      inflight.delete(id);
      return detail;
    })
    .catch((err) => {
      inflight.delete(id);
      throw err;
    });

  inflight.set(id, request);
  return request;
}

export function invalidateSuiteDetailCache(agentId?: string): void {
  if (agentId?.trim()) {
    const id = agentId.trim();
    cache.delete(id);
    inflight.delete(id);
  } else {
    cache.clear();
    inflight.clear();
  }
}

export function peekSuiteDetailCache(agentId: string): SuiteDetailResult | undefined {
  return cache.get(agentId.trim());
}
