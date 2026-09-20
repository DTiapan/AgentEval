import React, { createContext, useContext, useEffect, useState } from "react";
import { EngineHealth, fetchHealth, listSuites } from "../api";
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
  isLoadingSuites: boolean;
  engineHealth: EngineHealth | null;
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  removeToast: (id: string) => void;
}

const DEFAULT_WORKSPACES: Workspace[] = [
  {
    id: "ws-local",
    name: "Local Development",
    slug: "local-dev",
    role: "OWNER",
    isEnterpriseCloud: false,
  },
  {
    id: "ws-acme",
    name: "Acme AI Core",
    slug: "acme-ai-core",
    role: "ADMIN",
    isEnterpriseCloud: true,
  },
  {
    id: "ws-prod-org",
    name: "Enterprise Assurance Org",
    slug: "enterprise-cloud",
    role: "ADMIN",
    isEnterpriseCloud: true,
  },
];

const WorkspaceContext = createContext<WorkspaceContextValue | undefined>(undefined);

export const WorkspaceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [workspace, setWorkspace] = useState<Workspace>(DEFAULT_WORKSPACES[0]);
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
      if (items.length > 0 && !activeAgentId) {
        setActiveAgentId(items[0].agent_id);
      }
    } catch (err: unknown) {
      console.warn("Failed to load suites", err);
    } finally {
      setIsLoadingSuites(false);
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
        workspaces: DEFAULT_WORKSPACES,
        setWorkspace,
        suites,
        activeAgentId,
        setActiveAgentId,
        refreshSuites,
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
