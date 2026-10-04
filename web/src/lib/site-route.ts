import { hasActiveWorkspace } from "@/lib/workspace-session";
import { hashForConsoleView, type ConsoleView } from "@/lib/console-route";

export type SiteRoute = "marketing" | "workspace" | "console";

export function readSiteRoute(): SiteRoute {
  const hash = window.location.hash.replace(/^#/, "");
  if (hash === "/workspace" || hash.startsWith("/workspace/")) {
    return "workspace";
  }
  if (hash === "/console" || hash.startsWith("/console/")) {
    return hasActiveWorkspace() ? "console" : "workspace";
  }
  return "marketing";
}

export function navigateMarketing(): void {
  window.location.hash = "#/";
}

export function navigateWorkspaceEntry(): void {
  window.location.hash = "#/workspace";
}

export function navigateConsole(view: ConsoleView = "studio"): void {
  window.location.hash = hashForConsoleView(view);
}

/** “Open console” from marketing — skip workspace picker when one is already active. */
export function enterProductFromMarketing(): void {
  if (hasActiveWorkspace()) {
    navigateConsole("studio");
  } else {
    navigateWorkspaceEntry();
  }
}

/** “Start free” — always show workspace create/open (Recall-style entry). */
export function startFreeFromMarketing(): void {
  navigateWorkspaceEntry();
}
