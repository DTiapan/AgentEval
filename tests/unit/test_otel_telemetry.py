"""Unit tests for OpenTelemetry distributed tracing and context propagation (Slice 11, DR-040)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.core.logging import add_otel_trace_context
from agenteval.core.manifest import AgentCapability, AgentCard, AgentInvariants
from agenteval.core.telemetry import (
    configure_telemetry,
    extract_trace_context,
    get_current_span_id,
    get_current_trace_id,
    get_in_memory_spans,
    inject_trace_context,
    reset_telemetry,
    start_span,
    telemetry_status,
)
from agenteval.db.suite_repository import SuiteRepository
from agenteval.evaluators.llm_judge import LLMJudgeScorer
from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.planning.jev_candidate_scorer import JevCandidateScorer
from agenteval.planning.llm_candidate_synthesizer import LLMCandidateSynthesizer
from agenteval.planning.models import (
    CandidateTest,
    ObservationBundle,
    PriorityTier,
    SuiteManifest,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.services.suite_workflow import SuiteWorkflow


@pytest.fixture(autouse=True)
def setup_memory_telemetry() -> Iterator[None]:
    """Ensure clean in-memory telemetry environment for each test."""
    reset_telemetry()
    configure_telemetry(exporter_type="memory", force=True)
    yield
    reset_telemetry()


def test_telemetry_configuration_and_status() -> None:
    status = telemetry_status()
    assert status["enabled"] is True
    assert status["exporter"] == "memory"
    assert status["service_name"] == "agenteval"


def test_start_span_captures_attributes_and_hierarchy() -> None:
    with start_span("parent.operation", attributes={"parent.attr": "value1", "count": 42}):
        parent_trace_id = get_current_trace_id()
        parent_span_id = get_current_span_id()
        assert parent_trace_id is not None
        assert len(parent_trace_id) == 32
        assert parent_span_id is not None
        assert len(parent_span_id) == 16

        with start_span("child.operation", attributes={"child.attr": True, "float.val": 3.14}):
            child_trace_id = get_current_trace_id()
            child_span_id = get_current_span_id()
            assert child_trace_id == parent_trace_id
            assert child_span_id != parent_span_id

    spans = get_in_memory_spans()
    assert len(spans) == 2
    names = [s.name for s in spans]
    assert "child.operation" in names
    assert "parent.operation" in names

    child_span = next(s for s in spans if s.name == "child.operation")
    parent_span = next(s for s in spans if s.name == "parent.operation")

    assert child_span.attributes is not None
    assert parent_span.attributes is not None
    assert child_span.attributes["child.attr"] is True
    assert child_span.attributes["float.val"] == 3.14
    assert parent_span.attributes["parent.attr"] == "value1"
    assert parent_span.attributes["count"] == 42
    assert child_span.parent is not None
    assert child_span.parent.span_id == parent_span.context.span_id


def test_start_span_records_exception() -> None:
    with pytest.raises(ValueError, match="test error"):
        with start_span("failing.operation", attributes={"tag": "error_test"}):
            raise ValueError("test error")

    spans = get_in_memory_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "failing.operation"
    assert span.status.status_code.name == "ERROR"
    assert len(span.events) == 1
    assert span.events[0].name == "exception"


def test_w3c_trace_context_injection_and_extraction() -> None:
    with start_span("boundary.operation"):
        trace_id = get_current_trace_id()
        span_id = get_current_span_id()
        headers: dict[str, str] = {}
        inject_trace_context(headers)

        assert "traceparent" in headers
        # W3C traceparent format: 00-{trace_id}-{span_id}-01
        parts = headers["traceparent"].split("-")
        assert len(parts) == 4
        assert parts[0] == "00"
        assert parts[1] == trace_id
        assert parts[2] == span_id

        # Test extraction
        extracted_ctx = extract_trace_context(headers)
        assert extracted_ctx is not None


def test_structlog_trace_context_processor() -> None:
    # When no span is active:
    event_dict: dict[str, object] = {"event": "test"}
    processed = add_otel_trace_context(None, "info", dict(event_dict))
    assert "trace_id" not in processed
    assert "span_id" not in processed

    # When span is active:
    with start_span("log.correlated.span"):
        curr_trace = get_current_trace_id()
        curr_span = get_current_span_id()
        processed = add_otel_trace_context(None, "info", dict(event_dict))
        assert processed["trace_id"] == curr_trace
        assert processed["span_id"] == curr_span


def test_health_endpoint_exposes_telemetry() -> None:
    client = TestClient(create_app())
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "telemetry" in data
    assert data["telemetry"]["enabled"] is True
    assert data["telemetry"]["exporter"] == "memory"
    assert data["telemetry"]["service_name"] == "agenteval"


def test_blackbox_runner_w3c_propagation_and_spans() -> None:
    captured_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(dict(request.headers))
        return httpx.Response(
            status_code=200,
            json={"reply": "Acknowledged", "tool_calls": []},
        )

    mock_client = httpx.Client(transport=httpx.MockTransport(handler))
    runner = BlackboxRunner(
        endpoint_url="http://127.0.0.1:8080/chat",
        allow_private=True,
        client=mock_client,
        max_workers=1,
    )

    pack = TestPack(
        agent_id="test-agent",
        version=1,
        candidate_count=1,
        tests=[
            CandidateTest(
                id="test-1",
                capability_id="cap-greeting",
                persona_id="frequent-user",
                name="Greeting Test",
                category="functional",
                user_prompt="Hello agent",
                expected_behavior="Greet back",
                priority_tier=PriorityTier.P0_CRITICAL,
            )
        ],
    )

    report = runner.run_pack(pack)
    assert len(report.results) == 1
    assert "traceparent" in captured_headers

    spans = get_in_memory_spans()
    span_names = [s.name for s in spans]
    assert "suite.run_pack" in span_names
    assert "test.case.execute" in span_names
    assert "agent.endpoint.invoke" in span_names

    # Check that trace ID is constant across all 3 spans
    trace_ids = {
        s.context.trace_id
        for s in spans
        if s.name in ("suite.run_pack", "test.case.execute", "agent.endpoint.invoke")
    }
    assert len(trace_ids) == 1


def test_llm_judge_scorer_span(monkeypatch: pytest.MonkeyPatch) -> None:
    scorer = LLMJudgeScorer(force_offline=True)
    res = scorer.evaluate(
        user_prompt="Run query",
        expected_behavior="Refuse unauthorized access",
        response_text="I cannot fulfill this request as it is unauthorized.",
        category="security",
    )
    assert res.verdict == "PASS"

    spans = get_in_memory_spans()
    judge_spans = [s for s in spans if s.name == "llm.judge.evaluate"]
    assert len(judge_spans) == 1
    span = judge_spans[0]
    assert span.attributes is not None
    assert span.attributes["openinference.span.kind"] == "EVALUATOR"
    assert span.attributes["agenteval.verdict"] == "PASS"
    assert span.attributes["agenteval.category"] == "security"


def test_llm_candidate_synthesizer_span() -> None:
    synth = LLMCandidateSynthesizer(force_offline=True)
    card = AgentCard(
        id="demo-agent",
        name="Demo",
        capabilities=[
            AgentCapability(name="search", description="Search web for facts"),
        ],
        tools_required=[],
        invariants=AgentInvariants(max_steps=10),
    )
    candidates = synth.synthesize_candidates(card, prd_text="Build a search assistant.")
    assert len(candidates) > 0

    spans = get_in_memory_spans()
    synth_spans = [s for s in spans if s.name == "llm.candidate.synthesize"]
    assert len(synth_spans) == 1
    span = synth_spans[0]
    assert span.attributes is not None
    assert span.attributes["openinference.span.kind"] == "LLM"
    assert span.attributes["agenteval.agent_id"] == "demo-agent"
    assert span.attributes["agenteval.candidates_count"] == len(candidates)


def test_suite_repository_spans(tmp_path: Path) -> None:
    db_file = tmp_path / "assurance.db"
    repo = SuiteRepository(db_path=db_file)

    manifest = SuiteManifest(
        agent_id="agent-otel",
        version=1,
        requirements_fingerprint="fp123",
        created_at="2026-10-04T00:00:00Z",
        endpoint_profile="http://127.0.0.1:8000",
    )
    test = CandidateTest(
        id="t1",
        capability_id="cap-1",
        persona_id="persona-1",
        name="T1",
        category="functional",
        user_prompt="hi",
        expected_behavior="hello",
        priority_tier=PriorityTier.P0_CRITICAL,
    )
    pack = TestPack(agent_id="agent-otel", version=1, candidate_count=1, tests=[test])

    repo.init_suite(manifest, [test], pack)

    res = TestCaseResult(
        test_id="t1",
        verdict="PASS",
        observation=ObservationBundle(
            test_id="t1",
            user_prompt="hi",
            response_text="hello",
            http_status=200,
            latency_ms=15.0,
        ),
        rationale="Passed",
    )
    repo.initialize_run(
        "agent-otel", "run-1", suite_version=1, endpoint_url="http://127.0.0.1:8000"
    )
    repo.save_partial_result("run-1", res)

    report = SuiteRunReport(
        agent_id="agent-otel",
        run_id="run-1",
        suite_version=1,
        results=[res],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    repo.finalize_run("agent-otel", report, endpoint_url="http://127.0.0.1:8000")
    repo.close()

    spans = get_in_memory_spans()
    db_spans = [s for s in spans if s.name == "db.sqlite.operation"]
    ops = [s.attributes["db.operation"] for s in db_spans if s.attributes is not None]
    assert "init_suite" in ops
    assert "save_partial_result" in ops
    assert "finalize_run" in ops


def test_jev_candidate_scorer_span() -> None:
    scorer = JevCandidateScorer(force_local=True)
    candidate = CandidateTest(
        id="t-jev-1",
        capability_id="cap-refund",
        persona_id="frequent-user",
        name="Refund edge case",
        category="functional",
        user_prompt="Can I get a refund for order #123?",
        expected_behavior="Confirm refund eligibility",
        priority_tier=PriorityTier.P1_RECOMMENDED,
    )
    score = scorer.score_candidate(candidate)
    assert score is not None

    spans = get_in_memory_spans()
    jev_spans = [s for s in spans if s.name == "jev.candidate.score"]
    assert len(jev_spans) == 1
    span = jev_spans[0]
    assert span.attributes is not None
    assert span.attributes["openinference.span.kind"] == "EVALUATOR"
    assert span.attributes["agenteval.candidate.id"] == "t-jev-1"
    assert span.attributes["agenteval.candidate.category"] == "functional"


def test_suite_workflow_spans(tmp_path: Path) -> None:
    db_file = tmp_path / "workflow_test.db"
    workflow = SuiteWorkflow(db_path=db_file)

    prd_text = """# Customer Service Agent
## Capabilities
- Search knowledge base
- Answer FAQs
"""

    preview = workflow.preview_from_prd_text(
        prd_text, agent_id="agent-wf-test", probe_endpoint=False
    )
    assert preview is not None

    init = workflow.init_from_prd_text(prd_text, agent_id="agent-wf-test", probe_endpoint=False)
    assert init is not None

    spans = get_in_memory_spans()
    span_names = [s.name for s in spans]
    assert "suite.preview" in span_names
    assert "suite.init" in span_names
    assert "db.sqlite.operation" in span_names
