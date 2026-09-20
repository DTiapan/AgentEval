import { TestCaseResult } from "../types";

export type ReplaySession = {
  agentId: string;
  runId: string;
  test: TestCaseResult;
};

const STORAGE_KEY = "agenteval_replay_session";

export function saveReplaySession(session: ReplaySession): void {
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export function loadReplaySession(): ReplaySession | null {
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as ReplaySession;
  } catch {
    return null;
  }
}

export function openTrajectoryReplay(session: ReplaySession): void {
  saveReplaySession(session);
  window.location.hash = "#/console/replay";
}

export function navigateToAssurance(): void {
  window.location.hash = "#/console/assurance";
}
