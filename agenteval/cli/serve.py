"""Start the AgentEval HTTP API (E3) and optional web UI (E4)."""

import os
from pathlib import Path
from typing import Annotated

import typer
import uvicorn

serve_app = typer.Typer(
    name="serve",
    help="Run the Web Console + HTTP API (primary product entry; DR-021).",
    invoke_without_command=True,
)

_UI_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


@serve_app.callback()
def serve(
    host: Annotated[str, typer.Option(help="Bind host")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Bind port")] = 8766,
    reload: Annotated[bool, typer.Option(help="Dev auto-reload")] = False,
    with_ui: Annotated[
        bool | None,
        typer.Option(
            "--with-ui/--no-ui",
            help="Serve web/dist console (default: on when web/dist exists)",
        ),
    ] = None,
    sqlite: Annotated[
        bool,
        typer.Option(
            "--sqlite/--no-sqlite",
            help="Persist suites, tests, and runs to SQLite (default on; ADR-004)",
        ),
    ] = True,
) -> None:
    """Listen for REST requests under /v1/suites/*."""
    if sqlite:
        os.environ["AGENTEVAL_USE_SQLITE"] = "1"
    else:
        os.environ["AGENTEVAL_USE_SQLITE"] = "0"

    serve_ui = with_ui if with_ui is not None else _UI_DIST.is_dir()

    if serve_ui:
        if not _UI_DIST.is_dir():
            typer.echo(
                f"[agenteval] UI build missing at {_UI_DIST}. "
                "Run: cd web && npm install && npm run build",
                err=True,
            )
            raise typer.Exit(code=1)
        os.environ["AGENTEVAL_SERVE_UI"] = "1"
        os.environ["AGENTEVAL_UI_DIST"] = str(_UI_DIST)
        typer.echo(
            f"[agenteval] Web console: http://{host}:{port}/  (static from {_UI_DIST})",
            err=False,
        )
    elif with_ui is False:
        typer.echo("[agenteval] API only (--no-ui).", err=False)
    else:
        typer.echo(
            f"[agenteval] No UI at {_UI_DIST}. "
            "Build: cd web && npm install && npm run build — or use --no-ui for API-only.",
            err=False,
        )

    uvicorn.run(
        "agenteval.api.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
