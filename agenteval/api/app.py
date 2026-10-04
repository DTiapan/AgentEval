"""FastAPI application exposing suite preview, init, and run (E3+E4)."""

import os
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from agenteval import __version__
from agenteval.api.schemas import (
    EndpointProbeRequest,
    PrdBootstrapRequest,
    SuiteGapExtendRequest,
    SuiteInitRequest,
    SuiteRunRequest,
    SuiteSyncRequest,
)
from agenteval.ingest.endpoint_probe import EndpointProber
from agenteval.planning.models import PriorityTier
from agenteval.planning.suite_store import SuiteExistsError
from agenteval.services.run_manager import get_run_job_manager
from agenteval.services.workflow_factory import create_suite_workflow, persistence_status

_REPO_UI_DIST = Path(__file__).resolve().parents[2] / "web" / "dist"


def get_allowed_cors_origins() -> list[str]:
    """Resolve allowed CORS origins from environment, defaulting to local dev frontends."""
    raw = os.environ.get("AGENTEVAL_CORS_ORIGINS", "").strip()
    if not raw:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8766",
            "http://127.0.0.1:8766",
        ]
    if raw == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgentEval API",
        version=__version__,
        description="HTTP façade over black-box suite services (DR-012).",
    )

    origins = get_allowed_cors_origins()
    is_wildcard = origins == ["*"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=not is_wildcard,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept", "Origin"],
    )

    @app.get("/health")
    def health() -> dict[str, str | bool | dict[str, str | bool | None]]:
        return {
            "status": "ok",
            "version": __version__,
            "persistence": persistence_status(),
        }

    @app.get("/v1/packs")
    def list_domain_packs(suite_root: str = ".agenteval/suites") -> JSONResponse:
        workflow = create_suite_workflow(suite_root=suite_root)
        result = workflow.list_domain_packs()
        return JSONResponse(content=result.model_dump(mode="json"))

    @app.get("/v1/suites")
    def list_suites(suite_root: str = ".agenteval/suites") -> JSONResponse:
        workflow = create_suite_workflow(suite_root=suite_root)
        items = workflow.list_suites()
        return JSONResponse(content={"suites": [item.model_dump(mode="json") for item in items]})

    @app.get("/v1/suites/{agent_id}/requirements")
    def get_suite_requirements(
        agent_id: str, suite_root: str = ".agenteval/suites"
    ) -> JSONResponse:
        workflow = create_suite_workflow(suite_root=suite_root)
        try:
            result = workflow.get_requirements(agent_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No suite for agent '{agent_id}'.",
            ) from None
        return JSONResponse(content=result.model_dump(mode="json"))

    @app.get("/v1/suites/{agent_id}")
    def get_suite(agent_id: str, suite_root: str = ".agenteval/suites") -> JSONResponse:
        workflow = create_suite_workflow(suite_root=suite_root)
        try:
            detail = workflow.get_suite(agent_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No suite for agent '{agent_id}'.",
            ) from None
        return JSONResponse(content=detail.model_dump(mode="json"))

    @app.delete("/v1/suites/{agent_id}")
    def delete_suite(agent_id: str, suite_root: str = ".agenteval/suites") -> JSONResponse:
        workflow = create_suite_workflow(suite_root=suite_root)
        try:
            workflow.delete_suite(agent_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No suite for agent '{agent_id}'.",
            ) from None
        return JSONResponse(content={"deleted": True, "agent_id": agent_id})

    @app.post("/v1/endpoints/probe")
    def probe_agent_endpoint(body: EndpointProbeRequest) -> JSONResponse:
        """Probe target agent from the engine (avoids browser CORS to user endpoints)."""
        result = EndpointProber().probe(body.endpoint_url)
        if result.error and "SSRF protection" in result.error:
            raise HTTPException(status_code=422, detail=result.error)
        return JSONResponse(content=result.model_dump(mode="json"))

    @app.post("/v1/suites/preview")
    def preview_suite(body: PrdBootstrapRequest) -> JSONResponse:
        workflow = create_suite_workflow(suite_root=body.suite_root, max_tests=body.max_tests)
        tier = PriorityTier(body.target_tier) if body.target_tier else None
        try:
            result = workflow.preview_from_prd_text(
                body.requirements_text,
                agent_id=body.agent_id,
                endpoint_url=body.endpoint_url,
                probe_endpoint=body.probe_endpoint,
                max_tier=tier,
                selected_test_ids=body.selected_test_ids,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return JSONResponse(content=result.model_dump(mode="json"))

    @app.post("/v1/suites")
    def init_suite(body: SuiteInitRequest) -> JSONResponse:
        workflow = create_suite_workflow(suite_root=body.suite_root, max_tests=body.max_tests)
        tier = PriorityTier(body.target_tier) if body.target_tier else None
        try:
            result = workflow.init_from_prd_text(
                body.requirements_text,
                agent_id=body.agent_id,
                endpoint_url=body.endpoint_url,
                probe_endpoint=body.probe_endpoint,
                force_new_version=body.force_new_version,
                enabled_domain_packs=body.enabled_domain_packs or None,
                max_tier=tier,
                selected_test_ids=body.selected_test_ids,
            )
        except SuiteExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return JSONResponse(content=result.model_dump(mode="json"), status_code=201)

    @app.post("/v1/suites/{agent_id}/extend-gaps")
    def extend_suite_gaps(agent_id: str, body: SuiteGapExtendRequest) -> JSONResponse:
        workflow = create_suite_workflow(suite_root=body.suite_root)
        try:
            result = workflow.extend_gaps_from_latest_run(
                agent_id,
                max_add=body.max_add,
                run_id=body.run_id,
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No suite or run for agent '{agent_id}'. Freeze suite and run assurance first.",
            ) from None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return JSONResponse(content=result.model_dump(mode="json"))

    @app.post("/v1/suites/{agent_id}/sync")
    def sync_suite(agent_id: str, body: SuiteSyncRequest) -> JSONResponse:
        workflow = create_suite_workflow(suite_root=body.suite_root, max_tests=body.max_tests)
        try:
            result = workflow.sync_from_prd_text(
                agent_id,
                body.requirements_text,
                endpoint_url=body.endpoint_url,
                probe_endpoint=body.probe_endpoint,
                enabled_domain_packs=body.enabled_domain_packs or None,
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No suite for agent '{agent_id}'. POST /v1/suites first.",
            ) from None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return JSONResponse(content=result.model_dump(mode="json"))

    @app.post("/v1/suites/{agent_id}/runs")
    def run_suite(agent_id: str, body: SuiteRunRequest) -> JSONResponse:
        workflow = create_suite_workflow(suite_root=body.suite_root)
        try:
            workflow.get_suite(agent_id)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No suite for agent '{agent_id}'. POST /v1/suites first.",
            ) from None

        if body.wait:
            try:
                report = workflow.run_suite(
                    agent_id,
                    endpoint_url=body.endpoint_url,
                    audit_log_db_path=body.audit_log_db_path,
                    judge_mode=body.judge_mode,
                    max_concurrency=body.max_concurrency,
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from None
            return JSONResponse(content=report.model_dump(mode="json"))

        manager = get_run_job_manager()
        job = manager.submit_run(
            agent_id,
            workflow,
            endpoint_url=body.endpoint_url,
            audit_log_db_path=body.audit_log_db_path,
            judge_mode=body.judge_mode,
            max_concurrency=body.max_concurrency,
        )
        return JSONResponse(
            status_code=202,
            content=job.model_dump(mode="json"),
        )

    @app.get("/v1/suites/{agent_id}/runs/latest")
    def latest_run(agent_id: str, suite_root: str = ".agenteval/suites") -> JSONResponse:
        workflow = create_suite_workflow(suite_root=suite_root)
        report = workflow.latest_run(agent_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"No runs for agent '{agent_id}'.")
        return JSONResponse(content=report.model_dump(mode="json"))

    @app.get("/v1/suites/{agent_id}/runs/{run_id}/status")
    def run_status(
        agent_id: str,
        run_id: str,
        suite_root: str = ".agenteval/suites",
    ) -> JSONResponse:
        manager = get_run_job_manager()
        job = manager.get_job(run_id)
        if job is not None:
            return JSONResponse(content=job.model_dump(mode="json"))
        workflow = create_suite_workflow(suite_root=suite_root)
        repo = workflow._repository()
        run_record = repo.get_run_record(run_id) if repo is not None else None
        report = workflow.get_run(agent_id, run_id)
        if report is not None or run_record is not None:
            now_iso = datetime.now(UTC).isoformat()
            status = "completed"
            error = None
            started_at = now_iso
            finished_at = now_iso
            if run_record is not None:
                status = str(run_record.get("status") or "completed")
                error = run_record.get("error_message")
                started_at = str(run_record.get("started_at") or now_iso)
                finished_at = str(run_record.get("finished_at") or now_iso)

            completed_count = len(report.results) if report else 0
            total_count = completed_count
            try:
                pack = workflow._load_pack(workflow._store(), agent_id)
                total_count = max(len(pack.tests), completed_count)
            except Exception:
                pass

            percent = 100.0 if status == "completed" else (
                (completed_count / total_count * 100.0) if total_count > 0 else 0.0
            )

            return JSONResponse(
                content={
                    "run_id": run_id,
                    "agent_id": agent_id,
                    "status": status,
                    "created_at": started_at,
                    "started_at": started_at,
                    "completed_at": finished_at if status in ("completed", "failed") else None,
                    "progress": {
                        "completed": completed_count,
                        "total": total_count,
                        "percent": round(percent, 1),
                    },
                    "error": error,
                }
            )
        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found for agent '{agent_id}'.",
        )

    @app.get("/v1/suites/{agent_id}/runs/{run_id}")
    def get_run(
        agent_id: str,
        run_id: str,
        suite_root: str = ".agenteval/suites",
    ) -> JSONResponse:
        manager = get_run_job_manager()
        job = manager.get_job(run_id)
        if job is not None:
            if job.status in ("pending", "running"):
                return JSONResponse(
                    status_code=202,
                    content=job.model_dump(mode="json"),
                )
            if job.status == "failed":
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": job.error or "Run execution failed",
                        "job": job.model_dump(mode="json"),
                    },
                )
            report = manager.get_report(run_id)
            if report is not None:
                return JSONResponse(content=report.model_dump(mode="json"))

        workflow = create_suite_workflow(suite_root=suite_root)
        report = workflow.get_run(agent_id, run_id)
        if report is not None:
            return JSONResponse(content=report.model_dump(mode="json"))

        raise HTTPException(
            status_code=404,
            detail=f"Run '{run_id}' not found for agent '{agent_id}'.",
        )

    @app.get("/v1/suites/{agent_id}/report", response_class=HTMLResponse)
    def suite_report(
        agent_id: str,
        run_id: str | None = None,
        suite_root: str = ".agenteval/suites",
        embed: bool = False,
        theme: str = "auto",
    ) -> HTMLResponse:
        workflow = create_suite_workflow(suite_root=suite_root)
        try:
            html_content = workflow.generate_html_report(
                agent_id,
                run_id=run_id,
                embed=embed,
                theme=theme,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from None
        return HTMLResponse(
            content=html_content,
            headers={
                # Allow in-console iframe embed on same origin (M4).
                "X-Frame-Options": "SAMEORIGIN",
                "Content-Security-Policy": "frame-ancestors 'self'",
            },
        )

    ui_dist = Path(os.environ.get("AGENTEVAL_UI_DIST", str(_REPO_UI_DIST)))
    if os.environ.get("AGENTEVAL_SERVE_UI", "0") == "1" and ui_dist.is_dir():
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="agenteval-ui")

    return app
