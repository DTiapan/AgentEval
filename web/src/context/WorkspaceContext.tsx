import React, { createContext, useContext, useEffect, useState } from "react";
import { EngineHealth, deleteSuite, fetchHealth, listSuites } from "../api";
import { SuiteListItem, Workspace } from "../types";

export type ToastMessage = {
  id: string;
  type: "info" | "success" | "warning" | "error";
  title: string;
  message?: string;
};

interface WorkspaceContextValue {
  workspace: Workspace;
  workspaces: Workspace[];
  setWorkspace: (ws: Workspace) => void;
  suites: SuiteListItem[];
  activeAgentId: string | null;
  setActiveAgentId: (id: string | null) => void;
  refreshSuites: () => Promise<void>;
  deleteAgentSuite: (agentId: string) => Promise<boolean>;
  isLoadingSuites: boolean;
  engineHealth: EngineHealth | null;
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  removeToast: (id: string) => void;
}

/** MVP: one local workspace; suite list comes from GET /v1/suites only. */
export const LOCAL_WORKSPACE: Workspace = {
  id: "ws-local",
  name: "Local workspace",
  slug: "local",
  role: "OWNER",
  isEnterpriseCloud: false,
};

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [workspace] = useState<Workspace>(LOCAL_WORKSPACE);
  const [suites, setSuites] = useState<SuiteListItem[]>([]);
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [isLoadingSuites, setIsLoadingSuites] = useState(false);
  const [engineHealth, setEngineHealth] = useState<EngineHealth | null>(null);
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

  const refreshSuites = async () => {
    setIsLoadingSuites(true);
    try {
      const items = await listSuites();
      setSuites(items);
      if (activeAgentId && !items.some((s) => s.agent_id === activeAgentId)) {
        setActiveAgentId(null);
      }
    } catch (err: unknown) {
      console.warn("Failed to load suites", err);
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

  useEffect(() => {
    fetchHealth()
      .then((health) => setEngineHealth(health))
      .catch(() => setEngineHealth(null));
    refreshSuites();
  }, []);

  return (
    <WorkspaceContext.Provider
      value={{
        workspace,
        workspaces: [LOCAL_WORKSPACE],
        setWorkspace: () => {
          /* MVP: single workspace until /v1/workspaces exists */
        },
        suites,
        activeAgentId,
        setActiveAgentId,
        refreshSuites,
        deleteAgentSuite,
        isLoadingSuites,
        engineHealth,
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
