import { ExecutionStep, TestCaseResult } from "../types";

export type TrajectoryReplayModel = {
  steps: ExecutionStep[];
  failStepIndex: number | null;
  testId: string;
  verdict: string;
};

export function trajectoryFromResult(result: TestCaseResult): TrajectoryReplayModel {
  const steps = result.trajectory ?? [];
  const failIdx = steps.findIndex((s) => s.is_failure);
  return {
    steps,
    failStepIndex: failIdx >= 0 ? failIdx : null,
    testId: result.test_id,
    verdict: result.verdict,
  };
}

export type StepPanelContent = {
  thought: string;
  action: string;
  observation: string;
  emphasis?: "observation" | "thought" | "action";
};

export function panelContentForStep(step: ExecutionStep): StepPanelContent {
  const actionPayload =
    step.action_tool
      ? `${step.action_tool}\n${JSON.stringify(step.action_args ?? {}, null, 2)}`
      : step.kind === "tool_call"
        ? "(no tool payload in sealed trace)"
        : "—";

  const telemetry =
    step.http_status != null
      ? `HTTP ${step.http_status}${step.latency_ms != null ? ` · ${step.latency_ms} ms` : ""}`
      : "";

  switch (step.kind) {
    case "user_message":
      return {
        thought: "Sealed user prompt from test definition and run request.",
        action: "—",
        observation: step.observation || "—",
        emphasis: "observation",
      };
    case "agent_thought":
      return {
        thought: step.thought || "—",
        action: "—",
        observation: telemetry || "—",
        emphasis: "thought",
      };
    case "tool_call":
      return {
        thought: step.thought || "Tool invocation from agent response payload.",
        action: actionPayload,
        observation: step.observation || telemetry || "—",
        emphasis: "action",
      };
    case "http_response":
      return {
        thought: "Observable HTTP response body captured by the runner.",
        action: "—",
        observation: step.observation || "—",
        emphasis: "observation",
      };
    case "invariant_check":
      return {
        thought: step.thought || "—",
        action: "invariant_evaluator",
        observation: step.observation || telemetry || "—",
        emphasis: "thought",
      };
    default:
      return {
        thought: step.thought || "—",
        action: step.action_tool ? actionPayload : "—",
        observation: step.observation || telemetry || "—",
      };
  }
}
