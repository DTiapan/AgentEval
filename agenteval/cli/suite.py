"""CLI: frozen regression suite init and run (B8, DR-010)."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from agenteval.core.manifest import AgentCard
from agenteval.ingest.bootstrap import AgentBootstrap
from agenteval.ingest.endpoint_probe import EndpointProber
from agenteval.ingest.probe_render import render_endpoint_probe
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.coverage import CoverageMapper
from agenteval.planning.run_diff import SuiteRunDiff, diff_suite_runs
from agenteval.planning.run_diff_render import render_run_diff
from agenteval.planning.suite_store import SuiteExistsError, SuiteStore
from agenteval.planning.suite_sync import SuiteSynchronizer

suite_app = typer.Typer(
    name="suite",
    help="Frozen regression suites: init once, run many (no implicit regeneration).",
    no_args_is_help=True,
)
console = Console()


@suite_app.command("init")
def suite_init(
    endpoint: Annotated[
        str | None,
        typer.Option(
            "--endpoint",
            "-e",
            help="HTTP agent URL (optional at init; required for suite run unless stored)",
        ),
    ] = None,
    manifest: Annotated[
        Path | None,
        typer.Option("--manifest", "-m", exists=True, dir_okay=False, readable=True),
    ] = None,
    prd: Annotated[
        Path | None,
        typer.Option(
            "--prd",
            exists=True,
            dir_okay=False,
            readable=True,
            help="Functional requirements (North Star entry; no AgentCard YAML required)",
        ),
    ] = None,
    agent_id: Annotated[
        str | None,
        typer.Option("--agent-id", "-a", help="Agent id when using --prd only"),
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
    if manifest is None and prd is None:
        console.print("[bold red]Error:[/bold red] Provide --prd or --manifest.")
        raise typer.Exit(code=1)

    probe_result = None
    if manifest is not None:
        card = AgentCard.from_yaml(manifest)
        fp = SuiteBootstrap.fingerprint_files(manifest, prd)
        source_label = str(manifest)
    else:
        assert prd is not None
        card, fp, probe_result = AgentBootstrap.from_prd(
            prd,
            agent_id=agent_id,
            endpoint_url=endpoint,
            probe_endpoint=endpoint is not None,
        )
        source_label = str(prd)

    if endpoint and manifest is not None:
        probe_result = EndpointProber().probe(endpoint)
        card = EndpointProber.merge_tools(card, probe_result)

    bootstrap = SuiteBootstrap(max_tests=max_tests)
    try:
        pool, pack, coverage = bootstrap.build(card, fp)
    except ValueError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        raise typer.Exit(code=1) from None

    store = SuiteStore(suite_root)
    manifest_obj = SuiteStore.new_manifest(card.id, fp, endpoint or "")
    try:
        out = store.init_suite(manifest_obj, pool, pack, force=force_new_version)
    except SuiteExistsError as e:
        console.print(f"[bold red]{e}[/bold red]")
        raise typer.Exit(code=1) from None

    derived = out / "derived_agent_card.json"
    derived.write_text(card.model_dump_json(indent=2), encoding="utf-8")
    if probe_result is not None:
        (out / "endpoint_probe.json").write_text(
            probe_result.model_dump_json(indent=2), encoding="utf-8"
        )
        render_endpoint_probe(console, probe_result)

    console.print(f"[green]Suite initialized at[/green] {out}")
    console.print(f"  source: {source_label}")
    if prd and manifest is None:
        console.print(f"  derived AgentCard: {derived}")
    if not endpoint:
        console.print(
            "[yellow]No endpoint stored.[/yellow] Run with "
            f"`agenteval suite run --agent-id {card.id} -e <url>` when ready."
        )
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

    previous_run = store.load_latest_run(agent_id)

    runner = BlackboxRunner(endpoint_url=url)
    report = runner.run_pack(pack)
    pool = store.load_pool(agent_id)
    coverage = CoverageMapper().report(pool, pack.tests)
    report.coverage_report = coverage

    if previous_run is not None:
        run_diff = diff_suite_runs(previous_run, report)
        if run_diff is not None:
            report.run_diff = run_diff.model_dump(mode="json")
        elif previous_run.suite_version != report.suite_version:
            console.print(
                "[yellow]Skipping verdict diff:[/yellow] suite version changed "
                f"(v{previous_run.suite_version} → v{report.suite_version})."
            )

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
    if coverage.critical_uncovered:
        console.print(f"[yellow]Coverage gaps:[/yellow] {coverage.critical_uncovered}")

    if report.run_diff:
        render_run_diff(console, SuiteRunDiff.model_validate(report.run_diff))

    raise typer.Exit(code=0 if report.failed == 0 else 1)


@suite_app.command("sync")
def suite_sync(
    agent_id: Annotated[str, typer.Option("--agent-id", "-a", help="Agent id from frozen suite")],
    manifest: Annotated[
        Path,
        typer.Option("--manifest", "-m", exists=True, dir_okay=False, readable=True),
    ],
    prd: Annotated[
        Path | None,
        typer.Option("--prd", exists=True, dir_okay=False, readable=True),
    ] = None,
    max_tests: Annotated[int, typer.Option("--max-tests", min=1, max=50)] = 10,
    suite_root: Annotated[Path, typer.Option("--suite-root")] = Path(".agenteval/suites"),
) -> None:
    """Prune tests for removed capabilities; extend pool for new ones (DR-011)."""
    card = AgentCard.from_yaml(manifest)
    store = SuiteStore(suite_root)
    syncer = SuiteSynchronizer(max_tests=max_tests)
    try:
        result = syncer.sync(store, agent_id, card, manifest, prd)
    except FileNotFoundError:
        console.print(
            f"[bold red]No suite for '{agent_id}'. Run `agenteval suite init` first.[/bold red]"
        )
        raise typer.Exit(code=1) from None
    except ValueError as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        raise typer.Exit(code=1) from None

    if result.noop:
        console.print("[green]Suite already matches manifest[/green] (fingerprint and capabilities).")
        raise typer.Exit(code=0)

    console.print(
        f"[green]Suite synced[/green] v{result.previous_version} → v{result.new_version} "
        f"(fingerprint {result.requirements_fingerprint})"
    )
    if result.removed_capabilities:
        console.print(f"  [yellow]Pruned capabilities:[/yellow] {result.removed_capabilities}")
        console.print(f"  [dim]Removed {len(result.removed_test_ids)} tests (archived)[/dim]")
    if result.added_capabilities:
        console.print(f"  [cyan]Added capabilities:[/cyan] {result.added_capabilities}")
    console.print(f"  pool: {result.pool_size} tests | pack: {result.pack_size} tests")
