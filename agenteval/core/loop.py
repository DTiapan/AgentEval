"""Agent loop engine: drives multi-turn reasoning and tool execution cycles."""

import time
import uuid

from agenteval.adapters.base import AgentAdapter
from agenteval.adapters.tool import ToolAdapter
from agenteval.core.models import (
    AgentLoopMetrics,
    ExecutionTrace,
    StepRecord,
    ToolResult,
    Verdict,
)
from agenteval.faults.injector import ToolFaultInjector
from agenteval.sandbox.base import Sandbox


class AgentLoopEngine:
    """Orchestrates the multi-turn agent execution loop, tool dispatch, and state tracking."""

    def __init__(
        self,
        adapter: AgentAdapter,
        sandbox: Sandbox | None = None,
        tool_adapter: ToolAdapter | ToolFaultInjector | None = None,
        max_steps: int = 15,
        agent_id: str = "agent-under-test",
    ) -> None:
        self.adapter = adapter
        self.sandbox = sandbox
        self.tool_adapter = tool_adapter
        self.max_steps = max_steps
        self.agent_id = agent_id

    def run(
        self,
        scenario_id: str,
        user_prompt: str,
        execution_id: str | None = None,
    ) -> ExecutionTrace:
        """Execute the agent loop until completion, error, or max steps exceeded."""
        exec_id = execution_id or f"exec-{uuid.uuid4().hex[:8]}"
        trace = ExecutionTrace(
            execution_id=exec_id,
            scenario_id=scenario_id,
            agent_id=self.agent_id,
            verdict=Verdict.UNVERIFIABLE,
        )

        # 1. Capture initial environment state snapshot
        pre_snap = None
        if self.sandbox:
            pre_snap = self.sandbox.snapshot(f"snap-{exec_id}-pre")
            trace.state_snapshots.append(pre_snap)

        steps: list[StepRecord] = []
        consecutive_duplicate_count = 0
        last_action_sig = ""
        termination_reason = "COMPLETED"
        start_time = time.perf_counter()

        # 2. Multi-turn loop
        for step_idx in range(1, self.max_steps + 1):
            step_start = time.perf_counter()
            thought, tool_calls, is_finished = self.adapter.step(user_prompt, steps)

            # Check consecutive duplicate tool calls
            current_action_sig = str([c.tool_name for c in tool_calls])
            if current_action_sig and current_action_sig == last_action_sig:
                consecutive_duplicate_count += 1
            last_action_sig = current_action_sig

            # Execute tool calls
            tool_results: list[ToolResult] = []
            for call in tool_calls:
                if isinstance(self.tool_adapter, ToolFaultInjector):
                    res = self.tool_adapter.execute(call, step_number=step_idx)
                elif isinstance(self.tool_adapter, ToolAdapter):
                    res = self.tool_adapter.execute(call)
                else:
                    res = ToolResult(
                        call_id=call.call_id,
                        tool_name=call.tool_name,
                        output=None,
                        is_error=False,
                    )
                tool_results.append(res)

            step_latency = (time.perf_counter() - step_start) * 1000
            step_rec = StepRecord(
                step_number=step_idx,
                thought=thought,
                tool_calls=tool_calls,
                tool_results=tool_results,
                latency_ms=round(step_latency, 2),
            )
            steps.append(step_rec)

            if is_finished or not tool_calls:
                termination_reason = "COMPLETED"
                break
        else:
            termination_reason = "MAX_STEPS"

        total_latency = (time.perf_counter() - start_time) * 1000

        # 3. Capture post environment state snapshot & compute Delta S
        if self.sandbox and pre_snap:
            post_snap = self.sandbox.snapshot(f"snap-{exec_id}-post")
            trace.state_snapshots.append(post_snap)
            diff = self.sandbox.diff(pre_snap, post_snap)
            trace.state_diffs.append(diff)

        trace.steps = steps
        trace.loop_metrics = AgentLoopMetrics(
            agent_loop_iterations=len(steps),
            duplicate_actions=consecutive_duplicate_count,
            termination_reason=termination_reason,
            time_to_completion_ms=round(total_latency, 2),
            tokens_consumed=sum(s.tokens_used for s in steps),
        )

        return trace
