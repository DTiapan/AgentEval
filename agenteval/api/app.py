"""FastAPI application exposing suite preview, init, and run (E3)."""

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from agenteval import __version__
from agenteval.api.schemas import PrdBootstrapRequest, SuiteInitRequest, SuiteRunRequest
from agenteval.planning.suite_store import SuiteExistsError
from agenteval.services.suite_workflow import SuiteWorkflow


def create_app() -> FastAPI:
    app = FastAPI(
        title="AgentEval API",
        version=__version__,
        description="HTTP façade over black-box suite services (DR-012).",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.post("/v1/suites/preview")
    def preview_suite(body: PrdBootstrapRequest) -> JSONResponse:
        workflow = SuiteWorkflow(suite_root=body.suite_root, max_tests=body.max_tests)
        try:
            result = workflow.preview_from_prd_text(
                body.requirements_text,
                agent_id=body.agent_id,
                endpoint_url=body.endpoint_url,
                probe_endpoint=body.probe_endpoint,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return JSONResponse(content=result.model_dump(mode="json"))

    @app.post("/v1/suites")
    def init_suite(body: SuiteInitRequest) -> JSONResponse:
        workflow = SuiteWorkflow(suite_root=body.suite_root, max_tests=body.max_tests)
        try:
            result = workflow.init_from_prd_text(
                body.requirements_text,
                agent_id=body.agent_id,
                endpoint_url=body.endpoint_url,
                probe_endpoint=body.probe_endpoint,
                force_new_version=body.force_new_version,
            )
        except SuiteExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return JSONResponse(content=result.model_dump(mode="json"), status_code=201)

    @app.post("/v1/suites/{agent_id}/runs")
    def run_suite(agent_id: str, body: SuiteRunRequest) -> JSONResponse:
        workflow = SuiteWorkflow(suite_root=body.suite_root)
        try:
            report = workflow.run_suite(agent_id, endpoint_url=body.endpoint_url)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"No suite for agent '{agent_id}'. POST /v1/suites first.",
            ) from None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return JSONResponse(content=report.model_dump(mode="json"))

    @app.get("/v1/suites/{agent_id}/runs/latest")
    def latest_run(agent_id: str, suite_root: str = ".agenteval/suites") -> JSONResponse:
        workflow = SuiteWorkflow(suite_root=suite_root)
        report = workflow.latest_run(agent_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"No runs for agent '{agent_id}'.")
        return JSONResponse(content=report.model_dump(mode="json"))

    return app
