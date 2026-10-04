"""Integration tests for Authenticated Target Connection Profiles over HTTP API (Slice 13.3)."""

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.ingest.endpoint_probe import EndpointProbeResult
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult

SAMPLE_PRD = """# Secure Bot — Requirements
## Functional requirements
1. The agent must authenticate the caller and respond politely.
"""


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_file = tmp_path / "test_auth_api.db"
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.setenv("AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS", "1")
    return TestClient(create_app())


@patch("agenteval.api.app.EndpointProber")
def test_probe_endpoint_with_auth_profile(mock_prober_cls: MagicMock, client: TestClient) -> None:
    mock_prober = MagicMock()
    mock_prober.probe.return_value = EndpointProbeResult(
        endpoint_url="https://agent.corp/chat",
        reachable=True,
        http_status=200,
        latency_ms=45.2,
        inferred_tool_names=["kb_search"],
    )
    mock_prober_cls.return_value = mock_prober

    resp = client.post(
        "/v1/endpoints/probe",
        json={
            "endpoint_url": "https://agent.corp/chat",
            "headers": {"X-Tenant-Id": "tenant-123"},
            "auth_profile": {
                "endpoint_url": "https://agent.corp/chat",
                "auth_type": "bearer",
                "token_secret": "my-secret-token-value",
            },
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["reachable"] is True
    assert data["http_status"] == 200
    assert data["inferred_tool_names"] == ["kb_search"]

    # Verify headers and profile were passed to EndpointProber.probe
    mock_prober.probe.assert_called_once()
    call_kwargs = mock_prober.probe.call_args.kwargs
    assert call_kwargs["headers"] == {"X-Tenant-Id": "tenant-123"}
    assert call_kwargs["profile"] is not None
    assert call_kwargs["profile"].auth_type == "bearer"
    assert call_kwargs["profile"].token_secret == "my-secret-token-value"


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_run_suite_with_auth_headers_synchronous(
    mock_runner_cls: MagicMock, client: TestClient
) -> None:
    # 1. Initialize suite first
    init_resp = client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "auth-target-agent",
            "endpoint_url": "https://agent.corp/chat",
            "probe_endpoint": False,
        },
    )
    assert init_resp.status_code == 201

    # 2. Mock runner
    mock_runner = MagicMock()
    mock_runner.run_pack.return_value = SuiteRunReport(
        agent_id="auth-target-agent",
        run_id="run-sync-auth",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="T01",
                verdict="PASS",
                rationale="Authorized call succeeded",
                observation=ObservationBundle(
                    test_id="T01",
                    user_prompt="ping",
                    response_text="pong",
                    http_status=200,
                    latency_ms=12.0,
                ),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    mock_runner_cls.return_value = mock_runner

    # 3. Execute run with custom headers and auth profile
    run_resp = client.post(
        "/v1/suites/auth-target-agent/runs",
        json={
            "endpoint_url": "https://agent.corp/chat",
            "wait": True,
            "headers": {"X-Custom-Header": "custom-val"},
            "auth_profile": {
                "endpoint_url": "https://agent.corp/chat",
                "auth_type": "api_key",
                "header_name": "X-API-Key",
                "token_secret": "secret-key-456",
            },
        },
    )
    assert run_resp.status_code == 200
    report = run_resp.json()
    assert report["passed"] == 1
    assert report["run_id"] == "run-sync-auth"

    # Verify BlackboxRunner received connection profile and headers
    mock_runner_cls.assert_called_once()
    runner_kwargs = mock_runner_cls.call_args.kwargs
    assert runner_kwargs["headers"] == {"X-Custom-Header": "custom-val"}
    assert runner_kwargs["connection_profile"] is not None
    assert runner_kwargs["connection_profile"].auth_type == "api_key"
    assert runner_kwargs["connection_profile"].token_secret == "secret-key-456"


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_run_suite_with_auth_headers_async(mock_runner_cls: MagicMock, client: TestClient) -> None:
    # 1. Initialize suite first
    init_resp = client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "auth-async-agent",
            "endpoint_url": "https://agent.corp/chat",
            "probe_endpoint": False,
        },
    )
    assert init_resp.status_code == 201

    # 2. Mock runner
    mock_runner = MagicMock()
    mock_runner.run_pack.return_value = SuiteRunReport(
        agent_id="auth-async-agent",
        run_id="run-async-auth-job",
        suite_version=1,
        results=[],
        passed=0,
        failed=0,
        unverifiable=0,
    )
    mock_runner_cls.return_value = mock_runner

    # 3. Submit async run (wait=False by default)
    run_resp = client.post(
        "/v1/suites/auth-async-agent/runs",
        json={
            "endpoint_url": "https://agent.corp/chat",
            "wait": False,
            "headers": {"X-Async-Header": "async-val"},
            "auth_profile": {
                "endpoint_url": "https://agent.corp/chat",
                "auth_type": "bearer",
                "token_secret": "bearer-token-xyz",
            },
        },
    )
    assert run_resp.status_code == 202
    job_info = run_resp.json()
    assert "run_id" in job_info
    run_id = job_info["run_id"]

    # Poll until completed so background thread terminates cleanly
    for _ in range(50):
        st = client.get(f"/v1/suites/auth-async-agent/runs/{run_id}/status").json()
        if st["status"] in ("completed", "failed"):
            break
        time.sleep(0.02)
