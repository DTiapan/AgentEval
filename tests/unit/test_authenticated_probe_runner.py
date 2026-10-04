"""Unit tests for Authenticated Endpoint Prober and Blackbox Runner (Slice 13.2)."""

import httpx

from agenteval.ingest.endpoint_probe import EndpointProber
from agenteval.planning.blackbox_runner import BlackboxRunner
from agenteval.planning.models import CandidateTest, TestPack
from agenteval.targets.models import AuthType, TargetConnectionProfile


def test_endpoint_prober_with_headers() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if request.headers.get("Authorization") == "Bearer valid-token":
            return httpx.Response(
                200,
                json={"reply": "pong", "tools": ["search"]},
            )
        return httpx.Response(401, json={"error": "Unauthorized"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    prober = EndpointProber(client=client, allow_private=True)

    # Test without auth -> 401
    res_unauth = prober.probe("https://agent.example.com/api")
    assert not res_unauth.reachable
    assert res_unauth.http_status == 401
    assert "401" in res_unauth.error

    # Test with headers -> 200
    res_auth = prober.probe(
        "https://agent.example.com/api",
        headers={"Authorization": "Bearer valid-token"},
    )
    assert res_auth.reachable
    assert res_auth.http_status == 200
    assert "search" in res_auth.inferred_tool_names
    assert len(captured_requests) == 2
    assert captured_requests[1].headers["Authorization"] == "Bearer valid-token"


def test_endpoint_prober_with_connection_profile() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if request.headers.get("X-API-Key") == "secret-key-999":
            return httpx.Response(
                200,
                json={"output": "ready", "declared_tools": ["calculator"]},
            )
        return httpx.Response(403, json={"error": "Forbidden"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    prober = EndpointProber(client=client, allow_private=True)

    profile = TargetConnectionProfile(
        endpoint_url="https://agent.example.com/v1/chat",
        auth_type=AuthType.API_KEY,
        token_secret="secret-key-999",
        custom_headers={"X-Tenant-Id": "tenant-corp"},
    )

    res = prober.probe("https://agent.example.com/v1/chat", profile=profile)
    assert res.reachable
    assert res.http_status == 200
    assert "calculator" in res.inferred_tool_names
    assert len(captured_requests) == 1
    assert captured_requests[0].headers["X-API-Key"] == "secret-key-999"
    assert captured_requests[0].headers["X-Tenant-Id"] == "tenant-corp"


def test_endpoint_prober_openapi_tools_with_headers() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if request.url.path == "/openapi.json":
            if request.headers.get("Authorization") == "Bearer doc-secret":
                return httpx.Response(
                    200,
                    json={
                        "openapi": "3.0.0",
                        "paths": {
                            "/tools/execute": {
                                "post": {
                                    "operationId": "execute_code",
                                    "summary": "Execute code",
                                }
                            }
                        },
                    },
                )
            return httpx.Response(401, json={"error": "Unauthorized"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    prober = EndpointProber(client=client, allow_private=True)

    # Without headers -> fails to fetch openapi
    tools_no_auth = prober.try_fetch_openapi_tools("https://agent.example.com")
    assert tools_no_auth == []

    # With headers -> successfully parses openapi tools
    tools_auth = prober.try_fetch_openapi_tools(
        "https://agent.example.com",
        headers={"Authorization": "Bearer doc-secret"},
    )
    assert "execute_code" in tools_auth


def test_blackbox_runner_with_connection_profile() -> None:
    captured_requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        if request.headers.get("Authorization") == "Bearer runner-secret":
            return httpx.Response(
                200,
                json={"response": "Hello world", "thought": "Plan executed"},
            )
        return httpx.Response(401, json={"error": "Unauthorized"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)

    profile = TargetConnectionProfile(
        endpoint_url="https://agent.example.com/agent",
        auth_type=AuthType.BEARER,
        token_secret="runner-secret",
    )

    runner = BlackboxRunner(
        endpoint_url="https://agent.example.com/agent",
        connection_profile=profile,
        client=client,
        allow_private=True,
    )

    pack = TestPack(
        agent_id="test_agent",
        version=1,
        candidate_count=1,
        tests=[
            CandidateTest(
                id="T-01",
                capability_id="cap-greet",
                persona_id="user",
                name="Say hello",
                user_prompt="Say hello",
                expected_behavior="Friendly greeting",
            )
        ],
    )

    report = runner.run_pack(pack, run_id="run-auth-01")
    assert report.passed == 1
    assert len(captured_requests) == 1
    assert captured_requests[0].headers["Authorization"] == "Bearer runner-secret"
