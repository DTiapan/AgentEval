"""Unit tests for ToolFaultInjector and tool proxy."""

from agenteval.adapters.tool import LocalToolAdapter
from agenteval.core.models import FailureClass, ToolCall
from agenteval.faults.injector import FaultRule, ToolFaultInjector


def add_numbers(a: int, b: int) -> int:
    """Sample tool."""
    return a + b


def test_tool_adapter_clean_execution() -> None:
    """Test standard tool execution through adapter."""
    adapter = LocalToolAdapter()
    adapter.register("add", add_numbers)

    call = ToolCall(call_id="c1", tool_name="add", arguments={"a": 10, "b": 20})
    result = adapter.execute(call)

    assert not result.is_error
    assert result.output == 30
    assert result.tool_name == "add"


def test_fault_injector_timeout() -> None:
    """Test injecting a synthetic timeout on first call."""
    adapter = LocalToolAdapter()
    adapter.register("add", add_numbers)

    rule = FaultRule(
        tool_name="add",
        trigger_occurrence=1,
        inject_timeout=True,
        error_message="Connection timed out after 5000ms",
    )
    injector = ToolFaultInjector(target_adapter=adapter, rules=[rule])

    # 1st call triggers fault
    call1 = ToolCall(call_id="c1", tool_name="add", arguments={"a": 5, "b": 5})
    res1 = injector.execute(call1, step_number=1)
    assert res1.is_error
    assert "timed out" in (res1.error_message or "")
    assert injector.injected_fault_count == 1

    # 2nd call (retry) passes through cleanly
    call2 = ToolCall(call_id="c2", tool_name="add", arguments={"a": 5, "b": 5})
    res2 = injector.execute(call2, step_number=2)
    assert not res2.is_error
    assert res2.output == 10


def test_fault_injector_status_code_500() -> None:
    """Test injecting HTTP 500 server error."""
    adapter = LocalToolAdapter()
    adapter.register("add", add_numbers)

    rule = FaultRule(
        tool_name="add",
        fault_type=FailureClass.TOOL_FAILURE,
        inject_status_code=500,
        error_message="Internal Server Error (HTTP 500)",
    )
    injector = ToolFaultInjector(target_adapter=adapter, rules=[rule])

    call = ToolCall(call_id="c1", tool_name="add", arguments={"a": 1, "b": 2})
    res = injector.execute(call, step_number=1)

    assert res.is_error
    assert "HTTP 500" in (res.error_message or "")


def test_tool_adapter_catches_exception() -> None:
    """Test tool raising an unhandled exception."""

    def broken_tool() -> None:
        raise ValueError("Database connection lost")

    adapter = LocalToolAdapter()
    adapter.register("broken", broken_tool)

    call = ToolCall(call_id="c1", tool_name="broken", arguments={})
    res = adapter.execute(call)
    assert res.is_error
    assert "Database connection lost" in (res.error_message or "")


def test_fault_injector_step_matching() -> None:
    """Test injecting fault only on specific step."""
    adapter = LocalToolAdapter()
    adapter.register("add", add_numbers)

    rule = FaultRule(
        tool_name="add",
        trigger_step=3,
        inject_timeout=True,
    )
    injector = ToolFaultInjector(target_adapter=adapter, rules=[rule])

    # Call on step 1 -> does not trigger
    call1 = ToolCall(call_id="c1", tool_name="add", arguments={"a": 1, "b": 1})
    res1 = injector.execute(call1, step_number=1)
    assert not res1.is_error

    # Call on step 3 -> does trigger
    call2 = ToolCall(call_id="c2", tool_name="add", arguments={"a": 2, "b": 2})
    res2 = injector.execute(call2, step_number=3)
    assert res2.is_error
