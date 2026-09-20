"""Unit tests for ScenarioLoader and VerdictEngine."""

from pathlib import Path

from agenteval.core.models import (
    AgentLoopMetrics,
    ExecutionTrace,
    StateDiff,
    StepRecord,
    ToolCall,
    ToolResult,
    Verdict,
)
from agenteval.engine.verdict import VerdictEngine
from agenteval.evaluators.state_diff import StateDiffAssertion
from agenteval.scenarios.loader import ScenarioLoader
from agenteval.scenarios.schema import TestScenario


def test_scenario_loader_from_yaml(temp_sandbox_dir: Path) -> None:
    """Test loading a scenario from a YAML file."""
    yaml_content = """
id: scen-test-01
name: Test File Creation
description: Tests that agent creates expected file
user_prompt: "Create test.txt with hello"
max_steps: 5
state_assertions:
  expected_files_created:
    - "test.txt"
fault_rules:
  - tool_name: "write_file"
    trigger_occurrence: 1
    inject_timeout: true
"""
    yaml_file = temp_sandbox_dir / "scenario.yaml"
    yaml_file.write_text(yaml_content)

    loader = ScenarioLoader()
    scenarios = loader.load(yaml_file)
    assert len(scenarios) == 1
    scen = scenarios[0]
    assert scen.id == "scen-test-01"
    assert scen.user_prompt == "Create test.txt with hello"
    assert scen.max_steps == 5
    assert scen.state_assertions is not None
    assert "test.txt" in scen.state_assertions.expected_files_created
    assert len(scen.fault_rules) == 1
    assert scen.fault_rules[0].inject_timeout


def test_verdict_engine_produces_pass() -> None:
    """Test VerdictEngine producing PASS when state diff matches."""
    scen = TestScenario(
        id="scen-1",
        name="Pass Scenario",
        user_prompt="Run",
        state_assertions=StateDiffAssertion(expected_files_created=["out.txt"]),
    )
    trace = ExecutionTrace(
        execution_id="e1",
        scenario_id="scen-1",
        agent_id="test-agent",
        steps=[
            StepRecord(
                step_number=1,
                tool_calls=[ToolCall(call_id="c1", tool_name="create", arguments={})],
                tool_results=[
                    ToolResult(call_id="c1", tool_name="create", is_error=False, mutated_state=True)
                ],
            )
        ],
        state_diffs=[
            StateDiff(pre_snapshot_id="s1", post_snapshot_id="s2", files_added=["out.txt"])
        ],
        loop_metrics=AgentLoopMetrics(termination_reason="COMPLETED"),
    )

    engine = VerdictEngine()
    scorecard = engine.evaluate(trace, scen)
    assert scorecard.verdict == Verdict.PASS
    assert scorecard.outcome_pass


def test_verdict_engine_produces_fail_on_missing_state() -> None:
    """Test VerdictEngine producing FAIL when expected file is missing."""
    scen = TestScenario(
        id="scen-2",
        name="Fail Scenario",
        user_prompt="Run",
        state_assertions=StateDiffAssertion(expected_files_created=["missing.txt"]),
    )
    trace = ExecutionTrace(
        execution_id="e2",
        scenario_id="scen-2",
        agent_id="test-agent",
        steps=[
            StepRecord(
                step_number=1,
                tool_calls=[ToolCall(call_id="c1", tool_name="create", arguments={})],
                tool_results=[ToolResult(call_id="c1", tool_name="create", is_error=False)],
            )
        ],
        state_diffs=[
            StateDiff(pre_snapshot_id="s1", post_snapshot_id="s2", files_added=["wrong.txt"])
        ],
        loop_metrics=AgentLoopMetrics(termination_reason="COMPLETED"),
    )

    engine = VerdictEngine()
    scorecard = engine.evaluate(trace, scen)
    assert scorecard.verdict == Verdict.FAIL
    assert not scorecard.outcome_pass


def test_verdict_engine_produces_unverifiable() -> None:
    """Test VerdictEngine producing UNVERIFIABLE when no state assertions exist and evidence cannot be sealed."""
    scen = TestScenario(
        id="scen-3",
        name="Unverifiable Scenario",
        user_prompt="Send external email",
        state_assertions=None,
    )
    trace = ExecutionTrace(
        execution_id="e3",
        scenario_id="scen-3",
        agent_id="test-agent",
        steps=[
            StepRecord(
                step_number=1,
                tool_calls=[ToolCall(call_id="c1", tool_name="send_email", arguments={})],
                tool_results=[ToolResult(call_id="c1", tool_name="send_email", is_error=False)],
            )
        ],
        state_diffs=[],
        loop_metrics=AgentLoopMetrics(termination_reason="COMPLETED"),
    )

    engine = VerdictEngine()
    scorecard = engine.evaluate(trace, scen)
    assert scorecard.verdict == Verdict.UNVERIFIABLE
