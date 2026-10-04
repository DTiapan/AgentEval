import React, { useEffect, useState } from "react";
import { KeyRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useWorkspace } from "@/context/WorkspaceContext";
import { readEngineApiKey, writeEngineApiKey } from "@/lib/engine-api-key";

interface EngineApiKeyDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved?: () => void;
}

export const EngineApiKeyDialog: React.FC<EngineApiKeyDialogProps> = ({
  open,
  onOpenChange,
  onSaved,
}) => {
  const { workspace } = useWorkspace();
  const [draft, setDraft] = useState("");
  const [showValue, setShowValue] = useState(false);

  useEffect(() => {
    if (open) {
      setDraft(readEngineApiKey() ?? "");
      setShowValue(false);
    }
  }, [open]);

  const handleSave = () => {
    writeEngineApiKey(draft);
    onSaved?.();
    onOpenChange(false);
  };

  const handleClear = () => {
    setDraft("");
    writeEngineApiKey(null);
    onSaved?.();
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-primary shrink-0" aria-hidden />
            <DialogTitle>Engine API key</DialogTitle>
          </div>
          <DialogDescription className="text-xs leading-relaxed">
            {workspace ? (
              <>
                Scoped to workspace <span className="font-medium text-foreground">{workspace.name}</span>.
              </>
            ) : null}{" "}
            When the server sets <code className="font-mono text-[11px]">AGENTEVAL_API_KEY</code>, paste
            the same value here. Stored in this browser only; sent as{" "}
            <code className="font-mono text-[11px]">X-API-Key</code> on API calls.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2 py-1">
          <label htmlFor="engine-api-key-input" className="text-xs font-medium text-foreground">
            API key
          </label>
          <div className="flex gap-2">
            <Input
              id="engine-api-key-input"
              name="engine_api_key"
              type={showValue ? "text" : "password"}
              autoComplete="off"
              spellCheck={false}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Paste key from Secret Manager / deploy"
              className="font-mono text-xs"
            />
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="shrink-0 text-xs"
              onClick={() => setShowValue((v) => !v)}
            >
              {showValue ? "Hide" : "Show"}
            </Button>
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0 flex-col-reverse sm:flex-row sm:justify-between">
          <Button type="button" variant="ghost" size="sm" className="text-xs" onClick={handleClear}>
            Clear saved key
          </Button>
          <div className="flex gap-2 justify-end">
            <Button type="button" variant="outline" size="sm" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="button" size="sm" onClick={handleSave}>
              Save
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
