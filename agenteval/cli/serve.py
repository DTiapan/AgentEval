"""Start the AgentEval HTTP API (E3) and optional web UI (E4)."""

import os
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

serve_app = typer.Typer(
    name="serve",
    help="Run the AgentEval HTTP API (same services as CLI).",
    invoke_without_command=True,
)

_UI_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


@serve_app.callback()
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port")] = 8766,
    reload: Annotated[bool, typer.Option(help="Dev auto-reload")] = False,
    with_ui: Annotated[
        bool,
        typer.Option(
            "--with-ui",
            help="Serve built web UI from web/dist (run npm run build in web/ first)",
        ),
    ] = False,
) -> None:
    """Listen for REST requests under /v1/suites/*."""
    if with_ui:
        if not _UI_DIST.is_dir():
            typer.echo(
                f"[agenteval] UI build missing at {_UI_DIST}. "
                "Run: cd web && npm install && npm run build",
                err=True,
            )
            raise typer.Exit(code=1)
        os.environ["AGENTEVAL_SERVE_UI"] = "1"
        os.environ["AGENTEVAL_UI_DIST"] = str(_UI_DIST)

    uvicorn.run(
        "agenteval.api.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
