"""Interactive and terminal scrubber replayer for agent execution traces."""

import json
from pathlib import Path
from typing import Any

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from agenteval.core.models import ExecutionTrace, StepRecord, Verdict


class TraceReplayer:
    """Provides terminal-based interactive and formatted playback of execution traces."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    @classmethod
    def load_trace(cls, source: str | Path | dict[str, Any] | ExecutionTrace) -> ExecutionTrace:
        """Load an ExecutionTrace from a JSON file, dict, or existing instance."""
        if isinstance(source, ExecutionTrace):
            return source
        if isinstance(source, dict):
            return ExecutionTrace.model_validate(source)
        path = Path(source)
        if not path.exists():
            raise FileNotFoundError(f"Trace file not found: {path}")
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return ExecutionTrace.model_validate(data)

    def render_step_live(self, step: StepRecord) -> None:
        """Render an individual step immediately during a live run."""
        table = Table(
            title=f"⚡ Step {step.step_number} ({step.latency_ms:.1f}ms)",
            box=None,
            show_header=True,
            header_style="bold blue",
        )
        table.add_column("Type", style="dim", width=12)
        table.add_column("Details")

        if step.thought:
            table.add_row("Thought", f"[italic cyan]{step.thought}[/italic cyan]")

        for tc in step.tool_calls:
            call_info = f"[bold yellow]{tc.tool_name}[/bold yellow]({json.dumps(tc.arguments)})"
            if tc.idempotency_key:
                call_info += f" [magenta]\\[key={tc.idempotency_key}\\][/magenta]"
            table.add_row("Tool Call", call_info)

        for tr in step.tool_results:
            if tr.is_error:
                status = f"[bold red]FAILED: {tr.error_message}[/bold red]"
            else:
                status = f"[green]SUCCESS[/green] (out={json.dumps(tr.output)})"
            if tr.mutated_state:
                status += " [bold magenta]\\[ΔS mutated\\][/bold magenta]"
            table.add_row("Tool Result", status)

        self.console.print(Panel(table, border_style="blue"))

    def render(
        self,
        source: str | Path | dict[str, Any] | ExecutionTrace,
        jump_to_fail: bool = False,
    ) -> None:
        """Render the complete trace timeline, scorecard, and environmental diffs."""
        trace = self.load_trace(source)

        verdict_style = {
            Verdict.PASS: "bold green",
            Verdict.FAIL: "bold red",
            Verdict.UNVERIFIABLE: "bold yellow",
            Verdict.ANOMALOUS: "bold magenta",
        }.get(trace.verdict, "white")

        summary_text = Text()
        summary_text.append("Scenario: ", style="bold")
        summary_text.append(f"{trace.scenario_id}  ", style="cyan")
        summary_text.append("Execution: ", style="bold")
        summary_text.append(f"{trace.execution_id}  ", style="dim")
        summary_text.append("Agent: ", style="bold")
        summary_text.append(f"{trace.agent_id}  ", style="magenta")
        summary_text.append("Verdict: ", style="bold")
        summary_text.append(f"[{trace.verdict.value}]", style=verdict_style)

        self.console.print(
            Panel(
                summary_text,
                title="🔍 [bold]AgentEval Execution Replay[/bold]",
                border_style="cyan",
            )
        )

        if trace.loop_metrics:
            m = trace.loop_metrics
            m_table = Table(box=None, show_header=False)
            m_table.add_column("Metric", style="dim")
            m_table.add_column("Value", style="bold")
            m_table.add_row("Iterations / Steps", str(m.agent_loop_iterations))
            m_table.add_row("Total Time", f"{m.time_to_completion_ms:.1f}ms")
            m_table.add_row("Duplicate Actions", str(m.duplicate_actions))
            m_table.add_row("Termination Reason", m.termination_reason)
            self.console.print(
                Panel(m_table, title="📊 Loop & Telemetry Metrics", border_style="dim")
            )

        # Find first failing step if jump_to_fail requested
        fail_step_idx: int | None = None
        for step in trace.steps:
            if any(tr.is_error for tr in step.tool_results):
                fail_step_idx = step.step_number
                break

        if jump_to_fail and fail_step_idx is not None:
            self.console.print(
                f"\n🚨 [bold red]Jumping directly to first failure at Step {fail_step_idx}[/bold red]\n"
            )

        for step in trace.steps:
            is_failing_step = any(tr.is_error for tr in step.tool_results)
            if jump_to_fail and not is_failing_step and fail_step_idx is not None:
                continue

            step_border = "red" if is_failing_step else "blue"
            step_title = f"Step {step.step_number} ({step.latency_ms:.1f}ms)"
            if is_failing_step:
                step_title += " [bold red][FAILURE DETECTED][/bold red]"

            step_content: list[Any] = []
            if step.thought:
                step_content.append(
                    Panel(
                        f"[italic]{step.thought}[/italic]",
                        title="💭 Agent Reasoning",
                        border_style="dim",
                    )
                )

            if step.tool_calls:
                call_table = Table(title="🛠️ Tool Invocations", box=None)
                call_table.add_column("Call ID", style="dim")
                call_table.add_column("Tool", style="bold yellow")
                call_table.add_column("Arguments")
                call_table.add_column("Idempotency Key", style="magenta")

                for tc in step.tool_calls:
                    args_str = json.dumps(tc.arguments, indent=2)
                    args_syntax = Syntax(args_str, "json", theme="monokai", word_wrap=True)
                    call_table.add_row(
                        tc.call_id,
                        tc.tool_name,
                        args_syntax,
                        tc.idempotency_key or "-",
                    )
                step_content.append(call_table)

            if step.tool_results:
                res_table = Table(title="📥 Tool Results & Observability", box=None)
                res_table.add_column("Call ID", style="dim")
                res_table.add_column("Status", style="bold")
                res_table.add_column("Output / Error")
                res_table.add_column("State Mutated", style="bold magenta")

                for tr in step.tool_results:
                    status = "[red]ERROR[/red]" if tr.is_error else "[green]OK[/green]"
                    out_text = (
                        tr.error_message
                        if tr.is_error
                        else (json.dumps(tr.output) if tr.output is not None else "")
                    )
                    res_table.add_row(
                        tr.call_id,
                        status,
                        str(out_text),
                        "YES (ΔS)" if tr.mutated_state else "NO",
                    )
                step_content.append(res_table)

            self.console.print(
                Panel(
                    Group(*step_content),
                    title=f"[bold]{step_title}[/bold]",
                    border_style=step_border,
                )
            )

        # Environmental State Diffs (ΔS)
        if trace.state_diffs:
            for diff in trace.state_diffs:
                diff_table = Table(
                    title=f"🌐 Sealed Environment State Diff (ΔS): {diff.pre_snapshot_id} ➔ {diff.post_snapshot_id}",
                    box=None,
                )
                diff_table.add_column("Type", style="dim")
                diff_table.add_column("Changes", style="bold")

                if diff.files_added:
                    diff_table.add_row(
                        "Added Files", f"[green]{', '.join(diff.files_added)}[/green]"
                    )
                if diff.files_modified:
                    diff_table.add_row(
                        "Modified Files", f"[yellow]{', '.join(diff.files_modified)}[/yellow]"
                    )
                if diff.files_deleted:
                    diff_table.add_row(
                        "Deleted Files", f"[red]{', '.join(diff.files_deleted)}[/red]"
                    )
                if diff.db_mutations:
                    diff_table.add_row(
                        "DB Mutations", f"{len(diff.db_mutations)} table mutation(s)"
                    )
                self.console.print(
                    Panel(diff_table, border_style="magenta", title="📦 Environmental Evidence")
                )

        # Final Scorecard
        if trace.scorecard:
            sc = trace.scorecard
            score_table = Table(title="🏁 Final Assurance Verdict & Scorecard", box=None)
            score_table.add_column("Field", style="dim")
            score_table.add_column("Value", style="bold")
            score_table.add_row("Verdict", f"[{verdict_style}]{sc.verdict.value}[/{verdict_style}]")
            score_table.add_row("Outcome Pass", "YES" if sc.outcome_pass else "NO")
            score_table.add_row("Trajectory Score", f"{sc.trajectory_score * 100:.1f}%")
            score_table.add_row("Idempotency Score", f"{sc.idempotency_score * 100:.1f}%")
            score_table.add_row("Duplicate Side Effects", str(sc.duplicate_side_effects))
            if sc.failure_classes:
                score_table.add_row(
                    "Failure Classes",
                    f"[bold red]{', '.join(fc.value for fc in sc.failure_classes)}[/bold red]",
                )

            self.console.print(
                Panel(
                    score_table,
                    border_style="green" if sc.outcome_pass else "red",
                )
            )
