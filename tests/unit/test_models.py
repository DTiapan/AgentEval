"""Unit tests for AgentEval core domain models."""

from agenteval.core.models import (
    AgentLoopMetrics,
    ExecutionTrace,
    FailureClass,
    ReliabilityScorecard,
    StateDiff,
    StateSnapshot,
    StepRecord,
    ToolCall,
    ToolResult,
    Verdict,
)


def test_verdict_values() -> None:
    """Ensure all core verdict values exist."""
    assert Verdict.PASS == "PASS"
    assert Verdict.FAIL == "FAIL"
    assert Verdict.UNVERIFIABLE == "UNVERIFIABLE"
    assert Verdict.ANOMALOUS == "ANOMALOUS"


def test_failure_class_values() -> None:
    """Ensure standard failure classes are represented."""
    assert FailureClass.TOOL_FAILURE == "TOOL_FAILURE"
    assert FailureClass.IDEMPOTENCY_FAILURE == "IDEMPOTENCY_FAILURE"
    assert FailureClass.CHECKPOINT_FAILURE == "CHECKPOINT_FAILURE"


def test_tool_call_and_result_creation() -> None:
    """Test ToolCall and ToolResult models."""
    call = ToolCall(
        call_id="call-1",
        tool_name="transfer_funds",
        arguments={"account": "acc-123", "amount": 100},
        idempotency_key="idemp-xyz",
    )
    assert call.tool_name == "transfer_funds"
    assert call.arguments["amount"] == 100
    assert call.idempotency_key == "idemp-xyz"

    result = ToolResult(
        call_id="call-1",
        tool_name="transfer_funds",
        output={"status": "success", "tx_id": "tx-999"},
        is_error=False,
        latency_ms=12.5,
        mutated_state=True,
    )
    assert not result.is_error
    assert result.mutated_state
    assert result.latency_ms == 12.5


def test_step_record() -> None:
    """Test StepRecord aggregation."""
    call = ToolCall(call_id="c-1", tool_name="query_db", arguments={"query": "SELECT 1"})
    res = ToolResult(call_id="c-1", tool_name="query_db", output=[(1,)])

    step = StepRecord(
        step_number=1,
        thought="Querying database to check connection",
        tool_calls=[call],
        tool_results=[res],
        tokens_used=150,
        latency_ms=85.0,
    )
    assert step.step_number == 1
    assert len(step.tool_calls) == 1
    assert len(step.tool_results) == 1
    assert step.tokens_used == 150


def test_state_snapshot_and_diff() -> None:
    """Test environment state snapshot and diff models."""
    snap1 = StateSnapshot(
        snapshot_id="snap-1",
        timestamp_ns=1000,
        file_hashes={"file.txt": "hash1"},
    )
    snap2 = StateSnapshot(
        snapshot_id="snap-2",
        timestamp_ns=2000,
        file_hashes={"file.txt": "hash2", "new.txt": "hash3"},
    )
    diff = StateDiff(
        pre_snapshot_id=snap1.snapshot_id,
        post_snapshot_id=snap2.snapshot_id,
        files_added=["new.txt"],
        files_modified=["file.txt"],
    )
    assert diff.pre_snapshot_id == "snap-1"
    assert "new.txt" in diff.files_added
    assert "file.txt" in diff.files_modified


def test_execution_trace_and_scorecard() -> None:
    """Test complete ExecutionTrace lifecycle model."""
    trace = ExecutionTrace(
        execution_id="exec-001",
        scenario_id="scen-transfer-01",
        agent_id="bank-agent-v1",
    )
    assert trace.execution_id == "exec-001"
    assert trace.verdict == Verdict.UNVERIFIABLE
    assert len(trace.steps) == 0

    metrics = AgentLoopMetrics(
        agent_loop_iterations=3,
        duplicate_actions=0,
        termination_reason="GOAL_ACCOMPLISHED",
        time_to_completion_ms=350.0,
        tokens_consumed=450,
    )
    scorecard = ReliabilityScorecard(
        outcome_pass=True,
        trajectory_score=1.0,
        recovery_score=1.0,
        idempotency_score=1.0,
        duplicate_side_effects=0,
        verdict=Verdict.PASS,
        metrics=metrics,
    )
    assert scorecard.outcome_pass
    assert scorecard.verdict == Verdict.PASS
    assert scorecard.duplicate_side_effects == 0
