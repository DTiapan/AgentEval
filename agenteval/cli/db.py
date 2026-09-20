"""Database maintenance commands (SQLite import, etc.)."""

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
