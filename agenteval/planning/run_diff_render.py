"""CLI rendering for suite run diffs."""

from rich.console import Console
from rich.table import Table

from agenteval.planning.run_diff import SuiteRunDiff, VerdictChangeKind


def render_run_diff(console: Console, diff: SuiteRunDiff) -> None:
    material = diff.material_changes
    if not material:
        console.print(
            f"\n[dim]No verdict changes vs run {diff.baseline_run_id} "
            f"(suite v{diff.baseline_suite_version}).[/dim]"
        )
        return

    table = Table(
        title=f"What changed vs run {diff.baseline_run_id} (suite v{diff.baseline_suite_version})",
        box=None,
    )
    table.add_column("Change", style="bold")
    table.add_column("Test", style="cyan", max_width=40)
    table.add_column("Before")
    table.add_column("After")

    kind_style = {
        VerdictChangeKind.REGRESSED: "red",
        VerdictChangeKind.FIXED: "green",
        VerdictChangeKind.CHANGED: "yellow",
        VerdictChangeKind.NEW: "cyan",
        VerdictChangeKind.REMOVED: "dim",
    }

    for change in material:
        style = kind_style.get(change.kind, "white")
        before = change.previous_verdict or "—"
        after = change.current_verdict or "—"
        table.add_row(
            f"[{style}]{change.kind.value}[/{style}]",
            change.test_id,
            before,
            after,
        )

    console.print(table)
    console.print(f"[dim]Regressions: {len(diff.regressions)} | Fixes: {len(diff.fixes)}[/dim]")
