"""AgentEval command line interface: run scenarios, inject chaos faults, replay traces."""

import importlib
import importlib.util
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agenteval import __version__
from agenteval.adapters.callable import CallableAdapter
from agenteval.adapters.tool import LocalToolAdapter
from agenteval.core.loop import AgentLoopEngine
from agenteval.core.models import StepRecord, ToolCall, Verdict
from agenteval.engine.verdict import VerdictEngine
from agenteval.faults.injector import ToolFaultInjector
from agenteval.replay.player import TraceReplayer
from agenteval.sandbox.local import LocalSandbox
from agenteval.scenarios.loader import ScenarioLoader

app = typer.Typer(
    name="agenteval",
    help="AgentEval: Production-Grade AI Agent Assurance, Reliability & Chaos Engineering Platform",
    no_args_is_help=True,
)
console = Console()


def _load_agent_callable(
    spec: str,
) -> tuple[
    Callable[[str, list[StepRecord]], tuple[str | None, list[ToolCall], bool]],
    dict[str, Callable[..., Any]],
]:
    """Load agent step function and any exported tools from 'module:func' or 'path.py:func'."""
    if ":" not in spec:
        raise ValueError(
            f"Invalid agent specifier '{spec}'. Expected format 'module:function' or 'path/to/file.py:function'."
        )
    mod_part, fn_name = spec.split(":", 1)

    if mod_part.endswith(".py"):
        file_path = Path(mod_part).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"Agent script file not found: {file_path}")
        spec_obj = importlib.util.spec_from_file_location("dynamic_agent_module", file_path)
        if spec_obj is None or spec_obj.loader is None:
            raise ImportError(f"Could not load Python module from {file_path}")
        module = importlib.util.module_from_spec(spec_obj)
        sys.modules["dynamic_agent_module"] = module
        spec_obj.loader.exec_module(module)
    else:
        module = importlib.import_module(mod_part)

    fn = getattr(module, fn_name, None)
    if fn is None or not callable(fn):
        raise AttributeError(
            f"Agent callable '{fn_name}' not found or not callable in '{mod_part}'."
        )

    tools = getattr(module, "TOOLS", {})
    if not isinstance(tools, dict):
        tools = {}

    return fn, tools


@app.command("version")
def version() -> None:
    """Display AgentEval version and build information."""
    console.print(
        f"[bold cyan]AgentEval[/bold cyan] version [bold green]{__version__}[/bold green]"
    )


@app.command("replay")
def replay(
    trace_file: Annotated[
        Path,
        typer.Argument(
            help="Path to an execution trace JSON file",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    jump_to_fail: Annotated[
        bool,
        typer.Option(
            "--jump-to-fail",
            "-j",
            help="Jump directly to the first failed tool call or error step",
        ),
    ] = False,
) -> None:
    """Scrub through an agent execution timeline with Rich visual diagnostics."""
    replayer = TraceReplayer(console=console)
    replayer.render(trace_file, jump_to_fail=jump_to_fail)


@app.command("run")
def run(
    scenario_path: Annotated[
        Path,
        typer.Option(
            "--scenario",
            "-s",
            help="Path to the scenario YAML specification file",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ],
    agent_spec: Annotated[
        str | None,
        typer.Option(
            "--agent",
            "-a",
            help="Agent entrypoint (format: 'module:function' or 'path/to/script.py:function')",
        ),
    ] = None,
    live: Annotated[
        bool,
        typer.Option(
            "--live",
            "-l",
            help="Stream execution steps live to the terminal",
        ),
    ] = False,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Write execution trace JSON to the specified file path",
        ),
    ] = None,
    sandbox_dir: Annotated[
        Path | None,
        typer.Option(
            "--sandbox-dir",
            help="Custom root directory for the sandbox execution environment",
        ),
    ] = None,
) -> None:
    """Execute a scenario against an agent in a sealed sandbox with fault injection."""
    # 1. Load Scenario
    try:
        scenario = ScenarioLoader.from_yaml(scenario_path)
    except Exception as e:
        console.print(f"[bold red]Failed to load scenario:[/bold red] {e}")
        raise typer.Exit(code=1) from None

    console.print(
        Panel(
            f"[bold]Evaluating Scenario:[/bold] [cyan]{scenario.name}[/cyan] ({scenario.id})\n"
            f"[dim]{scenario.description}[/dim]",
            title="🛡️ AgentEval Assurance Engine",
            border_style="cyan",
        )
    )

    # 2. Setup Sandbox
    temp_dir_obj = None
    if sandbox_dir:
        sb_path = sandbox_dir
        sb_path.mkdir(parents=True, exist_ok=True)
    else:
        temp_dir_obj = tempfile.TemporaryDirectory(prefix=f"agenteval-{scenario.id}-")
        sb_path = Path(temp_dir_obj.name)

    sandbox = LocalSandbox(root_dir=sb_path)

    # 3. Setup Tools & Fault Injection
    tool_adapter = LocalToolAdapter()

    # Register default built-in sandbox tools
    def builtin_write_file(filename: str, content: str) -> dict[str, Any]:
        dest = sb_path / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        return {"status": "created", "path": filename, "bytes": len(content.encode("utf-8"))}

    def builtin_read_file(filename: str) -> str:
        target = sb_path / filename
        if not target.exists():
            raise FileNotFoundError(f"File '{filename}' does not exist in sandbox.")
        return target.read_text(encoding="utf-8")

    tool_adapter.register("write_file", builtin_write_file)
    tool_adapter.register("read_file", builtin_read_file)

    # 4. Resolve Agent Callable & Custom Tools
    agent_fn: Callable[[str, list[StepRecord]], tuple[str | None, list[ToolCall], bool]]
    resolved_spec = agent_spec
    if not resolved_spec:
        # Default simple echo agent for testing if none provided
        def fallback_agent(
            prompt: str, history: list[StepRecord]
        ) -> tuple[str | None, list[ToolCall], bool]:
            return "Task completed with default echo agent", [], True

        agent_fn = fallback_agent
    else:
        try:
            agent_fn, custom_tools = _load_agent_callable(resolved_spec)
            for t_name, t_fn in custom_tools.items():
                tool_adapter.register(t_name, t_fn)
        except Exception as e:
            console.print(f"[bold red]Failed to load agent '{resolved_spec}':[/bold red] {e}")
            raise typer.Exit(code=1) from None

    # Wrap with Fault Injector if scenario specifies rules
    injector = ToolFaultInjector(target_adapter=tool_adapter, rules=scenario.fault_rules)

    # 5. Execute Multi-Turn Agent Loop
    replayer = TraceReplayer(console=console)
    step_cb = replayer.render_step_live if live else None

    adapter = CallableAdapter(agent_fn=agent_fn)
    engine = AgentLoopEngine(
        adapter=adapter,
        sandbox=sandbox,
        tool_adapter=injector,
        max_steps=scenario.max_steps,
        agent_id=agent_spec or "default-echo-agent",
        step_callback=step_cb,
    )

    with console.status("[bold green]Executing agent evaluation loop...[/bold green]"):
        trace = engine.run(
            scenario_id=scenario.id,
            user_prompt=scenario.user_prompt,
        )

    # 6. Evaluate Verdict
    sc = VerdictEngine().evaluate(trace, scenario)

    # 7. Render Scorecard Table
    verdict_style = {
        Verdict.PASS: "bold green",
        Verdict.FAIL: "bold red",
        Verdict.UNVERIFIABLE: "bold yellow",
        Verdict.ANOMALOUS: "bold magenta",
    }.get(trace.verdict, "white")

    table = Table(title="Assurance Scorecard", box=None)
    table.add_column("Metric", style="dim")
    table.add_column("Verdict / Value", style="bold")

    table.add_row("Final Verdict", f"[{verdict_style}]{trace.verdict.value}[/{verdict_style}]")
    table.add_row("Outcome Pass", "YES" if sc.outcome_pass else "NO")
    table.add_row("Trajectory Score", f"{sc.trajectory_score * 100:.1f}%")
    table.add_row("Idempotency Score", f"{sc.idempotency_score * 100:.1f}%")
    table.add_row("Duplicate Side Effects", str(sc.duplicate_side_effects))
    if sc.failure_classes:
        f_classes_str = ", ".join(f.value for f in sc.failure_classes)
        table.add_row("Failure Classes", f"[red]{f_classes_str}[/red]")

    if trace.loop_metrics:
        table.add_row("Loop Iterations", str(trace.loop_metrics.agent_loop_iterations))
        table.add_row("Execution Latency", f"{trace.loop_metrics.time_to_completion_ms:.1f}ms")

    console.print(
        Panel(
            table,
            border_style="green" if trace.verdict == Verdict.PASS else "red",
            title="🏁 Result",
        )
    )

    # 8. Save Trace Artifacts
    default_trace_dir = Path(".agenteval/traces")
    default_trace_dir.mkdir(parents=True, exist_ok=True)
    auto_trace_file = default_trace_dir / f"{trace.execution_id}.json"
    auto_trace_file.write_text(trace.model_dump_json(indent=2), encoding="utf-8")

    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(trace.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"📁 Trace saved to: [cyan]{output}[/cyan]")
    else:
        console.print(f"📁 Trace auto-saved to: [dim]{auto_trace_file}[/dim]")

    if temp_dir_obj:
        temp_dir_obj.cleanup()

    # 9. Return exit code based on Verdict
    if trace.verdict == Verdict.PASS:
        raise typer.Exit(code=0)
    else:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
