"""CLI: frozen regression suite init and run (B8, DR-010)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agenteval.core.manifest import AgentCard
from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.suite_store import SuiteExistsError, SuiteStore

suite_app = typer.Typer(
    name="suite",
    help="Frozen regression suites: init once, run many (no implicit regeneration).",
    no_args_is_help=True,
)
console = Console()


@suite_app.command("init")
def suite_init(
    manifest: Annotated[
        Path,
        typer.Option("--manifest", "-m", exists=True, dir_okay=False, readable=True),
    ],
    endpoint: Annotated[
        str,
        typer.Option("--endpoint", "-e", help="HTTP agent endpoint URL"),
    ],
    prd: Annotated[
        Path | None,
        typer.Option("--prd", exists=True, dir_okay=False, readable=True),
    ] = None,
    max_tests: Annotated[int, typer.Option("--max-tests", min=1, max=50)] = 10,
    suite_root: Annotated[
        Path,
        typer.Option("--suite-root", help="Root directory for frozen suites"),
    ] = Path(".agenteval/suites"),
    force_new_version: Annotated[
        bool,
        typer.Option("--force-new-version", help="Replace existing suite directory"),
    ] = False,
) -> None:
    """Generate pool + optimized pack once and persist (DR-010)."""
    card = AgentCard.from_yaml(manifest)
    fp = SuiteBootstrap.fingerprint_files(manifest, prd)
    bootstrap = SuiteBootstrap(max_tests=max_tests)
    try:
        pool, pack, coverage = bootstrap.build(card, fp)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from None

    store = SuiteStore(suite_root)
    manifest_obj = SuiteStore.new_manifest(card.id, fp, endpoint)
    try:
        out = store.init_suite(manifest_obj, pool, pack, force=force_new_version)
    except SuiteExistsError as e:
        console.print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1) from None

    console.print(f"[green]Suite initialized at[/green] {out}")
    console.print(f"  candidate_pool: {len(pool)} tests")
    console.print(f"  optimized_pack: {len(pack.tests)} tests")
    if coverage.critical_uncovered:
        console.print(f"  [yellow]critical gaps (preview):[/yellow] {coverage.critical_uncovered}")


@suite_app.command("run")
def suite_run(
    agent_id: Annotated[str, typer.Option("--agent-id", "-a", help="Agent id from manifest")],
    endpoint: Annotated[
        str | None,
        typer.Option("--endpoint", "-e", help="Override endpoint URL from init"),
    ] = None,
    suite_root: Annotated[Path, typer.Option("--suite-root")] = Path(".agenteval/suites"),
) -> None:
    """Execute frozen test pack only (no generation)."""
    store = SuiteStore(suite_root)
    try:
        manifest = store.load_manifest(agent_id)
        pack = store.load_pack(agent_id)
    except FileNotFoundError:
        console.print(
            f"[bold red]No suite for '{agent_id}'. Run `agenteval suite init` first.[/bold red]"
        )
        raise typer.Exit(code=1) from None

    url = endpoint or manifest.endpoint_profile
    if not url:
        console.print("[bold red]Endpoint missing; pass --endpoint[/bold red]")
        raise typer.Exit(code=1)

    runner = BlackboxRunner(endpoint_url=url)
    report = runner.run_pack(pack)
    pool = store.load_pool(agent_id)
    coverage = CoverageMapper().report(pool, pack.tests)
    report.coverage_report = coverage
    store.save_run(agent_id, report)

    table = Table(title=f"Suite run {report.run_id} (v{report.suite_version})")
    table.add_column("Test", style="cyan")
    table.add_column("Verdict")
    table.add_column("Rationale", max_width=60)
    for r in report.results:
        style = {"PASS": "green", "FAIL": "red"}.get(r.verdict, "yellow")
        table.add_row(r.test_id, f"[{style}]{r.verdict}[/{style}]", r.rationale[:60])
    console.print(table)
    console.print(
        f"\nSummary: {report.passed} passed, {report.failed} failed, "
        f"{report.unverifiable} unverifiable (rule-based, no LLM judge)"
    )

    prev = store.load_latest_run(agent_id)
    if prev and prev.run_id != report.run_id:
        console.print("[dim]Previous run comparison: use runs/*.json for full diff[/dim]")

    raise typer.Exit(code=0 if report.failed == 0 else 1)
