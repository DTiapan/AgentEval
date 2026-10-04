"""Comprehensive test suite for structured logging and distributed correlation (Slice 8, DR-037)."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.core.logging import (
    add_gcp_severity,
    bind_contextvars,
    clear_contextvars,
    configure_logging,
    get_logger,
    unbind_contextvars,
)
from agenteval.evaluators.llm_judge import LLMJudgeResult, LLMJudgeScorer
from agenteval.planning.blackbox_runner import BlackboxRunner, JudgeMode
from agenteval.planning.models import (
    CandidateTest,
    ObservationBundle,
    PriorityTier,
    SuiteRunReport,
)
from agenteval.planning.models import (
    TestPack as PlanTestPack,
)
from agenteval.security.url_validator import UnsafeURLError, validate_endpoint_url
from agenteval.services.run_manager import RunJobManager


def _get_logged_json_lines(captured_stderr: str) -> list[dict[str, Any]]:
    """Parse JSON log entries from captured stderr output."""
    lines: list[dict[str, Any]] = []
    for line in captured_stderr.strip().splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return lines


class TestStructuredLoggingCore:
    """Tests for core structlog configuration, processors, and contextvars."""

    def test_add_gcp_severity_mapping(self) -> None:
        """Verify standard log levels map directly to GCP Cloud Logging severity values."""
        assert add_gcp_severity(None, "info", {"level": "info"})["severity"] == "INFO"
        assert add_gcp_severity(None, "warning", {"level": "warning"})["severity"] == "WARNING"
        assert add_gcp_severity(None, "warn", {"level": "warn"})["severity"] == "WARNING"
        assert add_gcp_severity(None, "error", {"level": "error"})["severity"] == "ERROR"
        assert add_gcp_severity(None, "critical", {"level": "critical"})["severity"] == "CRITICAL"
        assert add_gcp_severity(None, "debug", {"level": "debug"})["severity"] == "DEBUG"

    def test_configure_logging_json_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify configure_logging produces valid JSON with required metadata fields."""
        configure_logging(log_level="INFO", log_format="json", force=True)
        clear_contextvars()
        logger = get_logger("test.core")

        logger.info("system_boot", component="kernel", version="1.0.0")

        captured = capsys.readouterr()
        records = _get_logged_json_lines(captured.err)
        assert len(records) >= 1

        boot_record = next(r for r in records if r.get("event") == "system_boot")
        assert boot_record["component"] == "kernel"
        assert boot_record["version"] == "1.0.0"
        assert boot_record["level"] == "info"
        assert boot_record["severity"] == "INFO"
        assert "timestamp" in boot_record

    def test_contextvars_binding_and_unbinding(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify context variables propagate to log entries and unbind cleanly."""
        configure_logging(log_level="INFO", log_format="json", force=True)
        clear_contextvars()
        logger = get_logger("test.context")

        bind_contextvars(trace_id="trace-abc-123", tenant="org_42")
        logger.info("event_with_context")

        unbind_contextvars("tenant")
        logger.info("event_after_unbind")

        clear_contextvars()
        logger.info("event_after_clear")

        captured = capsys.readouterr()
        records = _get_logged_json_lines(captured.err)

        rec1 = next(r for r in records if r.get("event") == "event_with_context")
        assert rec1["trace_id"] == "trace-abc-123"
        assert rec1["tenant"] == "org_42"

        rec2 = next(r for r in records if r.get("event") == "event_after_unbind")
        assert rec2["trace_id"] == "trace-abc-123"
        assert "tenant" not in rec2

        rec3 = next(r for r in records if r.get("event") == "event_after_clear")
        assert "trace_id" not in rec3
        assert "tenant" not in rec3


class TestRequestIdMiddleware:
    """Tests for FastAPI RequestIdMiddleware correlation headers and access logging."""

    def test_request_id_generated_when_missing(self) -> None:
        """Verify missing X-Request-ID generates a req_ prefixed UUID and returns in header."""
        app = create_app()
        client = TestClient(app)

        response = client.get("/health")
        assert response.status_code == 200
        req_id = response.headers.get("X-Request-ID")
        assert req_id is not None
        assert req_id.startswith("req_")

    def test_request_id_preserved_when_supplied(self) -> None:
        """Verify client-supplied X-Request-ID is preserved across processing and response."""
        app = create_app()
        client = TestClient(app)

        client_id = "client-trace-987654321"
        response = client.get("/health", headers={"X-Request-ID": client_id})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == client_id

    def test_request_id_emitted_in_access_logs(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify RequestIdMiddleware logs http_request_completed with correlated request_id."""
        configure_logging(log_level="INFO", log_format="json", force=True)
        app = create_app()
        client = TestClient(app)

        client_id = "client-req-555"
        client.get("/health", headers={"X-Request-ID": client_id})

        captured = capsys.readouterr()
        records = _get_logged_json_lines(captured.err)

        access_log = next(
            (r for r in records if r.get("event") == "http_request_completed" and r.get("request_id") == client_id),
            None,
        )
        assert access_log is not None
        assert access_log["method"] == "GET"
        assert access_log["path"] == "/health"
        assert access_log["status_code"] == 200
        assert "duration_ms" in access_log


class TestSecurityAndEvaluatorLogging:
    """Tests for SSRF block auditing and LLM judge fallback provenance attribution."""

    def test_ssrf_blocked_structured_log(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify SSRF validation violations emit structured ssrf_blocked warning with metadata."""
        configure_logging(log_level="INFO", log_format="json", force=True)
        clear_contextvars()

        with pytest.raises(UnsafeURLError):
            validate_endpoint_url("http://169.254.169.254/latest/meta-data")

        captured = capsys.readouterr()
        records = _get_logged_json_lines(captured.err)

        ssrf_record = next((r for r in records if r.get("event") == "ssrf_blocked"), None)
        assert ssrf_record is not None
        assert ssrf_record["severity"] == "WARNING"
        assert ssrf_record["hostname"] == "169.254.169.254"
        assert "169.254.169.254" in ssrf_record["url"]

    def test_llm_judge_fallback_triggered_log(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify LLMJudgeScorer logs warning and records fallback provenance on model failure."""
        configure_logging(log_level="INFO", log_format="json", force=True)
        clear_contextvars()

        scorer = LLMJudgeScorer(api_key="sk-test-key", force_offline=False)
        with patch.object(
            scorer,
            "_evaluate_with_litellm",
            side_effect=RuntimeError("LiteLLM connection timeout"),
        ):
            res = scorer.evaluate(
                user_prompt="Transfer $50",
                expected_behavior="Confirm transfer details before executing",
                response_text="Transfer executed immediately.",
                category="financial_safety",
            )

        assert res.evaluator_provenance == "heuristic-fallback"

        captured = capsys.readouterr()
        records = _get_logged_json_lines(captured.err)

        fallback_record = next(
            (r for r in records if r.get("event") == "llm_judge_fallback_triggered"),
            None,
        )
        assert fallback_record is not None
        assert fallback_record["severity"] == "WARNING"
        assert fallback_record["error_type"] == "RuntimeError"
        assert "LiteLLM connection timeout" in fallback_record["error"]
        assert fallback_record["evaluator_provenance"] == "heuristic-fallback"

    def test_llm_judge_evaluated_success_log(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify successful LLM judge evaluations emit llm_judge_evaluated structured info log."""
        configure_logging(log_level="INFO", log_format="json", force=True)
        clear_contextvars()

        scorer = LLMJudgeScorer(api_key="sk-test-key", force_offline=False)
        mock_result = LLMJudgeResult(
            verdict="PASS",
            score=0.95,
            passed=True,
            rationale="Agent correctly adhered to policy rubric.",
            evaluator_provenance="litellm-judge",
            model_used="openrouter/deepseek/deepseek-v4-flash-0731",
        )
        with patch.object(scorer, "_evaluate_with_litellm", return_value=mock_result):
            res = scorer.evaluate(
                user_prompt="What is your return policy?",
                expected_behavior="Explain 30-day return policy clearly",
                response_text="You can return any item within 30 days for a full refund.",
                category="policy",
            )

        assert res.evaluator_provenance == "litellm-judge"

        captured = capsys.readouterr()
        records = _get_logged_json_lines(captured.err)

        eval_record = next(
            (r for r in records if r.get("event") == "llm_judge_evaluated"),
            None,
        )
        assert eval_record is not None
        assert eval_record["severity"] == "INFO"
        assert eval_record["score"] == 0.95
        assert eval_record["passed"] is True
        assert eval_record["evaluator_provenance"] == "litellm-judge"


class TestRunnerAndJobManagerLogging:
    """Tests for BlackboxRunner and RunJobManager lifecycle structured events."""

    def test_blackbox_runner_lifecycle_events(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify BlackboxRunner emits suite_run_started, test_completed, and suite_run_finished."""
        configure_logging(log_level="INFO", log_format="json", force=True)
        clear_contextvars()

        test = CandidateTest(
            id="TEST-01",
            capability_id="cap_balance",
            persona_id="retail_user",
            name="Balance inquiry",
            user_prompt="What is my checking balance?",
            expected_behavior="Return formatted dollar balance.",
            priority_tier=PriorityTier.P0_CRITICAL,
        )
        pack = PlanTestPack(
            agent_id="banking_agent",
            version=1,
            tests=[test],
            candidate_count=1,
        )

        mock_obs = ObservationBundle(
            test_id=test.id,
            user_prompt=test.user_prompt,
            response_text="Your balance is $4,250.00.",
            http_status=200,
            latency_ms=45.2,
            raw_json={"reply": "Your balance is $4,250.00."},
        )

        runner = BlackboxRunner(
            endpoint_url="https://api.example.com/agent",
            judge_mode=JudgeMode.DETERMINISTIC_ONLY,
        )

        with patch.object(runner, "_invoke", return_value=mock_obs):
            report = runner.run_pack(pack, run_id="run-test-logging-01")

        assert report.run_id == "run-test-logging-01"

        captured = capsys.readouterr()
        records = _get_logged_json_lines(captured.err)

        started = next((r for r in records if r.get("event") == "suite_run_started"), None)
        assert started is not None
        assert started["run_id"] == "run-test-logging-01"
        assert started["agent_id"] == "banking_agent"
        assert started["test_count"] == 1

        completed = next((r for r in records if r.get("event") == "test_completed"), None)
        assert completed is not None
        assert completed["run_id"] == "run-test-logging-01"
        assert completed["test_id"] == "TEST-01"
        assert "verdict" in completed
        assert completed["http_status"] == 200

        finished = next((r for r in records if r.get("event") == "suite_run_finished"), None)
        assert finished is not None
        assert finished["run_id"] == "run-test-logging-01"
        assert finished["agent_id"] == "banking_agent"
        assert finished["total"] == 1

    def test_run_job_manager_lifecycle_events(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Verify RunJobManager emits job_submitted, job_started, and job_completed events."""
        configure_logging(log_level="INFO", log_format="json", force=True)
        clear_contextvars()

        manager = RunJobManager(max_concurrent_jobs=1)
        mock_workflow = MagicMock()
        mock_report = SuiteRunReport(
            agent_id="test_agent",
            run_id="run-dummy",
            suite_version=1,
            results=[],
            passed=0,
            failed=0,
            unverifiable=0,
        )
        mock_workflow.run_suite.return_value = mock_report

        job = manager.submit_run(
            agent_id="test_agent",
            workflow=mock_workflow,
            judge_mode="hybrid",
        )

        # Wait for thread pool to finish
        manager._executor.shutdown(wait=True)

        captured = capsys.readouterr()
        records = _get_logged_json_lines(captured.err)

        submitted = next(
            (r for r in records if r.get("event") == "job_submitted" and r.get("run_id") == job.run_id),
            None,
        )
        assert submitted is not None
        assert submitted["agent_id"] == "test_agent"
        assert submitted["judge_mode"] == "hybrid"

        started = next(
            (r for r in records if r.get("event") == "job_started" and r.get("run_id") == job.run_id),
            None,
        )
        assert started is not None

        completed = next(
            (r for r in records if r.get("event") == "job_completed" and r.get("run_id") == job.run_id),
            None,
        )
        assert completed is not None
