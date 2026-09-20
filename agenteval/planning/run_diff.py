"""Per-test verdict diff between suite runs (v0.2 regression)."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from agenteval.planning.models import SuiteRunReport


class VerdictChangeKind(StrEnum):
    STABLE = "STABLE"
    REGRESSED = "REGRESSED"
    FIXED = "FIXED"
    CHANGED = "CHANGED"
    NEW = "NEW"
    REMOVED = "REMOVED"


class VerdictChange(BaseModel):
    """One test's verdict movement vs a baseline run."""

    model_config = ConfigDict(extra="forbid")

    test_id: str
    previous_verdict: str | None = None
    current_verdict: str
    kind: VerdictChangeKind


class SuiteRunDiff(BaseModel):
    """Diff of current run against a prior run on the same suite version."""

    model_config = ConfigDict(extra="forbid")

    baseline_run_id: str
    baseline_suite_version: int
    current_run_id: str
    changes: list[VerdictChange] = Field(default_factory=list)

    @property
    def regressions(self) -> list[VerdictChange]:
        return [c for c in self.changes if c.kind == VerdictChangeKind.REGRESSED]

    @property
    def fixes(self) -> list[VerdictChange]:
        return [c for c in self.changes if c.kind == VerdictChangeKind.FIXED]

    @property
    def material_changes(self) -> list[VerdictChange]:
        return [c for c in self.changes if c.kind != VerdictChangeKind.STABLE]


def _classify_change(previous: str | None, current: str) -> VerdictChangeKind:
    if previous is None:
        return VerdictChangeKind.NEW
    if previous == current:
        return VerdictChangeKind.STABLE
    if previous == "PASS" and current in ("FAIL", "UNVERIFIABLE"):
        return VerdictChangeKind.REGRESSED
    if previous in ("FAIL", "UNVERIFIABLE") and current == "PASS":
        return VerdictChangeKind.FIXED
    return VerdictChangeKind.CHANGED


def diff_suite_runs(baseline: SuiteRunReport, current: SuiteRunReport) -> SuiteRunDiff | None:
    """Compare verdicts per test_id. Returns None if suite versions differ."""
    if baseline.suite_version != current.suite_version:
        return None

    prev_map = {r.test_id: r.verdict for r in baseline.results}
    curr_map = {r.test_id: r.verdict for r in current.results}
    all_ids = sorted(set(prev_map) | set(curr_map))

    changes: list[VerdictChange] = []
    for test_id in all_ids:
        previous = prev_map.get(test_id)
        current_verdict = curr_map.get(test_id)
        if current_verdict is None:
            changes.append(
                VerdictChange(
                    test_id=test_id,
                    previous_verdict=previous,
                    current_verdict="",
                    kind=VerdictChangeKind.REMOVED,
                )
            )
            continue
        kind = _classify_change(previous, current_verdict)
        changes.append(
            VerdictChange(
                test_id=test_id,
                previous_verdict=previous,
                current_verdict=current_verdict,
                kind=kind,
            )
        )

    return SuiteRunDiff(
        baseline_run_id=baseline.run_id,
        baseline_suite_version=baseline.suite_version,
        current_run_id=current.run_id,
        changes=changes,
    )
