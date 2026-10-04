import React, { useEffect, useMemo, useState } from "react";
import { ArrowRight, Check, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { PRODUCT_DOMAIN } from "@/lib/product";
import {
  createWorkspace,
  readStoredWorkspaces,
  setActiveWorkspaceId,
  slugifyWorkspaceName,
  type StoredWorkspace,
} from "@/lib/workspace-session";
import { navigateConsole, navigateMarketing } from "@/lib/site-route";

const TRUST_BULLETS = [
  "BYOA: HTTP targets, no agent code changes",
  "Frozen regression packs for CI gates",
  "Sealed evidence and HTML audit reports",
] as const;

interface WorkspaceEntryPageProps {
  onWorkspaceReady: () => void;
}

export const WorkspaceEntryPage: React.FC<WorkspaceEntryPageProps> = ({ onWorkspaceReady }) => {
  const [name, setName] = useState("");
  const [slugOverride, setSlugOverride] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [existing, setExisting] = useState<StoredWorkspace[]>(() => readStoredWorkspaces());

  useEffect(() => {
    setExisting(readStoredWorkspaces());
  }, []);

  const slugPreview = useMemo(() => {
    const base = slugOverride ?? slugifyWorkspaceName(name || "your-workspace");
    return base || "your-workspace";
  }, [name, slugOverride]);

  const openWorkspace = (workspaceId: string) => {
    setActiveWorkspaceId(workspaceId);
    onWorkspaceReady();
    navigateConsole("studio");
  };

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      createWorkspace({
        name,
        slug: slugOverride ?? undefined,
      });
      onWorkspaceReady();
      navigateConsole("studio");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not create workspace.");
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <header className="border-b border-border px-4 py-3 sm:px-6">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <button
            type="button"
            onClick={navigateMarketing}
            className="flex items-center gap-2 text-sm font-semibold cursor-pointer"
          >
            <Shield className="h-4 w-4 text-primary" aria-hidden />
            AgentEval
          </button>
          <Badge variant="outline" className="font-mono text-[10px]">{PRODUCT_DOMAIN}</Badge>
        </div>
      </header>

      <div className="flex flex-1 flex-col lg:flex-row">
        <aside className="border-b border-border bg-muted/30 px-6 py-10 lg:w-[38%] lg:border-b-0 lg:border-r lg:py-14">
          <div className="mx-auto max-w-sm">
            <h1 className="text-lg font-semibold tracking-tight text-foreground">
              Workspace on this browser
            </h1>
            <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
              No sign-in yet, like early Recall. Pick or create a workspace; data stays namespaced
              locally until Firebase and server tenancy ship.
            </p>
            <ul className="mt-6 space-y-3">
              {TRUST_BULLETS.map((line) => (
                <li key={line} className="flex items-start gap-2 text-xs text-muted-foreground">
                  <Check className="h-3.5 w-3.5 text-primary shrink-0 mt-0.5" aria-hidden />
                  {line}
                </li>
              ))}
            </ul>
          </div>
        </aside>

        <main className="flex flex-1 items-start justify-center px-4 py-10 sm:px-6 lg:py-14">
          <div className="w-full max-w-md space-y-8">
            <form onSubmit={handleCreate} className="rounded-lg border border-border bg-card p-5 shadow-xs space-y-4">
              <div>
                <h2 className="text-sm font-semibold text-foreground">Create your workspace</h2>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Used in the console header and for per-workspace engine API keys.
                </p>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="ws-name" className="text-xs font-medium text-foreground">
                  Workspace name
                </label>
                <Input
                  id="ws-name"
                  name="workspace_name"
                  value={name}
                  onChange={(e) => {
                    setName(e.target.value);
                    setSlugOverride(null);
                  }}
                  placeholder="Acme AI Core"
                  autoComplete="organization"
                  className="text-sm"
                  required
                  minLength={2}
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="ws-slug" className="text-xs font-medium text-foreground">
                  URL slug
                </label>
                <Input
                  id="ws-slug"
                  name="workspace_slug"
                  value={slugOverride ?? slugPreview}
                  onChange={(e) => setSlugOverride(slugifyWorkspaceName(e.target.value))}
                  className="font-mono text-xs"
                  spellCheck={false}
                />
                <p className="text-[10px] text-muted-foreground font-mono">
                  {PRODUCT_DOMAIN}/{slugPreview}
                </p>
              </div>

              {error && (
                <p className="text-xs text-destructive" role="alert">{error}</p>
              )}

              <Button type="submit" className="w-full gap-1.5" disabled={name.trim().length < 2}>
                Create workspace & continue
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </Button>
            </form>

            {existing.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Open existing
                </h3>
                <ul className="space-y-2">
                  {existing.map((ws) => (
                    <li key={ws.id}>
                      <button
                        type="button"
                        onClick={() => openWorkspace(ws.id)}
                        className="flex w-full items-center justify-between rounded-md border border-border bg-card px-3 py-2.5 text-left hover:bg-muted/40 transition-colors cursor-pointer"
                      >
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">{ws.name}</p>
                          <p className="text-[10px] font-mono text-muted-foreground">{ws.slug}</p>
                        </div>
                        <ArrowRight className="h-3.5 w-3.5 text-muted-foreground shrink-0" aria-hidden />
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};
