"""Unit tests for FastAPI async background runs and status endpoints (Slice 6)."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult

SAMPLE_PRD = """# Async Agent
## Capabilities
- Search Docs: Search customer documentation
"""


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "1")
    db_file = tmp_path / "async-test.db"
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")
    app = create_app()
    return TestClient(app)


def test_run_suite_nonexistent_suite_returns_404(client: TestClient, tmp_path: Path) -> None:
    resp = client.post(
        "/v1/suites/ghost-agent/runs",
        json={"suite_root": str(tmp_path / "suites")},
    )
    assert resp.status_code == 404
    assert "No suite for agent 'ghost-agent'" in resp.json()["detail"]


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_async_run_polling_flow(
    mock_runner_cls: MagicMock,
    client: TestClient,
    tmp_path: Path,
) -> None:
    suite_root = str(tmp_path / "suites")
    # Initialize a suite
    init_resp = client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "async-agent",
            "endpoint_url": "http://127.0.0.1:9000/chat",
            "suite_root": suite_root,
            "force_new_version": True,
        },
    )
    assert init_resp.status_code == 201

    fake_report = SuiteRunReport(
        agent_id="async-agent",
        run_id="run-async-1",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=ObservationBundle(
                    test_id="t1",
                    user_prompt="search for help",
                    response_text="Found 2 articles",
                    http_status=200,
                    latency_ms=10.0,
                ),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )

    def slow_run_pack(*args: object, **kwargs: object) -> SuiteRunReport:
        on_progress = kwargs.get("on_progress")
        if callable(on_progress):
            on_progress(1, 1)
        time.sleep(0.05)
        return fake_report

    mock_runner_cls.return_value.run_pack.side_effect = slow_run_pack

    # Submit async run (wait=False by default)
    submit_resp = client.post(
        "/v1/suites/async-agent/runs",
        json={"suite_root": suite_root},
    )
    assert submit_resp.status_code == 202
    job_info = submit_resp.json()
    run_id = job_info["run_id"]
    assert job_info["agent_id"] == "async-agent"
    assert job_info["status"] in ("pending", "running")

    # Poll status endpoint
    for _ in range(50):
        status_resp = client.get(
            f"/v1/suites/async-agent/runs/{run_id}/status",
            params={"suite_root": suite_root},
        )
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        if status_data["status"] == "completed":
            break
        time.sleep(0.02)

    final_status = client.get(
        f"/v1/suites/async-agent/runs/{run_id}/status",
        params={"suite_root": suite_root},
    ).json()
    assert final_status["status"] == "completed", f"Job failed with error: {final_status.get('error')}"
    assert final_status["progress"]["completed"] == 1
    assert final_status["progress"]["percent"] == 100.0

    # Fetch completed run report via GET /runs/{run_id}
    report_resp = client.get(
        f"/v1/suites/async-agent/runs/{run_id}",
        params={"suite_root": suite_root},
    )
    assert report_resp.status_code == 200
    report_data = report_resp.json()
    assert report_data["agent_id"] == "async-agent"
    assert report_data["passed"] == 1


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_sync_run_fallback(
    mock_runner_cls: MagicMock,
    client: TestClient,
    tmp_path: Path,
) -> None:
    suite_root = str(tmp_path / "suites")
    client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "sync-fallback-agent",
            "endpoint_url": "http://127.0.0.1:9000/chat",
            "suite_root": suite_root,
            "force_new_version": True,
        },
    )

    mock_runner_cls.return_value.run_pack.return_value = SuiteRunReport(
        agent_id="sync-fallback-agent",
        run_id="run-sync-1",
        suite_version=1,
        results=[],
        passed=0,
        failed=0,
        unverifiable=0,
    )

    resp = client.post(
        "/v1/suites/sync-fallback-agent/runs",
        json={"suite_root": suite_root, "wait": True},
    )
    assert resp.status_code == 200
    assert resp.json()["agent_id"] == "sync-fallback-agent"
