import React from "react";
import { cn } from "@/lib/utils";

interface ConsoleStickyActionBarProps {
  children: React.ReactNode;
  className?: string;
  /** Accessible name for the action region */
  "aria-label"?: string;
}

/** Keeps wizard / console primary actions visible without scrolling to the page footer. */
export const ConsoleStickyActionBar: React.FC<ConsoleStickyActionBarProps> = ({
  children,
  className,
  "aria-label": ariaLabel = "Step actions",
}) => {
  return (
    <div
      className={cn(
        "fixed inset-x-0 bottom-0 z-30 border-t border-border bg-background/95 shadow-[0_-6px_28px_-12px_rgba(0,0,0,0.18)] backdrop-blur supports-backdrop-filter:bg-background/85",
        className,
      )}
      style={{ paddingBottom: "max(0.75rem, env(safe-area-inset-bottom))" }}
      aria-label={ariaLabel}
    >
      <div className="mx-auto flex max-w-7xl flex-col-reverse gap-3 px-4 pt-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        {children}
      </div>
    </div>
  );
};
