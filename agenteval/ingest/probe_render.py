"""CLI rendering for endpoint probe (E2)."""

from rich.console import Console
from rich.panel import Panel

from agenteval.ingest.endpoint_probe import EndpointProbeResult


def render_endpoint_probe(console: Console, probe: EndpointProbeResult) -> None:
    if probe.reachable:
        status = f"[green]reachable[/green] HTTP {probe.http_status} ({probe.latency_ms:.0f} ms)"
    else:
        status = f"[red]unreachable[/red] {probe.error or 'probe failed'}"

    tools = (
        ", ".join(probe.inferred_tool_names)
        if probe.inferred_tool_names
        else "[dim]none inferred[/dim]"
    )
    keys = ", ".join(probe.response_keys) if probe.response_keys else "[dim]n/a[/dim]"

    console.print(
        Panel(
            f"[bold]URL:[/bold] {probe.endpoint_url}\n"
            f"[bold]Status:[/bold] {status}\n"
            f"[bold]JSON keys:[/bold] {keys}\n"
            f"[bold]Inferred tools:[/bold] {tools}",
            title="Endpoint probe (black-box)",
            border_style="blue",
        )
    )
