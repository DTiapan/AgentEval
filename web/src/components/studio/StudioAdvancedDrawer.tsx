import React from "react";
import { ChevronDown, ChevronRight, SlidersHorizontal } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { STUDIO_ADVANCED_UX } from "@/lib/studio-ux-config";
import { cn } from "@/lib/utils";

interface StudioAdvancedDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  activeCount?: number;
  children: React.ReactNode;
  className?: string;
}

export const StudioAdvancedDrawer: React.FC<StudioAdvancedDrawerProps> = ({
  open,
  onOpenChange,
  activeCount = 0,
  children,
  className,
}) => {
  return (
    <div
      className={cn(
        "rounded-lg border border-border/80 bg-card/60 overflow-hidden shadow-xs transition-[border-color,box-shadow]",
        className,
      )}
    >
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        aria-expanded={open}
        className="w-full flex items-center justify-between px-3 py-2 bg-muted/20 hover:bg-muted/40 text-left transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2 min-w-0">
          <SlidersHorizontal className="h-3.5 w-3.5 text-primary shrink-0" aria-hidden />
          <span className="text-xs font-medium text-foreground">{STUDIO_ADVANCED_UX.title}</span>
          <span className="text-[10px] text-muted-foreground hidden sm:inline">
            {STUDIO_ADVANCED_UX.description}
          </span>
          {activeCount > 0 && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-mono">
              {activeCount} active
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1.5 text-muted-foreground shrink-0 ml-2">
          <span className="text-[11px] hidden sm:inline">{open ? "Hide" : "Show"}</span>
          {open ? (
            <ChevronDown className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          )}
        </div>
      </button>
      {open && (
        <div className="p-3.5 space-y-4 border-t border-border/70 bg-muted/5">{children}</div>
      )}
    </div>
  );
};
