import type { Workspace } from "@/types";

/** Client-only workspaces until E-ORG / Firebase auth ships on the API. */

export const WORKSPACES_STORAGE_KEY = "agenteval_workspaces_v1";
export const ACTIVE_WORKSPACE_ID_KEY = "agenteval_active_workspace_id";
export const WORKSPACE_CHANGED_EVENT = "agenteval-workspace-changed";

export type StoredWorkspace = Workspace & {
  createdAt: string;
};

function dispatchWorkspaceChanged(): void {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(WORKSPACE_CHANGED_EVENT));
  }
}

export function slugifyWorkspaceName(name: string): string {
  const slug = name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  return slug || "workspace";
}

function newWorkspaceId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return `ws_${crypto.randomUUID()}`;
  }
  return `ws_${Math.random().toString(36).slice(2, 11)}`;
}

export function readStoredWorkspaces(): StoredWorkspace[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(WORKSPACES_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StoredWorkspace[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeStoredWorkspaces(workspaces: StoredWorkspace[]): void {
  localStorage.setItem(WORKSPACES_STORAGE_KEY, JSON.stringify(workspaces));
  dispatchWorkspaceChanged();
}

export function getActiveWorkspaceId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACTIVE_WORKSPACE_ID_KEY);
}

export function getActiveWorkspace(): StoredWorkspace | null {
  const id = getActiveWorkspaceId();
  if (!id) return null;
  return readStoredWorkspaces().find((w) => w.id === id) ?? null;
}

export function setActiveWorkspaceId(workspaceId: string | null): void {
  if (!workspaceId) {
    localStorage.removeItem(ACTIVE_WORKSPACE_ID_KEY);
  } else {
    localStorage.setItem(ACTIVE_WORKSPACE_ID_KEY, workspaceId);
  }
  dispatchWorkspaceChanged();
}

export function ensureDefaultWorkspace(): StoredWorkspace {
  const existing = readStoredWorkspaces();
  if (existing.length > 0) {
    const active = getActiveWorkspace();
    if (active) return active;
    setActiveWorkspaceId(existing[0].id);
    return existing[0];
  }

  const legacyName = "Local workspace";
  const created: StoredWorkspace = {
    id: newWorkspaceId(),
    name: legacyName,
    slug: slugifyWorkspaceName(legacyName),
    role: "OWNER",
    isEnterpriseCloud: false,
    createdAt: new Date().toISOString(),
  };
  writeStoredWorkspaces([created]);
  setActiveWorkspaceId(created.id);
  migrateLegacyGlobalApiKey(created.id);
  return created;
}

/** One-time: move pre-workspace `AGENTEVAL_API_KEY` into the first workspace. */
function migrateLegacyGlobalApiKey(workspaceId: string): void {
  const legacy = localStorage.getItem("AGENTEVAL_API_KEY");
  if (!legacy?.trim()) return;
  const scopedKey = workspaceApiKeyStorageKey(workspaceId);
  if (!localStorage.getItem(scopedKey)) {
    localStorage.setItem(scopedKey, legacy.trim());
  }
}

export function workspaceApiKeyStorageKey(workspaceId: string): string {
  return `agenteval_ws_${workspaceId}_api_key`;
}

export function createWorkspace(input: { name: string; slug?: string }): StoredWorkspace {
  const name = input.name.trim();
  if (name.length < 2) {
    throw new Error("Workspace name must be at least 2 characters.");
  }

  const workspaces = readStoredWorkspaces();
  let slug = slugifyWorkspaceName(input.slug?.trim() || name);
  const taken = new Set(workspaces.map((w) => w.slug));
  let suffix = 2;
  const base = slug;
  while (taken.has(slug)) {
    slug = `${base}-${suffix}`;
    suffix += 1;
  }

  const workspace: StoredWorkspace = {
    id: newWorkspaceId(),
    name,
    slug,
    role: "OWNER",
    isEnterpriseCloud: false,
    createdAt: new Date().toISOString(),
  };

  workspaces.push(workspace);
  writeStoredWorkspaces(workspaces);
  setActiveWorkspaceId(workspace.id);
  return workspace;
}

export function toWorkspaceView(stored: StoredWorkspace): Workspace {
  return {
    id: stored.id,
    name: stored.name,
    slug: stored.slug,
    role: stored.role,
    isEnterpriseCloud: stored.isEnterpriseCloud,
  };
}

export function hasActiveWorkspace(): boolean {
  return getActiveWorkspace() !== null;
}
