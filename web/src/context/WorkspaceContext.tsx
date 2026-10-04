import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { EngineHealth, deleteSuite, fetchHealth, listSuites } from "../api";
import {
  ENGINE_API_KEY_CHANGED_EVENT,
  hasEngineApiKey,
  isEngineAuthErrorMessage,
} from "@/lib/engine-api-key";
import {
  WORKSPACE_CHANGED_EVENT,
  createWorkspace,
  ensureDefaultWorkspace,
  getActiveWorkspace,
  readStoredWorkspaces,
  setActiveWorkspaceId,
  toWorkspaceView,
} from "@/lib/workspace-session";
import { SuiteListItem, Workspace } from "../types";

export type ToastMessage = {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message?: string;
};

interface WorkspaceContextValue {
  workspace: Workspace | null;
  workspaces: Workspace[];
  selectWorkspace: (workspaceId: string) => void;
  createAndSelectWorkspace: (name: string) => Workspace;
  syncWorkspacesFromStorage: () => void;
  suites: SuiteListItem[];
  activeAgentId: string | null;
  setActiveAgentId: (id: string | null) => void;
  refreshSuites: () => Promise<void>;
  deleteAgentSuite: (agentId: string) => Promise<boolean>;
  isLoadingSuites: boolean;
  engineHealth: EngineHealth | null;
  engineApiKeyConfigured: boolean;
  refreshEngineConnection: () => Promise<void>;
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  removeToast: (id: string) => void;
}

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);

function migrateLegacyBrowserSession(): void {
  if (readStoredWorkspaces().length > 0) return;
  const legacySignals = localStorage.getItem("AGENTEVAL_API_KEY");
  if (legacySignals) {
    ensureDefaultWorkspace();
  }
}

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [workspace, setWorkspace] = useState<Workspace | null>(() => {
    migrateLegacyBrowserSession();
    const active = getActiveWorkspace();
    return active ? toWorkspaceView(active) : null;
  });
  const [workspaces, setWorkspaces] = useState<Workspace[]>(() =>
    readStoredWorkspaces().map(toWorkspaceView),
  );
  const [suites, setSuites] = useState<SuiteListItem[]>([]);
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [isLoadingSuites, setIsLoadingSuites] = useState(false);
  const [engineHealth, setEngineHealth] = useState<EngineHealth | null>(null);
  const [engineApiKeyConfigured, setEngineApiKeyConfigured] = useState(() => hasEngineApiKey());
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (toast: Omit<ToastMessage, "id">) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { ...toast, id }]);
    setTimeout(() => {
      removeToast(id);
    }, 4500);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const syncWorkspacesFromStorage = useCallback(() => {
    migrateLegacyBrowserSession();
    setWorkspaces(readStoredWorkspaces().map(toWorkspaceView));
    const active = getActiveWorkspace();
    setWorkspace(active ? toWorkspaceView(active) : null);
    setEngineApiKeyConfigured(hasEngineApiKey());
  }, []);

  const refreshSuites = async () => {
    if (!getActiveWorkspace()) return;
    setIsLoadingSuites(true);
    try {
      const items = await listSuites();
      setSuites(items);
      if (activeAgentId && !items.some((s) => s.agent_id === activeAgentId)) {
        setActiveAgentId(null);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      console.warn("Failed to load suites", err);
      if (isEngineAuthErrorMessage(msg)) {
        addToast({
          type: "warning",
          title: "Engine API key required",
          message: "Open Workspace → Engine API key and paste the value from AGENTEVAL_API_KEY.",
        });
      }
    } finally {
      setIsLoadingSuites(false);
    }
  };

  const deleteAgentSuite = async (agentId: string): Promise<boolean> => {
    try {
      await deleteSuite(agentId);
      setSuites((prev) => prev.filter((s) => s.agent_id !== agentId));
      if (activeAgentId === agentId) {
        setActiveAgentId(null);
      }
      addToast({
        type: "success",
        title: "Agent Suite Deleted",
        message: `Agent suite '${agentId}' and associated runs have been permanently deleted.`,
      });
      await refreshSuites();
      return true;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      addToast({
        type: "error",
        title: "Failed to Delete Agent",
        message: msg,
      });
      return false;
    }
  };

  const refreshEngineConnection = useCallback(async () => {
    syncWorkspacesFromStorage();
    if (!getActiveWorkspace()) {
      setEngineHealth(null);
      setSuites([]);
      return;
    }
    setEngineApiKeyConfigured(hasEngineApiKey());
    try {
      const health = await fetchHealth();
      setEngineHealth(health);
    } catch {
      setEngineHealth(null);
    }
    await refreshSuites();
  }, [syncWorkspacesFromStorage]);

  const selectWorkspace = useCallback(
    (workspaceId: string) => {
      setActiveWorkspaceId(workspaceId);
      syncWorkspacesFromStorage();
      void refreshEngineConnection();
    },
    [refreshEngineConnection, syncWorkspacesFromStorage],
  );

  const createAndSelectWorkspace = useCallback(
    (name: string) => {
      const stored = createWorkspace({ name });
      syncWorkspacesFromStorage();
      void refreshEngineConnection();
      return toWorkspaceView(stored);
    },
    [refreshEngineConnection, syncWorkspacesFromStorage],
  );

  useEffect(() => {
    if (workspace) {
      void refreshEngineConnection();
    }
  }, [workspace?.id]);

  useEffect(() => {
    const onKeyChange = () => {
      void refreshEngineConnection();
    };
    window.addEventListener(ENGINE_API_KEY_CHANGED_EVENT, onKeyChange);
    window.addEventListener(WORKSPACE_CHANGED_EVENT, onKeyChange);
    return () => {
      window.removeEventListener(ENGINE_API_KEY_CHANGED_EVENT, onKeyChange);
      window.removeEventListener(WORKSPACE_CHANGED_EVENT, onKeyChange);
    };
  }, [refreshEngineConnection]);

  return (
    <WorkspaceContext.Provider
      value={{
        workspace,
        workspaces,
        selectWorkspace,
        createAndSelectWorkspace,
        syncWorkspacesFromStorage,
        suites,
        activeAgentId,
        setActiveAgentId,
        refreshSuites,
        deleteAgentSuite,
        isLoadingSuites,
        engineHealth,
        engineApiKeyConfigured,
        refreshEngineConnection,
        toasts,
        addToast,
        removeToast,
      }}
    >
      {children}
    </WorkspaceContext.Provider>
  );
};

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error("useWorkspace must be used within a WorkspaceProvider");
  }
  return ctx;
}
