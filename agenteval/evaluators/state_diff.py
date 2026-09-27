"""State diff evaluator: asserts expected vs actual environment mutations."""

from dataclasses import dataclass, field
from typing import Any

from agenteval.core.models import StateDiff


@dataclass
class StateDiffAssertion:
    """Expected environmental side-effects required for passing evaluation."""

    expected_files_created: list[str] = field(default_factory=list)
    expected_files_modified: list[str] = field(default_factory=list)
    expected_files_deleted: list[str] = field(default_factory=list)
    expected_db_mutations: list[str] = field(default_factory=list)
    forbidden_files_modified: list[str] = field(default_factory=list)
    required_db_records: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class StateDiffEvaluationResult:
    """Outcome of evaluating environment mutations."""

    passed: bool
    unverifiable: bool
    missing_files: list[str] = field(default_factory=list)
    unexpected_files: list[str] = field(default_factory=list)
    missing_db_tables: list[str] = field(default_factory=list)
    details: str = ""


class StateDiffEvaluator:
    """Evaluates actual StateDiff (Delta S) against StateDiffAssertion."""

    def evaluate(
        self, actual_diff: StateDiff | None, assertion: StateDiffAssertion
    ) -> StateDiffEvaluationResult:
        """Assert whether actual mutations satisfy expected criteria (deterministic vs self-report)."""
        if actual_diff is None:
            return StateDiffEvaluationResult(
                passed=False,
                unverifiable=True,
                details="State diff evidence was not captured or is inaccessible (UNVERIFIABLE).",
            )

        if (
            actual_diff.pre_snapshot_id == "UNVERIFIABLE"
            or actual_diff.post_snapshot_id == "UNVERIFIABLE"
        ):
            return StateDiffEvaluationResult(
                passed=False,
                unverifiable=True,
                details="Environment state snapshots are unsealed or UNVERIFIABLE.",
            )

        missing_files: list[str] = []
        for expected_file in assertion.expected_files_created:
            if expected_file not in actual_diff.files_added:
                missing_files.append(expected_file)

        for expected_mod in assertion.expected_files_modified:
            if expected_mod not in actual_diff.files_modified:
                missing_files.append(expected_mod)

        for expected_del in assertion.expected_files_deleted:
            if expected_del not in actual_diff.files_deleted:
                missing_files.append(expected_del)

        # Check DB mutations across multiple tables
        actual_mutated_tables = {m.get("table") for m in actual_diff.db_mutations if m.get("table")}
        missing_db_tables = [
            t for t in assertion.expected_db_mutations if t not in actual_mutated_tables
        ]

        # Check column-level record requirements if specified
        for req in assertion.required_db_records:
            req_table = req.get("table")
            if req_table and req_table not in actual_mutated_tables:
                if req_table not in missing_db_tables:
                    missing_db_tables.append(req_table)

        # Check forbidden files
        unexpected_files = [
            f for f in actual_diff.files_modified if f in assertion.forbidden_files_modified
        ]

        passed = (
            len(missing_files) == 0 and len(missing_db_tables) == 0 and len(unexpected_files) == 0
        )

        details = (
            "All expected environmental state mutations verified."
            if passed
            else "State diff assertions failed to confirm required side-effects."
        )

        return StateDiffEvaluationResult(
            passed=passed,
            unverifiable=False,
            missing_files=missing_files,
            unexpected_files=unexpected_files,
            missing_db_tables=missing_db_tables,
            details=details,
        )
