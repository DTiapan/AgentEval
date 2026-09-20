import { CandidateTest } from "../types";

/** Distinct short label for Studio test tabs (avoids duplicate truncated ids). */
export function formatTestTabLabel(test: CandidateTest, index: number): string {
  const ord = String(index + 1).padStart(2, "0");
  const persona = test.persona_id?.replace(/-/g, " ") || "persona";
  const category = test.category || "test";
  const mode =
    test.failure_mode && test.failure_mode !== "hypothesis"
      ? test.failure_mode.replace(/_/g, " ")
      : null;

  if (test.name && test.name.length <= 32 && !test.name.startsWith("core-agent")) {
    return `[${ord}] ${test.name}`;
  }

  const tail = mode ? `${category} · ${mode}` : category;
  return `[${ord}] ${persona} · ${tail}`;
}
