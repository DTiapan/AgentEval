"""Unit tests for CallableAdapter and AgentLoopEngine."""

from pathlib import Path

from agenteval.adapters.callable import CallableAdapter
from agenteval.adapters.tool import LocalToolAdapter
from agenteval.core.loop import AgentLoopEngine
from agenteval.core.models import StepRecord, ToolCall
from agenteval.faults.injector import FaultRule, ToolFaultInjector
from agenteval.sandbox.local import LocalSandbox


def test_agent_loop_engine_clean_completion(temp_sandbox_dir: Path) -> None:
    """Test a 2-step agent completing a task and mutating sandbox state."""
    def sample_agent(prompt: str, history: list[StepRecord]) -> tuple[str | None, list[ToolCall], bool]:
        if not history:
            # Step 1: Write file
            call = ToolCall(call_id="c1", tool_name="write_file", arguments={"filename": "result.txt", "content": "done"})
            return "Need to write file", [call], False
        # Step 2: Finished
        return "Task complete", [], True

    tool_adapter = LocalToolAdapter()
    def write_file(filename: str, content: str) -> str:
        (temp_sandbox_dir / filename).write_text(content)
        return "OK"
    tool_adapter.register("write_file", write_file)

    sandbox = LocalSandbox(root_dir=temp_sandbox_dir)
    adapter = CallableAdapter(agent_fn=sample_agent)
    engine = AgentLoopEngine(adapter=adapter, sandbox=sandbox, tool_adapter=tool_adapter, max_steps=5)

    trace = engine.run(scenario_id="scen-01", user_prompt="Generate report")

    assert len(trace.steps) == 2
    assert trace.loop_metrics.termination_reason == "COMPLETED"
    assert trace.loop_metrics.agent_loop_iterations == 2
    assert len(trace.state_diffs) == 1
    assert "result.txt" in trace.state_diffs[0].files_added


def test_agent_loop_engine_handles_injected_fault_and_retry(temp_sandbox_dir: Path) -> None:
    """Test agent retrying after an injected tool timeout."""
    def resilient_agent(prompt: str, history: list[StepRecord]) -> tuple[str | None, list[ToolCall], bool]:
        if not history:
            # Step 1: Call search (will fail with timeout)
            return "Searching", [ToolCall(call_id="c1", tool_name="search", arguments={"q": "apple"})], False

        last_result = history[-1].tool_results[0]
        if last_result.is_error and len(history) == 1:
            # Step 2: Retry with idempotency key
            return "Retrying search", [ToolCall(call_id="c2", tool_name="search", arguments={"q": "apple"}, idempotency_key="k1")], False

        # Step 3: Finished
        return "Done searching", [], True

    tool_adapter = LocalToolAdapter()
    tool_adapter.register("search", lambda q: f"Results for {q}")

    fault_rule = FaultRule(tool_name="search", trigger_occurrence=1, inject_timeout=True)
    injector = ToolFaultInjector(target_adapter=tool_adapter, rules=[fault_rule])

    sandbox = LocalSandbox(root_dir=temp_sandbox_dir)
    adapter = CallableAdapter(agent_fn=resilient_agent)
    engine = AgentLoopEngine(adapter=adapter, sandbox=sandbox, tool_adapter=injector, max_steps=5)

    trace = engine.run(scenario_id="scen-retry", user_prompt="Search apple")

    assert len(trace.steps) == 3
    # Step 1 tool failed
    assert trace.steps[0].tool_results[0].is_error
    # Step 2 tool succeeded
    assert not trace.steps[1].tool_results[0].is_error
    assert trace.loop_metrics.termination_reason == "COMPLETED"
