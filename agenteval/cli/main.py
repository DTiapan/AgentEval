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
from agenteval.adapters.base import AgentAdapter
from agenteval.adapters.callable import CallableAdapter
from agenteval.adapters.http import HTTPAdapter
from agenteval.adapters.tool import LocalToolAdapter
from agenteval.core.loop import AgentLoopEngine
from agenteval.core.manifest import AgentCard, ToolRequirement
from agenteval.core.models import StepRecord, ToolCall, Verdict
from agenteval.engine.verdict import VerdictEngine
from agenteval.faults.injector import ToolFaultInjector
from agenteval.introspect.persona import PersonaIntrospector
from agenteval.personas.dynamic import DynamicPersonaGenerator, RankedPersonaCandidate
from agenteval.recommender.jev_client import JevClassifierClient
from agenteval.recommender.router import MetricRouter
from agenteval.replay.player import TraceReplayer
from agenteval.sandbox.local import LocalSandbox
from agenteval.scenarios.compiler import ScenarioCompiler
from agenteval.scenarios.loader import ScenarioLoader
from agenteval.scenarios.schema import TestScenario
from agenteval.cli.suite import suite_app

app = typer.Typer(
    name="agenteval",
    help="AgentEval: Production-Grade AI Agent Assurance, Reliability & Chaos Engineering Platform",
    no_args_is_help=True,
)
console = Console()

app.add_typer(suite_app, name="suite")


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


@app.command("plan")
def plan(
    manifest_path: Annotated[
        Path | None,
        typer.Option(
            "--manifest",
            "-m",
            help="Path to an AgentCard manifest YAML file",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    agent_spec: Annotated[
        str | None,
        typer.Option(
            "--agent",
            "-a",
            help="Agent entrypoint (format: 'module:function' or 'path/to/script.py:function')",
        ),
    ] = None,
    persona_path: Annotated[
        Path | None,
        typer.Option(
            "--persona",
            "-p",
            help="Path to an agency-agents markdown persona file",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    endpoint: Annotated[
        str | None,
        typer.Option(
            "--endpoint",
            "-e",
            help="Live HTTP/REST agent endpoint URL (e.g. http://localhost:8000/chat)",
        ),
    ] = None,
    prd_path: Annotated[
        Path | None,
        typer.Option(
            "--prd",
            help="Path to a functional requirements / PRD markdown file",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    top_personas: Annotated[
        int,
        typer.Option(
            "--top-personas",
            "-k",
            help="Number of top stack-ranked personas to formulate and test (default: 3)",
            min=1,
            max=10,
        ),
    ] = 3,
) -> None:
    """Generate and preview a calibrated evaluation plan for an agent."""
    if not manifest_path and not agent_spec and not persona_path and not endpoint and not prd_path:
        console.print(
            "[bold red]Error:[/bold red] Please provide one of: --persona, --manifest, --prd, --endpoint, or --agent."
        )
        raise typer.Exit(code=1)

    compiled_scenarios: list[TestScenario] = []
    matched_personas: list[tuple[RankedPersonaCandidate, str]] = []
    dyn_gen = DynamicPersonaGenerator()

    if persona_path:
        card = PersonaIntrospector.parse_file(persona_path)
        jev_res = JevClassifierClient().classify_agent(card)
        plan_obj = MetricRouter().recommend(card)
        compiled_scenarios = ScenarioCompiler.compile_scenarios(card)
    elif manifest_path:
        card = AgentCard.from_yaml(manifest_path)
        jev_res = JevClassifierClient().classify_agent(card)
        plan_obj = MetricRouter().recommend(card)
        compiled_scenarios = ScenarioCompiler.compile_scenarios(card)
    elif prd_path:
        prd_text = prd_path.read_text(encoding="utf-8")
        probe_card = AgentCard(
            id=prd_path.stem,
            name=prd_path.stem.replace("-", " ").title(),
            capabilities=PersonaIntrospector._extract_capabilities(prd_text),
        )
        ranked_cands = dyn_gen.discover_and_rank_personas(
            probe_card, top_k=top_personas, customer_context=prd_text
        )
        for cand in ranked_cands:
            c_card, status = dyn_gen.synthesize_or_load(cand, probe_card)
            matched_personas.append((cand, status))

        primary_cand = ranked_cands[0]
        card, _ = dyn_gen.synthesize_or_load(primary_cand, probe_card)
        card.id = prd_path.stem
        jev_res = JevClassifierClient().classify_agent(card)
        plan_obj = MetricRouter().recommend(card)
        compiled_scenarios = ScenarioCompiler.compile_scenarios(card)
    elif endpoint:
        clean_name = endpoint.split("/")[-1] or "chat"
        probe_card = AgentCard(
            id=f"endpoint:{endpoint}",
            name=f"HTTP Agent ({clean_name})",
        )
        ranked_cands = dyn_gen.discover_and_rank_personas(
            probe_card, top_k=top_personas, customer_context=f"HTTP Endpoint: {endpoint}"
        )
        for cand in ranked_cands:
            c_card, status = dyn_gen.synthesize_or_load(cand, probe_card)
            matched_personas.append((cand, status))

        primary_cand = ranked_cands[0]
        card, _ = dyn_gen.synthesize_or_load(primary_cand, probe_card)
        card.id = f"endpoint:{endpoint}"
        jev_res = JevClassifierClient().classify_agent(card)
        plan_obj = MetricRouter().recommend(card)
        compiled_scenarios = ScenarioCompiler.compile_scenarios(card)
    else:
        assert agent_spec is not None
        try:
            fn, tools = _load_agent_callable(agent_spec)
            context = getattr(fn, "__doc__", agent_spec) or agent_spec
            clean_name = agent_spec.split(":")[-1].replace("_", " ").title()
            probe_card = AgentCard(
                id=agent_spec,
                name=clean_name,
                tools_required=[ToolRequirement(name=t_name) for t_name in tools.keys()],
            )
            ranked_cands = dyn_gen.discover_and_rank_personas(
                probe_card, top_k=top_personas, customer_context=context
            )
            for cand in ranked_cands:
                c_card, status = dyn_gen.synthesize_or_load(cand, probe_card)
                matched_personas.append((cand, status))

            primary_cand = ranked_cands[0]
            card, _ = dyn_gen.synthesize_or_load(primary_cand, probe_card)
            card.id = agent_spec
            jev_res = JevClassifierClient().classify_agent(card)
            plan_obj = MetricRouter().recommend(card)
            compiled_scenarios = ScenarioCompiler.compile_scenarios(card)
        except Exception as e:
            console.print(f"[bold red]Failed to inspect agent '{agent_spec}':[/bold red] {e}")
            raise typer.Exit(code=1) from None

    # Render Plan with Rich
    console.print(
        Panel(
            f"[bold]Target Agent:[/bold] [cyan]{plan_obj.agent_id}[/cyan]\n"
            f"[bold]Classified Archetype:[/bold] [bold magenta]{plan_obj.primary_archetype.value}[/bold magenta] "
            f"([dim]Confidence: {plan_obj.confidence * 100:.0f}%[/dim])\n"
            f"[bold]Intelligence Layer:[/bold] [yellow]{jev_res.source}[/yellow] "
            f"([dim]Risk Tier: {jev_res.risk_level.upper()}[/dim])",
            title="🎯 AgentEval Metric Recommender Plan",
            border_style="cyan",
        )
    )

    # Universal Core Table (Group A)
    u_table = Table(title="Group A: Universal Core Metrics (Mandatory)", box=None)
    u_table.add_column("Metric Name", style="bold green")
    u_table.add_column("Plane", style="dim", width=8)
    u_table.add_column("Description")

    for m in plan_obj.universal_metrics:
        u_table.add_row(m.name, f"Plane {m.plane}", m.description)

    console.print(Panel(u_table, border_style="green"))

    # Domain Specific Table (Group B)
    d_table = Table(
        title=f"Group B: Domain-Specific Metrics ({plan_obj.primary_archetype.value})", box=None
    )
    d_table.add_column("Metric Name", style="bold yellow")
    d_table.add_column("Plane", style="dim", width=8)
    d_table.add_column("Description")

    for m in plan_obj.domain_metrics:
        d_table.add_row(m.name, f"Plane {m.plane}", m.description)

    console.print(Panel(d_table, border_style="yellow"))

    if plan_obj.fault_suggestions:
        f_table = Table(title="Suggested Chaos Engineering & Fault Scenarios", box=None)
        f_table.add_column("Fault Injection Rule", style="bold red")
        for f_sug in plan_obj.fault_suggestions:
            f_table.add_row(f"⚡ {f_sug}")
        console.print(Panel(f_table, border_style="red"))

    if matched_personas:
        p_table = Table(title="🎯 Dynamic Stack-Ranked Personas (LiteLLM Discovery)", box=None)
        p_table.add_column("Rank", style="bold cyan", width=6)
        p_table.add_column("Persona Name", style="bold")
        p_table.add_column("Operational Tier", style="magenta")
        p_table.add_column("Est. Volume", style="dim", justify="right", width=12)
        p_table.add_column("Status", style="bold")
        p_table.add_column("Testing Intent / Invariants")
        for cand, status_str in matched_personas:
            status_badge = (
                "[green]CACHED[/green]" if status_str == "CACHED" else "[yellow]SYNTHESIZED[/yellow]"
            )
            p_table.add_row(
                f"#{cand.rank}",
                cand.name,
                cand.tier.value,
                f"{cand.estimated_volume_pct}%",
                status_badge,
                cand.key_intent,
            )
        console.print(Panel(p_table, border_style="cyan"))

    if compiled_scenarios:
        s_table = Table(title="Dynamically Compiled Test Scenarios (Plane 0)", box=None)
        s_table.add_column("Scenario ID", style="bold cyan")
        s_table.add_column("Name", style="bold")
        s_table.add_column("Fault Rules", style="red")
        s_table.add_column("Max Steps", justify="right")
        for sc in compiled_scenarios:
            fault_desc = f"{len(sc.fault_rules)} rules" if sc.fault_rules else "None (Happy Path)"
            s_table.add_row(sc.id, sc.name, fault_desc, str(sc.max_steps))
        console.print(Panel(s_table, border_style="cyan"))


@app.command("run")
def run(
    scenario_path: Annotated[
        Path | None,
        typer.Option(
            "--scenario",
            "-s",
            help="Path to the scenario YAML specification file",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    persona_path: Annotated[
        Path | None,
        typer.Option(
            "--persona",
            "-p",
            help="Path to an agency-agents markdown persona file (auto-compiles scenarios)",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    prd_path: Annotated[
        Path | None,
        typer.Option(
            "--prd",
            help="Path to a PRD requirements file (auto-compiles scenarios)",
            exists=True,
            dir_okay=False,
            readable=True,
        ),
    ] = None,
    endpoint: Annotated[
        str | None,
        typer.Option(
            "--endpoint",
            "-e",
            help="Live HTTP/REST agent endpoint URL (e.g. http://localhost:8000/chat)",
        ),
    ] = None,
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
    top_personas: Annotated[
        int,
        typer.Option(
            "--top-personas",
            "-k",
            help="Number of top stack-ranked personas to consider (default: 3)",
            min=1,
            max=10,
        ),
    ] = 3,
) -> None:
    """Execute a scenario against an agent in a sealed sandbox with fault injection."""
    # 1. Resolve Scenario
    dyn_gen = DynamicPersonaGenerator()
    if scenario_path:
        try:
            scenario = ScenarioLoader.from_yaml(scenario_path)
        except Exception as e:
            console.print(f"[bold red]Failed to load scenario:[/bold red] {e}")
            raise typer.Exit(code=1) from None
    elif persona_path:
        scenarios = ScenarioCompiler.compile_from_persona(persona_path)
        if not scenarios:
            console.print(
                "[bold red]No executable scenarios could be compiled from persona.[/bold red]"
            )
            raise typer.Exit(code=1)
        scenario = scenarios[0]
    elif prd_path:
        prd_text = prd_path.read_text(encoding="utf-8")
        probe_card = AgentCard(
            id=prd_path.stem,
            name=prd_path.stem.replace("-", " ").title(),
            capabilities=PersonaIntrospector._extract_capabilities(prd_text),
        )
        ranked_cands = dyn_gen.discover_and_rank_personas(
            probe_card, top_k=top_personas, customer_context=prd_text
        )
        card, status = dyn_gen.synthesize_or_load(ranked_cands[0], probe_card)
        scenarios = ScenarioCompiler.compile_scenarios(card)
        if not scenarios:
            console.print(
                "[bold red]No executable scenarios could be compiled from PRD.[/bold red]"
            )
            raise typer.Exit(code=1)
        scenario = scenarios[0]
        status_str = "[green]CACHED[/green]" if status == "CACHED" else "[yellow]SYNTHESIZED[/yellow]"
        console.print(
            f"[dim]Auto-selected #{ranked_cands[0].rank} {ranked_cands[0].tier.value} Persona:[/dim] [bold cyan]{card.name}[/bold cyan] ({status_str})"
        )
    elif endpoint:
        clean_name = endpoint.split("/")[-1] or "chat"
        probe_card = AgentCard(
            id=f"endpoint:{endpoint}",
            name=f"HTTP Agent ({clean_name})",
        )
        ranked_cands = dyn_gen.discover_and_rank_personas(
            probe_card, top_k=top_personas, customer_context=f"HTTP Endpoint: {endpoint}"
        )
        card, status = dyn_gen.synthesize_or_load(ranked_cands[0], probe_card)
        scenarios = ScenarioCompiler.compile_scenarios(card)
        if not scenarios:
            console.print(
                "[bold red]No executable scenarios could be compiled from auto-selected persona.[/bold red]"
            )
            raise typer.Exit(code=1)
        scenario = scenarios[0]
        status_str = "[green]CACHED[/green]" if status == "CACHED" else "[yellow]SYNTHESIZED[/yellow]"
        console.print(
            f"[dim]Auto-selected #{ranked_cands[0].rank} {ranked_cands[0].tier.value} Persona:[/dim] [bold cyan]{card.name}[/bold cyan] ({status_str})"
        )
    elif agent_spec:
        try:
            fn, tools = _load_agent_callable(agent_spec)
            context = getattr(fn, "__doc__", agent_spec) or agent_spec
            clean_name = agent_spec.split(":")[-1].replace("_", " ").title()
            probe_card = AgentCard(
                id=agent_spec,
                name=clean_name,
                tools_required=[ToolRequirement(name=t_name) for t_name in tools.keys()],
            )
            ranked_cands = dyn_gen.discover_and_rank_personas(
                probe_card, top_k=top_personas, customer_context=context
            )
            card, status = dyn_gen.synthesize_or_load(ranked_cands[0], probe_card)
            scenarios = ScenarioCompiler.compile_scenarios(card)
            if not scenarios:
                console.print(
                    "[bold red]No executable scenarios could be compiled from agent.[/bold red]"
                )
                raise typer.Exit(code=1)
            scenario = scenarios[0]
            status_str = "[green]CACHED[/green]" if status == "CACHED" else "[yellow]SYNTHESIZED[/yellow]"
            console.print(
                f"[dim]Auto-selected #{ranked_cands[0].rank} {ranked_cands[0].tier.value} Persona:[/dim] [bold cyan]{card.name}[/bold cyan] ({status_str})"
            )
        except Exception as e:
            console.print(f"[bold red]Failed to inspect agent '{agent_spec}':[/bold red] {e}")
            raise typer.Exit(code=1) from None
    else:
        console.print(
            "[bold red]Error:[/bold red] Please provide either --scenario, --persona, --prd, --endpoint, or --agent."
        )
        raise typer.Exit(code=1)

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

    # 4. Resolve Agent Adapter (HTTP vs In-process Callable)
    adapter: AgentAdapter
    agent_id: str

    if endpoint:
        adapter = HTTPAdapter(endpoint_url=endpoint, agent_id=f"http-agent ({endpoint})")
        agent_id = f"endpoint:{endpoint}"
    elif agent_spec:
        try:
            agent_fn, custom_tools = _load_agent_callable(agent_spec)
            for t_name, t_fn in custom_tools.items():
                tool_adapter.register(t_name, t_fn)
            adapter = CallableAdapter(agent_fn=agent_fn)
            agent_id = agent_spec
        except Exception as e:
            console.print(f"[bold red]Failed to load agent '{agent_spec}':[/bold red] {e}")
            raise typer.Exit(code=1) from None
    else:

        def fallback_agent(
            prompt: str, history: list[StepRecord]
        ) -> tuple[str | None, list[ToolCall], bool]:
            return "Task completed with default echo agent", [], True

        adapter = CallableAdapter(agent_fn=fallback_agent)
        agent_id = "default-echo-agent"

    # Wrap with Fault Injector if scenario specifies rules
    injector = ToolFaultInjector(target_adapter=tool_adapter, rules=scenario.fault_rules)

    # 5. Execute Multi-Turn Agent Loop
    replayer = TraceReplayer(console=console)
    step_cb = replayer.render_step_live if live else None

    engine = AgentLoopEngine(
        adapter=adapter,
        sandbox=sandbox,
        tool_adapter=injector,
        max_steps=scenario.max_steps,
        agent_id=agent_id,
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
