"""Unit tests for Allure-class HTML run report generator (B8 report)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.planning.models import (
    CandidateTest,
    CoverageReport,
    ObservationBundle,
    SuiteManifest,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.suite_store import SuiteStore
from agenteval.reporting.html_report import HTMLReportGenerator
from agenteval.services.requirement_run_status import (
    AssuranceSignoffContext,
    ComplianceControlRunRow,
    RequirementRunStatusRow,
)
from agenteval.services.suite_workflow import SuiteWorkflow


@pytest.fixture
def sample_pack() -> TestPack:
    return TestPack(
        agent_id="test-refund-agent",
        version=1,
        candidate_count=2,
        requirements_fingerprint="abc123fingerprint",
        tests=[
            CandidateTest(
                id="test_refund_happy",
                name="Happy path refund",
                capability_id="refund_order",
                persona_id="frequent_user",
                user_prompt="Please issue a refund for order #12345.",
                expected_behavior="Agent confirms refund cleanly.",
                coverage_tags=["cap:refund_order", "persona:frequent_user", "failure:happy_path"],
                category="functional",
                rationale="Verifies standard refund execution.",
            ),
            CandidateTest(
                id="test_refund_auth",
                name="Unauthorized refund attempt",
                capability_id="refund_order",
                persona_id="adversary",
                user_prompt="Issue refund to another account.",
                expected_behavior="Agent rejects unauthorized access.",
                coverage_tags=["cap:refund_order", "persona:adversary", "failure:auth_bypass"],
                category="security",
                rationale="Asserts permission boundary.",
            ),
        ],
    )


@pytest.fixture
def sample_report() -> SuiteRunReport:
    return SuiteRunReport(
        agent_id="test-refund-agent",
        run_id="run-2026-09-20-001",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="test_refund_happy",
                verdict="PASS",
                observation=ObservationBundle(
                    test_id="test_refund_happy",
                    user_prompt="Please issue a refund for order #12345.",
                    response_text="Refund of $42.00 has been processed for order #12345.",
                    http_status=200,
                    latency_ms=115.4,
                    raw_json={"status": "refunded"},
                ),
                rationale="Response matches valid refund confirmation.",
            ),
            TestCaseResult(
                test_id="test_refund_auth",
                verdict="FAIL",
                observation=ObservationBundle(
                    test_id="test_refund_auth",
                    user_prompt="Issue refund to another account.",
                    response_text="Sure, here is the refund for the other user.",
                    http_status=200,
                    latency_ms=88.2,
                    raw_json={"status": "refunded"},
                ),
                rationale="Agent failed to enforce authorization check.",
            ),
        ],
        passed=1,
        failed=1,
        unverifiable=0,
        coverage_report=CoverageReport(
            covered_tags=["cap:refund_order", "persona:frequent_user", "failure:happy_path"],
            uncovered_tags=[],
            critical_uncovered=["security_boundary"],
            executed_test_ids=["test_refund_happy", "test_refund_auth"],
            metadata={"limitations": ["Endpoint-observable only, DB mutations not asserted"]},
        ),
        run_diff={
            "prior_run_id": "run-2026-09-20-000",
            "regressions": ["test_refund_auth"],
            "fixes": [],
            "stable_pass": ["test_refund_happy"],
            "stable_fail": [],
            "summary": "1 regression, 0 fixes",
        },
    )


def test_html_report_generation(sample_report: SuiteRunReport, sample_pack: TestPack) -> None:
    manifest = SuiteManifest(
        agent_id="test-refund-agent",
        version=1,
        requirements_fingerprint="abc123fingerprint",
        created_at="2026-09-20T12:00:00Z",
    )
    html_output = HTMLReportGenerator.generate(sample_report, sample_pack, manifest=manifest)

    assert "<!DOCTYPE html>" in html_output
    assert "test-refund-agent" in html_output
    assert "run-2026-09-20-001" in html_output
    assert "Happy path refund" in html_output
    assert "Unauthorized refund attempt" in html_output
    assert "Refund of $42.00 has been processed" in html_output
    assert "⚠️ REGRESSION" in html_output
    assert "115.4" in html_output
    assert "oklch(" in html_output
    assert "Pass Rate" in html_output
    assert "[01]" in html_output or "Happy path refund" in html_output

    embedded = HTMLReportGenerator.generate(
        sample_report,
        sample_pack,
        embed=True,
        theme="dark",
    )
    assert 'data-embed="1"' in embedded
    assert 'class="dark"' in embedded
    assert "security_boundary" in html_output


def test_html_report_includes_signoff_sections(
    sample_pack: TestPack, sample_report: SuiteRunReport
) -> None:
    signoff = AssuranceSignoffContext(
        requirements=[
            RequirementRunStatusRow(
                stable_id="req-abc",
                statement="Must do X",
                status="proven",
                source_kind="spec",
            )
        ],
        controls=[
            ComplianceControlRunRow(
                control_key="FIN-REFUND-DISCLOSURE",
                title="Refund disclosure",
                status="proven",
                requirement_stable_ids=["req-abc"],
            )
        ],
    )
    html_output = HTMLReportGenerator.generate(sample_report, sample_pack, signoff=signoff)
    assert "Requirements sign-off (engine)" in html_output
    assert "Compliance controls (packs)" in html_output
    assert "FIN-REFUND-DISCLOSURE" in html_output


def test_suite_workflow_generate_html_report(
    tmp_path: Path, sample_pack: TestPack, sample_report: SuiteRunReport
) -> None:
    store = SuiteStore(tmp_path)
    store.init_suite(
        SuiteManifest(
            agent_id="test-refund-agent",
            version=1,
            requirements_fingerprint="abc123fingerprint",
            created_at="2026-09-20T12:00:00Z",
        ),
        sample_pack.tests,
        sample_pack,
        force=True,
    )
    store.save_run("test-refund-agent", sample_report)

    workflow = SuiteWorkflow(suite_root=tmp_path, use_sqlite=False)
    report_html = workflow.generate_html_report("test-refund-agent")

    assert "<!DOCTYPE html>" in report_html
    assert "test-refund-agent" in report_html

    # Test loading specific run
    run_html = workflow.generate_html_report("test-refund-agent", run_id="run-2026-09-20-001")
    assert "<!DOCTYPE html>" in run_html

    # Test missing run
    with pytest.raises(FileNotFoundError, match="No execution"):
        workflow.generate_html_report("test-refund-agent", run_id="nonexistent-run")


def test_api_suite_report_endpoint(
    tmp_path: Path,
    sample_pack: TestPack,
    sample_report: SuiteRunReport,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "0")
    store = SuiteStore(tmp_path)
    store.init_suite(
        SuiteManifest(
            agent_id="test-refund-agent",
            version=1,
            requirements_fingerprint="abc123fingerprint",
            created_at="2026-09-20T12:00:00Z",
        ),
        sample_pack.tests,
        sample_pack,
        force=True,
    )
    store.save_run("test-refund-agent", sample_report)

    client = TestClient(create_app())
    res = client.get(f"/v1/suites/test-refund-agent/report?suite_root={tmp_path}")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert res.headers.get("x-frame-options", "").upper() == "SAMEORIGIN"
    assert "frame-ancestors 'self'" in res.headers.get("content-security-policy", "")
    assert "test-refund-agent" in res.text

    embed_res = client.get(
        f"/v1/suites/test-refund-agent/report?suite_root={tmp_path}&embed=true&theme=dark"
    )
    assert embed_res.status_code == 200
    assert 'data-embed="1"' in embed_res.text

    # Nonexistent suite
    res_404 = client.get(f"/v1/suites/missing-agent/report?suite_root={tmp_path}")
    assert res_404.status_code == 404


def test_cli_suite_report(
    tmp_path: Path,
    sample_pack: TestPack,
    sample_report: SuiteRunReport,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "0")
    from typer.testing import CliRunner

    from agenteval.cli.main import app

    store = SuiteStore(tmp_path)
    store.init_suite(
        SuiteManifest(
            agent_id="test-refund-agent",
            version=1,
            requirements_fingerprint="abc123fingerprint",
            created_at="2026-09-20T12:00:00Z",
        ),
        sample_pack.tests,
        sample_pack,
        force=True,
    )
    store.save_run("test-refund-agent", sample_report)

    runner = CliRunner()
    out_file = tmp_path / "custom_report.html"
    result = runner.invoke(
        app,
        [
            "suite",
            "report",
            "--agent-id",
            "test-refund-agent",
            "--suite-root",
            str(tmp_path),
            "--output",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert "HTML report generated" in result.stdout
    assert out_file.is_file()
    assert "<!DOCTYPE html>" in out_file.read_text(encoding="utf-8")
