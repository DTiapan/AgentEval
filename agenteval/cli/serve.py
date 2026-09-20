"""Start the AgentEval HTTP API (E3)."""

from typing import Annotated

import typer
import uvicorn

serve_app = typer.Typer(
    name="serve",
    help="Run the AgentEval HTTP API (same services as CLI).",
    invoke_without_command=True,
)


@serve_app.callback()
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port")] = 8766,
    reload: Annotated[bool, typer.Option(help="Dev auto-reload")] = False,
) -> None:
    """Listen for REST requests under /v1/suites/*."""
    uvicorn.run(
        "agenteval.api.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
