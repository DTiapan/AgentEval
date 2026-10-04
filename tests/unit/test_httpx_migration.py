"""Unit tests for Slice 5: httpx migration, connection pooling, and SSRF redirect hooks."""

import httpx
import pytest

from agenteval.ingest.endpoint_probe import EndpointProber
from agenteval.planning.blackbox_runner import BlackboxRunner, JudgeMode
from agenteval.planning.models import CandidateTest, TestPack
from agenteval.security.url_validator import UnsafeURLError, create_safe_client


def test_create_safe_client_blocks_direct_ssrf() -> None:
    """Verify that create_safe_client rejects direct requests to cloud metadata and loopback."""
    client = create_safe_client(allow_private=False)

    with pytest.raises(UnsafeURLError, match="Blocked hostname"):
        client.get("http://metadata.google.internal/computeMetadata/v1/")

    with pytest.raises(UnsafeURLError):
        client.get("http://169.254.169.254/latest/meta-data")


def test_create_safe_client_blocks_redirect_ssrf() -> None:
    """Verify that create_safe_client intercepts 3xx redirect hops attempting to bounce to internal metadata."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/bounce":
            return httpx.Response(302, headers={"Location": "http://169.254.169.254/secret"})
        return httpx.Response(200, text="OK")

    transport = httpx.MockTransport(mock_handler)
    client = create_safe_client(allow_private=False, transport=transport)

    with pytest.raises(UnsafeURLError):
        client.get("http://public.service.com/bounce")


def test_create_safe_client_allows_valid_redirect() -> None:
    """Verify that create_safe_client allows redirects between safe allowed endpoints."""

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/old-path":
            return httpx.Response(301, headers={"Location": "http://api.agent.internal/new-path"})
        return httpx.Response(200, json={"status": "arrived"})

    transport = httpx.MockTransport(mock_handler)
    # allow_private=True to permit .internal test domain
    client = create_safe_client(allow_private=True, transport=transport)

    resp = client.get("http://api.agent.internal/old-path")
    assert resp.status_code == 200
    assert resp.json() == {"status": "arrived"}


def test_create_safe_client_limits_and_timeouts() -> None:
    """Verify default connection limits and timeout settings."""
    client = create_safe_client(timeout=15.0)
    assert client.timeout.connect == 5.0
    assert client.timeout.read == 15.0


def test_blackbox_runner_httpx_invocation() -> None:
    """Verify BlackboxRunner executes requests and parses JSON responses using httpx."""
    test = CandidateTest(
        id="test-1",
        name="Test 1",
        capability_id="cap-1",
        persona_id="p-1",
        user_prompt="Can you refund ticket 123?",
        expected_behavior="Refund issued",
        category="finance",
    )
    pack = TestPack(agent_id="finance-agent", version=1, tests=[test], candidate_count=1)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"reply": "Refund processed successfully."})

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    with BlackboxRunner(
        endpoint_url="http://agent.test.local/chat",
        allow_private=True,
        judge_mode=JudgeMode.DETERMINISTIC_ONLY,
        client=client,
    ) as runner:
        report = runner.run_pack(pack)

    assert len(report.results) == 1
    assert report.results[0].observation.http_status == 200
    assert "Refund processed successfully." in report.results[0].observation.response_text


def test_blackbox_runner_httpx_error_responses() -> None:
    """Verify that HTTP 4xx/5xx responses are captured cleanly without crashing."""
    test = CandidateTest(
        id="test-err",
        name="Test Error",
        capability_id="cap-1",
        persona_id="p-1",
        user_prompt="Drop table",
        expected_behavior="Forbidden",
        category="security",
    )
    pack = TestPack(agent_id="test-agent", version=1, tests=[test], candidate_count=1)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={"error": "Access denied by security policy"})

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    runner = BlackboxRunner(
        endpoint_url="http://agent.test.local/chat",
        allow_private=True,
        judge_mode=JudgeMode.DETERMINISTIC_ONLY,
        client=client,
    )
    report = runner.run_pack(pack)

    assert len(report.results) == 1
    assert report.results[0].observation.http_status == 403
    assert "Access denied" in report.results[0].observation.response_text


def test_blackbox_runner_httpx_transport_error() -> None:
    """Verify network transport failure produces an UNVERIFIABLE result with status 0."""
    test = CandidateTest(
        id="test-net-err",
        name="Test Net Err",
        capability_id="cap-1",
        persona_id="p-1",
        user_prompt="ping",
        expected_behavior="pong",
        category="reliability",
    )
    pack = TestPack(agent_id="test-agent", version=1, tests=[test], candidate_count=1)

    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out after 5.0s")

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    runner = BlackboxRunner(
        endpoint_url="http://agent.test.local/chat",
        allow_private=True,
        judge_mode=JudgeMode.DETERMINISTIC_ONLY,
        client=client,
    )
    report = runner.run_pack(pack)

    assert len(report.results) == 1
    assert report.results[0].observation.http_status == 0
    assert "Connection timed out" in report.results[0].observation.response_text


def test_endpoint_prober_httpx_probe_and_openapi() -> None:
    """Verify EndpointProber probes connectivity and discovers OpenAPI tools with httpx."""
    openapi_spec = {
        "openapi": "3.0.0",
        "info": {"title": "Test API", "version": "1.0"},
        "paths": {
            "/users": {
                "get": {
                    "operationId": "list_users",
                    "description": "List users",
                    "responses": {"200": {"description": "OK"}},
                }
            }
        },
    }

    def mock_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/openapi.json":
            return httpx.Response(200, json=openapi_spec)
        if request.url.path == "/chat":
            return httpx.Response(
                200,
                json={
                    "reply": "Probe received",
                    "tool_calls": [{"name": "lookup_user", "arguments": {}}],
                },
            )
        return httpx.Response(404)

    transport = httpx.MockTransport(mock_handler)
    client = httpx.Client(transport=transport)

    with EndpointProber(allow_private=True, client=client) as prober:
        result = prober.probe("http://agent.test.local/chat")
        assert result.reachable is True
        assert result.http_status == 200
        assert "lookup_user" in result.inferred_tool_names

        discovered = prober.try_fetch_openapi_tools("http://agent.test.local/chat")
        assert "list_users" in discovered
