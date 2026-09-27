"""API slice 3: requirements + criterion verdicts on run detail."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult

SAMPLE_PRD = """# Refund Bot

## Capabilities
- Process refund requests when order id and reason are provided.
- Reject refunds without a valid order id.
"""


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_requirements_and_criterion_verdicts_api(
    mock_runner_cls: MagicMock,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "1")
    db_file = tmp_path / "req-api.db"
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")
    client = TestClient(create_app())
    suite_root = str(tmp_path / "suites")

    init = client.post(
        "/v1/suites",
        json={
            "requirements_text": SAMPLE_PRD,
            "agent_id": "req-api-agent",
            "endpoint_url": "http://127.0.0.1:9/chat",
            "suite_root": suite_root,
            "force_new_version": True,
        },
    )
    assert init.status_code == 201
    detail = client.get("/v1/suites/req-api-agent", params={"suite_root": suite_root})
    pack_tests = detail.json()["optimized_pack"]["tests"]
    assert len(pack_tests) >= 1
    tid = pack_tests[0]["id"]

    req_resp = client.get(
        "/v1/suites/req-api-agent/requirements",
        params={"suite_root": suite_root},
    )
    assert req_resp.status_code == 200
    req_body = req_resp.json()
    assert len(req_body["requirements"]) >= 1
    assert req_body["requirements"][0]["criteria"]

    mock_runner_cls.return_value.run_pack.return_value = SuiteRunReport(
        agent_id="req-api-agent",
        run_id="run-req-api",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id=tid,
                verdict="PASS",
                observation=ObservationBundle(
                    test_id=tid,
                    user_prompt="refund please",
                    response_text="I cannot proceed without order id.",
                    http_status=200,
                    latency_ms=3.0,
                ),
                rationale="policy boundary",
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    run = client.post(
        "/v1/suites/req-api-agent/runs",
        json={"suite_root": suite_root},
    )
    assert run.status_code == 200
    run_body = run.json()
    assert len(run_body.get("criterion_verdicts", [])) >= 1
    assert run_body["criterion_verdicts"][0]["evidence_item_ids"]

    latest = client.get(
        "/v1/suites/req-api-agent/runs/latest",
        params={"suite_root": suite_root},
    )
    assert latest.status_code == 200
    assert len(latest.json().get("criterion_verdicts", [])) >= 1
