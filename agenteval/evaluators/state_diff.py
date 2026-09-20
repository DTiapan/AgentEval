"""State diff evaluator: asserts expected vs actual environment mutations."""

from dataclasses import dataclass, field

from agenteval.core.models import StateDiff


@dataclass
class StateDiffAssertion:
    """Expected environmental side-effects required for passing evaluation."""

    expected_files_created: list[str] = field(default_factory=list)
    expected_files_modified: list[str] = field(default_factory=list)
    expected_files_deleted: list[str] = field(default_factory=list)
    expected_db_mutations: list[str] = field(default_factory=list)
    forbidden_files_modified: list[str] = field(default_factory=list)


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
        self, actual_diff: StateDiff, assertion: StateDiffAssertion
    ) -> StateDiffEvaluationResult:
        """Assert whether actual mutations satisfy expected criteria."""
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

        # Check DB mutations
        actual_mutated_tables = {m.get("table") for m in actual_diff.db_mutations if m.get("table")}
        missing_db_tables = [
            t for t in assertion.expected_db_mutations if t not in actual_mutated_tables
        ]

        # Check forbidden files
        unexpected_files = [
            f for f in actual_diff.files_modified if f in assertion.forbidden_files_modified
        ]

        passed = (
            len(missing_files) == 0 and len(missing_db_tables) == 0 and len(unexpected_files) == 0
        )

        details = (
            "All expected state mutations verified." if passed else "State diff assertions failed."
        )

        return StateDiffEvaluationResult(
            passed=passed,
            unverifiable=False,
            missing_files=missing_files,
            unexpected_files=unexpected_files,
            missing_db_tables=missing_db_tables,
            details=details,
        )
