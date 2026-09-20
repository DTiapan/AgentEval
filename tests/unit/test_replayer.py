"""Unit tests for TraceReplayer: terminal scrubber, live streaming, and failure jumping."""

import io
import json
from pathlib import Path

import pytest
from rich.console import Console

from agenteval.core.models import (
    AgentLoopMetrics,
    ExecutionTrace,
    ReliabilityScorecard,
    StateDiff,
    StepRecord,
    ToolCall,
    ToolResult,
    Verdict,
)
from agenteval.replay.player import TraceReplayer


def test_replayer_load_trace_from_dict_and_object(tmp_path: Path) -> None:
    """Test loading trace from object, dict, and json file."""
    trace = ExecutionTrace(
        execution_id="exec-123",
        scenario_id="scen-001",
        agent_id="test-agent",
        verdict=Verdict.PASS,
    )

    # 1. From object
    loaded1 = TraceReplayer.load_trace(trace)
    assert loaded1.execution_id == "exec-123"

    # 2. From dict
    data = trace.model_dump()
    loaded2 = TraceReplayer.load_trace(data)
    assert loaded2.execution_id == "exec-123"

    # 3. From file
    trace_file = tmp_path / "trace.json"
    trace_file.write_text(json.dumps(data), encoding="utf-8")
    loaded3 = TraceReplayer.load_trace(trace_file)
    assert loaded3.execution_id == "exec-123"

    # 4. Non-existent file
    with pytest.raises(FileNotFoundError):
        TraceReplayer.load_trace(tmp_path / "non_existent.json")


def test_replayer_render_full_timeline(tmp_path: Path) -> None:
    """Test rendering complete timeline with steps, diffs, metrics, and scorecard."""
    output_buf = io.StringIO()
    console = Console(file=output_buf, color_system=None, width=120)
    replayer = TraceReplayer(console=console)

    trace = ExecutionTrace(
        execution_id="exec-full",
        scenario_id="scen-001",
        agent_id="test-agent",
        verdict=Verdict.PASS,
        steps=[
            StepRecord(
                step_number=1,
                thought="Reasoning turn 1",
                tool_calls=[
                    ToolCall(
                        call_id="c1",
                        tool_name="charge",
                        arguments={"amt": 50},
                        idempotency_key="k1",
                    )
                ],
                tool_results=[
                    ToolResult(
                        call_id="c1",
                        tool_name="charge",
                        output={"status": "OK"},
                        mutated_state=True,
                    )
                ],
                latency_ms=10.5,
            )
        ],
        state_diffs=[
            StateDiff(
                pre_snapshot_id="snap-pre",
                post_snapshot_id="snap-post",
                files_added=["orders/1.json"],
                files_modified=[],
                files_deleted=[],
                db_mutations=[],
            )
        ],
        loop_metrics=AgentLoopMetrics(
            agent_loop_iterations=1,
            time_to_completion_ms=15.0,
            duplicate_actions=0,
            termination_reason="COMPLETED",
        ),
        scorecard=ReliabilityScorecard(
            outcome_pass=True,
            trajectory_score=1.0,
            idempotency_score=1.0,
            duplicate_side_effects=0,
            verdict=Verdict.PASS,
        ),
    )

    replayer.render(trace)
    output = output_buf.getvalue()

    assert "AgentEval Execution Replay" in output
    assert "exec-full" in output
    assert "Reasoning turn 1" in output
    assert "charge" in output
    assert "snap-pre" in output
    assert "orders/1.json" in output
    assert "Final Assurance Verdict" in output


def test_replayer_jump_to_fail() -> None:
    """Test jump-to-fail isolates and highlights only the failing turn."""
    output_buf = io.StringIO()
    console = Console(file=output_buf, color_system=None, width=120)
    replayer = TraceReplayer(console=console)

    trace = ExecutionTrace(
        execution_id="exec-fail",
        scenario_id="scen-fail",
        agent_id="test-agent",
        verdict=Verdict.FAIL,
        steps=[
            StepRecord(
                step_number=1,
                thought="Successful turn",
                tool_calls=[ToolCall(call_id="c1", tool_name="ping", arguments={})],
                tool_results=[ToolResult(call_id="c1", tool_name="ping", output="pong")],
            ),
            StepRecord(
                step_number=2,
                thought="Failing turn",
                tool_calls=[ToolCall(call_id="c2", tool_name="explode", arguments={})],
                tool_results=[
                    ToolResult(
                        call_id="c2",
                        tool_name="explode",
                        is_error=True,
                        error_message="Boom!",
                    )
                ],
            ),
        ],
    )

    replayer.render(trace, jump_to_fail=True)
    output = output_buf.getvalue()

    assert "Jumping directly to first failure at Step 2" in output
    assert "Boom!" in output
    # Step 1 should be skipped when jump_to_fail is active
    assert "Successful turn" not in output


def test_replayer_render_step_live() -> None:
    """Test live step rendering."""
    output_buf = io.StringIO()
    console = Console(file=output_buf, color_system=None, width=120)
    replayer = TraceReplayer(console=console)

    step = StepRecord(
        step_number=1,
        thought="Live thought",
        tool_calls=[
            ToolCall(
                call_id="c1",
                tool_name="fetch",
                arguments={"url": "https://api.test"},
                idempotency_key="key-live",
            )
        ],
        tool_results=[
            ToolResult(
                call_id="c1",
                tool_name="fetch",
                output={"status": 200},
                mutated_state=True,
            )
        ],
        latency_ms=5.0,
    )

    replayer.render_step_live(step)
    output = output_buf.getvalue()

    assert "Step 1 (5.0ms)" in output
    assert "Live thought" in output
    assert "fetch" in output
    assert "key-live" in output
    assert "ΔS mutated" in output
