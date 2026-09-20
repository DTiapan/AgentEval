"""Black-box test pack preview for `agenteval plan` (same path as `suite init`, no persist)."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agenteval.core.manifest import AgentCard
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.models import CandidateTest, CoverageReport, TestPack


def build_blackbox_preview(
    card: AgentCard,
    manifest_path: Path | None,
    prd_path: Path | None,
    max_tests: int,
) -> tuple[list[CandidateTest], TestPack, CoverageReport]:
    """Run pool generation + optimization without writing a frozen suite."""
    if manifest_path is not None:
        fingerprint = SuiteBootstrap.fingerprint_files(manifest_path, prd_path)
    elif prd_path is not None:
        fingerprint = SuiteBootstrap.fingerprint_prd(prd_path)
    else:
        raise ValueError("manifest_path or prd_path required for preview fingerprint")
    return SuiteBootstrap(max_tests=max_tests).build(card, fingerprint)


def render_blackbox_pack_preview(
    console: Console,
    card: AgentCard,
    manifest_path: Path | None,
    prd_path: Path | None,
    max_tests: int,
) -> None:
    """Rich summary: pool size, optimized pack, sample tests (B8 preview)."""
    try:
        pool, pack, coverage = build_blackbox_preview(card, manifest_path, prd_path, max_tests)
    except ValueError as exc:
        console.print(
            Panel(
                f"[yellow]{exc}[/yellow]\n"
                "[dim]Add capabilities to the AgentCard to preview a black-box regression pack.[/dim]",
                title="Black-Box Test Pack Preview",
                border_style="yellow",
            )
        )
        return

    summary = (
        f"[bold]Agent:[/bold] [cyan]{card.id}[/cyan]\n"
        f"[bold]Requirements fingerprint:[/bold] [dim]{pack.requirements_fingerprint}[/dim]\n"
        f"[bold]Candidate pool:[/bold] {len(pool)} tests\n"
        f"[bold]Optimized pack:[/bold] {len(pack.tests)} tests (max {max_tests})\n"
        f"[bold]Coverage axes:[/bold] "
        + ", ".join(f"{k}={v:.0%}" for k, v in sorted(coverage.axes.items()))
    )
    if coverage.critical_uncovered:
        summary += f"\n[bold yellow]Critical gaps (pool vs pack):[/bold yellow] {coverage.critical_uncovered}"

    console.print(
        Panel(
            summary,
            title="Black-Box Test Pack Preview (no files written)",
            border_style="blue",
        )
    )

    table = Table(title="Selected tests in optimized pack", box=None)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Category", style="magenta")
    table.add_column("Name", style="bold")
    table.add_column("Test ID", style="cyan", max_width=36)
    for index, test in enumerate(pack.tests, start=1):
        table.add_row(str(index), test.category, test.name, test.id)

    console.print(Panel(table, border_style="blue"))
    if manifest_path is not None:
        freeze_cmd = (
            f"`agenteval suite init -m {manifest_path} -e <endpoint> --max-tests {max_tests}`"
        )
    else:
        freeze_cmd = (
            f"`agenteval suite init --prd {prd_path} -e <endpoint> --max-tests {max_tests}`"
        )
    console.print(f"[dim]Freeze this pack:[/dim] {freeze_cmd}")
