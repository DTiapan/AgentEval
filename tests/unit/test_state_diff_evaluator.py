"""Unit tests for StateDiffEvaluator: multi-table DB mutations, file diffs, and UNVERIFIABLE handling."""

from agenteval.core.models import StateDiff
from agenteval.evaluators.state_diff import (
    StateDiffAssertion,
    StateDiffEvaluator,
)


def test_state_diff_evaluator_unverifiable_on_none_diff() -> None:
    evaluator = StateDiffEvaluator()
    assertion = StateDiffAssertion(expected_files_created=["out.txt"])
    result = evaluator.evaluate(None, assertion)

    assert not result.passed
    assert result.unverifiable
    assert "UNVERIFIABLE" in result.details


def test_state_diff_evaluator_unverifiable_on_unsealed_snapshot() -> None:
    evaluator = StateDiffEvaluator()
    diff = StateDiff(
        pre_snapshot_id="UNVERIFIABLE",
        post_snapshot_id="snap-2",
        files_added=["out.txt"],
        files_modified=[],
        files_deleted=[],
        db_mutations=[],
    )
    assertion = StateDiffAssertion(expected_files_created=["out.txt"])
    result = evaluator.evaluate(diff, assertion)

    assert not result.passed
    assert result.unverifiable
    assert "UNVERIFIABLE" in result.details


def test_state_diff_evaluator_passes_matching_file_and_multi_table_mutations() -> None:
    evaluator = StateDiffEvaluator()
    diff = StateDiff(
        pre_snapshot_id="snap-1",
        post_snapshot_id="snap-2",
        files_added=["receipt.pdf", "audit.log"],
        files_modified=["state.json"],
        files_deleted=["temp.lock"],
        db_mutations=[
            {"table": "refund_requests", "action": "INSERT", "id": "ref-101"},
            {"table": "audit_events", "action": "INSERT", "id": "evt-202"},
        ],
    )
    assertion = StateDiffAssertion(
        expected_files_created=["receipt.pdf", "audit.log"],
        expected_files_modified=["state.json"],
        expected_files_deleted=["temp.lock"],
        expected_db_mutations=["refund_requests", "audit_events"],
        forbidden_files_modified=[".env", "credentials.json"],
        required_db_records=[{"table": "refund_requests"}],
    )
    result = evaluator.evaluate(diff, assertion)

    assert result.passed
    assert not result.unverifiable
    assert len(result.missing_files) == 0
    assert len(result.missing_db_tables) == 0
    assert len(result.unexpected_files) == 0


def test_state_diff_evaluator_fails_on_missing_db_table_or_file() -> None:
    evaluator = StateDiffEvaluator()
    diff = StateDiff(
        pre_snapshot_id="snap-1",
        post_snapshot_id="snap-2",
        files_added=["receipt.pdf"],
        files_modified=[],
        files_deleted=[],
        db_mutations=[{"table": "refund_requests", "action": "INSERT"}],
    )
    assertion = StateDiffAssertion(
        expected_files_created=["receipt.pdf", "audit.log"],
        expected_db_mutations=["refund_requests", "ledger_entries"],
    )
    result = evaluator.evaluate(diff, assertion)

    assert not result.passed
    assert not result.unverifiable
    assert "audit.log" in result.missing_files
    assert "ledger_entries" in result.missing_db_tables


def test_state_diff_evaluator_fails_on_forbidden_file_modified() -> None:
    evaluator = StateDiffEvaluator()
    diff = StateDiff(
        pre_snapshot_id="snap-1",
        post_snapshot_id="snap-2",
        files_added=[],
        files_modified=[".env", "app.py"],
        files_deleted=[],
        db_mutations=[],
    )
    assertion = StateDiffAssertion(
        forbidden_files_modified=[".env"],
    )
    result = evaluator.evaluate(diff, assertion)

    assert not result.passed
    assert ".env" in result.unexpected_files
