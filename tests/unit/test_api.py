"""HTTP API façade (E3) over suite workflow."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult

SAMPLE_PRD = """# Refund Bot — Requirements

## Functional requirements

1. The agent must process refund requests when order id and reason are provided.
2. The agent must reject refunds without a valid order id.
"""


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "0")
    monkeypatch.delenv("AGENTEVAL_DATABASE_URL", raising=False)
    return TestClient(create_app())


def test_list_suites_empty(client: TestClient, tmp_path: Path) -> None:
    response = client.get("/v1/suites", params={"suite_root": str(tmp_path / "suites")})
    assert response.status_code == 200
    assert response.json()["suites"] == []


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "persistence" in body
    assert "sqlite_enabled" in body["persistence"]


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_run_suite_persists_to_sqlite(
    mock_runner_cls: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "1")
    db_file = tmp_path / "api.db"
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")
    client = TestClient(create_app())
    suite_root = str(tmp_path / "suites")

    client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "sql-agent",
            "endpoint_url": "http://127.0.0.1:9/chat",
            "suite_root": suite_root,
            "force_new_version": True,
        },
    )

    mock_runner_cls.return_value.run_pack.return_value = SuiteRunReport(
        agent_id="sql-agent",
        run_id="run-db",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=ObservationBundle(
                    test_id="t1",
                    user_prompt="x",
                    response_text="y",
                ),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    response = client.post(
        "/v1/suites/sql-agent/runs",
        json={"suite_root": suite_root},
    )
    assert response.status_code == 200

    import sqlite3

    conn = sqlite3.connect(tmp_path / "api.db")
    count = conn.execute("SELECT count(*) FROM assurance_runs").fetchone()[0]
    conn.close()
    assert count == 1


PRD_TWO_CAPS = """# Sync Agent

## Capabilities
- Issue Refund: Refund orders for customers
- Lookup Order: Find order status by id
"""

PRD_ONE_CAP = """# Sync Agent

## Capabilities
- Issue Refund: Refund orders for customers only
"""


def test_sync_suite_sqlite(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "1")
    db_file = tmp_path / "api-sync.db"
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")
    client = TestClient(create_app())
    suite_root = str(tmp_path / "suites")

    client.post(
        "/v1/suites",
        json={
            "requirements_text": PRD_TWO_CAPS,
            "agent_id": "sync-api",
            "endpoint_url": "http://127.0.0.1:9/chat",
            "suite_root": suite_root,
            "force_new_version": True,
            "max_tests": 12,
        },
    )

    sync = client.post(
        "/v1/suites/sync-api/sync",
        json={
            "requirements_text": PRD_ONE_CAP,
            "suite_root": suite_root,
            "max_tests": 12,
        },
    )
    assert sync.status_code == 200
    body = sync.json()
    assert body["new_version"] == 2
    lookup_cap_id = RequirementsIngestor.from_text(PRD_TWO_CAPS, agent_id="sync-api").capabilities[1].requirement_id()
    assert lookup_cap_id in body["removed_capabilities"]

    detail = client.get("/v1/suites/sync-api", params={"suite_root": suite_root})
    assert detail.json()["manifest"]["version"] == 2


def test_preview_suite(client: TestClient, tmp_path: Path) -> None:
    response = client.post(
        "/v1/suites/preview",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "refund-bot",
            "suite_root": str(tmp_path / "suites"),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["agent_card"]["id"] == "refund-bot"
    assert len(body["candidate_pool"]) >= 1
    assert len(body["optimized_pack"]["tests"]) >= 1


def test_init_and_latest_run(client: TestClient, tmp_path: Path) -> None:
    suite_root = str(tmp_path / "suites")
    init = client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "refund-api",
            "suite_root": suite_root,
            "force_new_version": True,
        },
    )
    assert init.status_code == 201
    assert init.json()["agent_id"] == "refund-api"

    listed = client.get("/v1/suites", params={"suite_root": suite_root})
    assert listed.json()["suites"][0]["agent_id"] == "refund-api"

    detail = client.get("/v1/suites/refund-api", params={"suite_root": suite_root})
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["optimized_pack"]["tests"]) >= 1
    assert body.get("coverage") is not None
    assert "axes" in body["coverage"]
    assert body.get("requirements_text", "") == SAMPLE_PRD

    latest = client.get(
        "/v1/suites/refund-api/runs/latest",
        params={"suite_root": suite_root},
    )
    assert latest.status_code == 404

    missing = client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "refund-api",
            "suite_root": suite_root,
        },
    )
    assert missing.status_code == 409


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_run_suite_endpoint(
    mock_runner_cls: MagicMock,
    client: TestClient,
    tmp_path: Path,
) -> None:
    suite_root = str(tmp_path / "suites")
    client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "run-me",
            "endpoint_url": "http://127.0.0.1:9/chat",
            "suite_root": suite_root,
            "force_new_version": True,
        },
    )

    mock_runner_cls.return_value.run_pack.return_value = SuiteRunReport(
        agent_id="run-me",
        run_id="run-1",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=ObservationBundle(
                    test_id="t1",
                    user_prompt="x",
                    response_text="y",
                ),
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )

    response = client.post(
        "/v1/suites/run-me/runs",
        json={"suite_root": suite_root},
    )
    assert response.status_code == 200
    assert response.json()["run_id"] == "run-1"
