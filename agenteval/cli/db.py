"""Database maintenance commands (SQLite import, etc.)."""

import shutil
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from agenteval.db.config import database_path
from agenteval.db.import_suites import import_suites_from_filesystem

db_app = typer.Typer(
    name="db",
    help="SQLite persistence utilities (ADR-004).",
    no_args_is_help=True,
)
console = Console()


@db_app.command("import-suites")
def import_suites(
    suite_root: Annotated[
        Path,
        typer.Option("--suite-root", help="Filesystem suite root (SuiteStore layout)"),
    ] = Path(".agenteval/suites"),
    database: Annotated[
        Path | None,
        typer.Option(
            "--database",
            "-d",
            help="SQLite file (default: .agenteval/agenteval.db or AGENTEVAL_DATABASE_URL)",
        ),
    ] = None,
    force: Annotated[
        bool,
        typer.Option(
            "--force/--no-force",
            help="Replace existing suite versions for the same agent",
        ),
    ] = True,
) -> None:
    """Import frozen suites and run JSON from disk into SQLite."""
    db = database or database_path()
    if not suite_root.is_dir():
        console.print(f"[bold red]Suite root not found:[/bold red] {suite_root}")
        raise typer.Exit(code=1)

    result = import_suites_from_filesystem(suite_root, db, force=force)

    if result.agents_imported == 0 and not result.errors:
        console.print(f"[yellow]No suites found under[/yellow] {suite_root}")
        raise typer.Exit(code=0)

    console.print(
        f"[green]Imported[/green] {result.agents_imported} agent(s), "
        f"{result.runs_imported} run(s), "
        f"{result.execution_steps_imported} execution step(s) → {db}"
    )
    if result.agent_ids:
        console.print(f"  agents: {', '.join(result.agent_ids)}")
    for err in result.errors:
        console.print(f"  [red]skip[/red] {err}")

    raise typer.Exit(code=1 if result.errors and result.agents_imported == 0 else 0)


@db_app.command("reset")
def reset_local_data(
    yes: Annotated[
        bool,
        typer.Option("--yes", "-y", help="Skip confirmation prompt"),
    ] = False,
    suite_root: Annotated[
        Path,
        typer.Option("--suite-root", help="Filesystem suite tree to remove"),
    ] = Path(".agenteval/suites"),
    keep_suite_files: Annotated[
        bool,
        typer.Option(
            "--keep-suite-files",
            help="Only delete SQLite; leave .agenteval/suites on disk",
        ),
    ] = False,
) -> None:
    """Remove local engine persistence (SQLite + optional suite files) for a clean slate."""
    db = database_path()
    targets: list[Path] = []
    if db.is_file():
        targets.append(db)
    if not keep_suite_files and suite_root.exists():
        targets.append(suite_root)

    if not targets:
        console.print("[yellow]Nothing to reset[/yellow] — no database or suite tree found.")
        raise typer.Exit(code=0)

    if not yes:
        console.print("[bold]Will delete:[/bold]")
        for path in targets:
            console.print(f"  • {path}")
        if not typer.confirm("Continue?", default=False):
            raise typer.Exit(code=1)

    for path in targets:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    console.print(
        "[green]Local engine data cleared.[/green] Restart [bold]agenteval serve[/bold] and refresh the console."
    )
