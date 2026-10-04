import React from "react";
import { ArrowRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useWorkspace } from "@/context/WorkspaceContext";
import { navigateWorkspaceEntry } from "@/lib/site-route";

interface WorkspaceSwitcherDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export const WorkspaceSwitcherDialog: React.FC<WorkspaceSwitcherDialogProps> = ({
  open,
  onOpenChange,
}) => {
  const { workspace, workspaces, selectWorkspace } = useWorkspace();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Workspaces</DialogTitle>
          <DialogDescription className="text-xs">
            Browser-local workspaces until accounts ship. Engine data is still shared on one API
            deployment. Server isolation comes with E-ORG on the backend.
          </DialogDescription>
        </DialogHeader>

        <ul className="space-y-2 max-h-[240px] overflow-y-auto">
          {workspaces.map((ws) => {
            const active = workspace?.id === ws.id;
            return (
              <li key={ws.id}>
                <button
                  type="button"
                  disabled={active}
                  onClick={() => {
                    selectWorkspace(ws.id);
                    onOpenChange(false);
                  }}
                  className="flex w-full items-center justify-between rounded-md border border-border px-3 py-2 text-left hover:bg-muted/40 disabled:opacity-80 disabled:bg-muted/20 cursor-pointer disabled:cursor-default"
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate">{ws.name}</p>
                    <p className="text-[10px] font-mono text-muted-foreground">{ws.slug}</p>
                  </div>
                  {active ? (
                    <span className="text-[10px] font-medium text-primary">Active</span>
                  ) : (
                    <ArrowRight className="h-3.5 w-3.5 text-muted-foreground" aria-hidden />
                  )}
                </button>
              </li>
            );
          })}
        </ul>

        <Button
          type="button"
          variant="outline"
          size="sm"
          className="w-full gap-1.5 text-xs"
          onClick={() => {
            onOpenChange(false);
            navigateWorkspaceEntry();
          }}
        >
          <Plus className="h-3.5 w-3.5" aria-hidden />
          Create or manage workspaces
        </Button>
      </DialogContent>
    </Dialog>
  );
};
