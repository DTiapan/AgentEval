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
