import React, { useEffect, useState } from "react";
import {
  ChevronDown,
  Moon,
  PlayCircle,
  Shield,
  Sliders,
  Sun,
} from "lucide-react";
import { useWorkspace } from "../context/WorkspaceContext";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PRODUCT_DOMAIN } from "@/lib/product";

interface HeaderProps {
  activeTab: "studio" | "assurance";
  setActiveTab: (tab: "studio" | "assurance") => void;
  onBrandClick?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onBrandClick,
}) => {
  const {
    workspace,
    workspaces,
    setWorkspace,
    suites,
    activeAgentId,
    setActiveAgentId,
    engineHealth,
  } = useWorkspace();

  const [isDark, setIsDark] = useState<boolean>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("agenteval_theme");
      if (saved) return saved === "dark";
      return document.documentElement.classList.contains("dark");
    }
    return false;
  });

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
      localStorage.setItem("agenteval_theme", "dark");
    } else {
      document.documentElement.classList.remove("dark");
      localStorage.setItem("agenteval_theme", "light");
    }
  }, [isDark]);

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-card/95 backdrop-blur-sm">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        {/* Left: Brand + Navigation */}
        <div className="flex items-center gap-6">
          <button
            type="button"
            onClick={onBrandClick}
            className="flex items-center gap-2.5 rounded-md text-left hover:opacity-90 transition-opacity cursor-pointer"
            title={onBrandClick ? `Back to ${PRODUCT_DOMAIN}` : undefined}
          >
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold shadow-xs">
              <Shield className="h-4 w-4 fill-current" />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tracking-tight text-foreground">
                Agent<span className="text-primary font-bold">Eval</span>
              </span>
              <Badge variant="outline" className="font-mono text-[10px] px-1.5 py-0 border-border bg-muted text-muted-foreground">
                {engineHealth?.version ? `v${engineHealth.version}` : "v0.3.0"}
              </Badge>
            </div>
          </button>

          <Separator orientation="vertical" className="h-4 bg-border" />

          <Tabs
            value={activeTab}
            onValueChange={(v) => setActiveTab(v as "studio" | "assurance")}
          >
            <TabsList className="h-auto p-0.5">
              <TabsTrigger value="studio" className="gap-2 px-3 py-1.5">
                <Sliders className="h-3.5 w-3.5" />
                Studio & Planner
              </TabsTrigger>
              <TabsTrigger value="assurance" className="gap-2 px-3 py-1.5">
                <PlayCircle className="h-3.5 w-3.5" />
                Assurance Runs
                {suites.length > 0 && (
                  <span className="ml-0.5 rounded-full bg-primary/10 text-primary px-1.5 text-[10px] font-semibold">
                    {suites.length}
                  </span>
                )}
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {/* Right: Agent Switcher + Workspace + Theme Toggle + Status */}
        <div className="flex items-center gap-3">
          {/* Agent Switcher */}
          {suites.length > 0 && (
            <div className="relative flex items-center">
              <span className="mr-2 text-xs text-muted-foreground">Agent:</span>
              <div className="relative">
                <select
                  value={activeAgentId || ""}
                  onChange={(e) => setActiveAgentId(e.target.value || null)}
                  className="appearance-none rounded-md border border-border bg-card py-1.5 pl-2.5 pr-7 font-mono text-xs font-medium text-foreground hover:border-border/80 focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
                >
                  {suites.map((s) => (
                    <option key={s.agent_id} value={s.agent_id}>
                      {s.agent_id} (v{s.suite_version})
                    </option>
                  ))}
                </select>
                <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
              </div>
            </div>
          )}

          {/* Workspace Pill */}
          <div className="relative">
            <select
              value={workspace.id}
              onChange={(e) => {
                const found = workspaces.find((w) => w.id === e.target.value);
                if (found) setWorkspace(found);
              }}
              className="appearance-none rounded-md border border-border bg-card py-1.5 pl-2.5 pr-7 text-xs font-medium text-foreground hover:border-border/80 focus:outline-none focus:ring-1 focus:ring-ring cursor-pointer"
            >
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
            <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
          </div>

          {/* Sun / Moon Theme Toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsDark(!isDark)}
            title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
            className="h-8 w-8 text-muted-foreground hover:text-foreground border border-border bg-card"
          >
            {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>

          {/* Live Engine Pulse */}
          <div className="flex items-center gap-1.5 rounded-md border border-border bg-card px-2.5 py-1 text-xs text-muted-foreground">
            <span
              className={`h-1.5 w-1.5 rounded-full ${
                engineHealth?.status === "ok" ? "bg-emerald-500" : "bg-amber-500"
              }`}
            />
            <span className="font-mono text-[11px]">
              {engineHealth?.status === "ok" ? "Engine 8766" : "Offline"}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
