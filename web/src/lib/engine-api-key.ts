/** Browser storage for server `AGENTEVAL_API_KEY` (sent as `X-API-Key` on `/v1/*`). */

import {
  getActiveWorkspaceId,
  workspaceApiKeyStorageKey,
} from "@/lib/workspace-session";

/** @deprecated Legacy global key; prefer per-workspace storage. */
export const ENGINE_API_KEY_STORAGE = "AGENTEVAL_API_KEY";

export const ENGINE_API_KEY_CHANGED_EVENT = "agenteval-api-key-changed";

function readScopedApiKey(workspaceId: string | null): string | null {
  if (typeof window === "undefined") return null;
  if (workspaceId) {
    const scoped = localStorage.getItem(workspaceApiKeyStorageKey(workspaceId))?.trim();
    if (scoped) return scoped;
  }
  const legacy = localStorage.getItem(ENGINE_API_KEY_STORAGE)?.trim();
  return legacy || null;
}

export function readEngineApiKey(): string | null {
  return readScopedApiKey(getActiveWorkspaceId());
}

export function writeEngineApiKey(value: string | null | undefined): void {
  if (typeof window === "undefined") return;
  const trimmed = value?.trim();
  const workspaceId = getActiveWorkspaceId();
  if (!workspaceId) {
    if (!trimmed) localStorage.removeItem(ENGINE_API_KEY_STORAGE);
    else localStorage.setItem(ENGINE_API_KEY_STORAGE, trimmed);
  } else if (!trimmed) {
    localStorage.removeItem(workspaceApiKeyStorageKey(workspaceId));
  } else {
    localStorage.setItem(workspaceApiKeyStorageKey(workspaceId), trimmed);
  }
  window.dispatchEvent(new Event(ENGINE_API_KEY_CHANGED_EVENT));
}

export function hasEngineApiKey(): boolean {
  return readEngineApiKey() !== null;
}

export function isEngineAuthErrorMessage(message: string): boolean {
  const lower = message.toLowerCase();
  return (
    lower.includes("missing api key") ||
    lower.includes("invalid api key") ||
    lower.includes("unauthorized") ||
    /\b401\b/.test(message)
  );
}
