export type ConsoleView = "studio" | "assurance" | "replay";

export function readConsoleView(): ConsoleView {
  const hash = window.location.hash.replace(/^#/, "");
  if (hash.includes("/replay")) return "replay";
  if (hash.includes("/assurance")) return "assurance";
  return "studio";
}

export function hashForConsoleView(view: ConsoleView): string {
  switch (view) {
    case "replay":
      return "#/console/replay";
    case "assurance":
      return "#/console/assurance";
    default:
      return "#/console";
  }
}

export function navigateConsoleView(view: ConsoleView): void {
  window.location.hash = hashForConsoleView(view);
}

export type AssuranceTab = "runs" | "signoff";

export function readAssuranceTab(): AssuranceTab {
  const hash = window.location.hash.replace(/^#/, "");
  if (hash.includes("/assurance/signoff")) return "signoff";
  return "runs";
}

export function navigateAssuranceTab(tab: AssuranceTab): void {
  window.location.hash =
    tab === "signoff" ? "#/console/assurance/signoff" : "#/console/assurance";
}
