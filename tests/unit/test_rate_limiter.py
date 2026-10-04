"""Unit tests for sliding-window rate limiting on API endpoints."""

from __future__ import annotations

import time

import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.api.rate_limiter import SlidingWindowRateLimiter, probe_limiter


def _make_mock_request(client_ip: str = "127.0.0.1", api_key: str | None = None) -> Request:
    scope = {
        "type": "http",
        "client": (client_ip, 12345),
        "headers": [(b"x-api-key", api_key.encode())] if api_key else [],
    }
    return Request(scope)


def test_sliding_window_rate_limiter_allows_up_to_rpm() -> None:
    limiter = SlidingWindowRateLimiter(requests_per_minute=3, window_seconds=10.0, name="test")
    limiter.reset()

    req = _make_mock_request("10.0.0.1")

    # First 3 requests must pass
    limiter(req)
    limiter(req)
    limiter(req)

    # 4th request must raise HTTP 429
    with pytest.raises(HTTPException) as exc_info:
        limiter(req)
    assert exc_info.value.status_code == 429
    assert "Retry-After" in exc_info.value.headers
    assert "Rate limit exceeded for test" in exc_info.value.detail


def test_rate_limiter_distinguishes_different_clients() -> None:
    limiter = SlidingWindowRateLimiter(requests_per_minute=2, window_seconds=10.0, name="test")
    limiter.reset()

    req_a = _make_mock_request("10.0.0.1")
    req_b = _make_mock_request("10.0.0.2")

    limiter(req_a)
    limiter(req_a)

    # req_a is blocked
    with pytest.raises(HTTPException):
        limiter(req_a)

    # req_b is allowed
    limiter(req_b)
    limiter(req_b)


def test_rate_limiter_distinguishes_api_keys() -> None:
    limiter = SlidingWindowRateLimiter(requests_per_minute=1, window_seconds=10.0, name="test")
    limiter.reset()

    req_key1 = _make_mock_request("10.0.0.1", api_key="secret-key-1")
    req_key2 = _make_mock_request("10.0.0.1", api_key="secret-key-2")

    limiter(req_key1)
    with pytest.raises(HTTPException):
        limiter(req_key1)

    # Different key from same IP passes
    limiter(req_key2)


def test_rate_limiter_window_expiry(monkeypatch: pytest.MonkeyPatch) -> None:
    limiter = SlidingWindowRateLimiter(requests_per_minute=1, window_seconds=5.0, name="test")
    limiter.reset()

    req = _make_mock_request("10.0.0.5")

    current_time = 1000.0
    monkeypatch.setattr(time, "time", lambda: current_time)

    limiter(req)
    with pytest.raises(HTTPException):
        limiter(req)

    # Advance time past 5s window
    current_time = 1006.0
    # Should now succeed
    limiter(req)


def test_rate_limiter_disabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_RATE_LIMIT_ENABLED", "0")
    limiter = SlidingWindowRateLimiter(requests_per_minute=1, window_seconds=10.0, name="test")
    limiter.reset()

    req = _make_mock_request("10.0.0.9")
    # Allowed indefinitely when disabled
    limiter(req)
    limiter(req)
    limiter(req)


def test_api_route_rate_limiting_enforcement(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_RATE_LIMIT_ENABLED", "1")
    # Reset default limiters
    probe_limiter.reset()
    original_rpm = probe_limiter.requests_per_minute
    try:
        probe_limiter.requests_per_minute = 2

        app = create_app()
        client = TestClient(app)

        # First 2 requests pass probe handler (validating loopback or SSRF)
        r1 = client.post("/v1/endpoints/probe", json={"endpoint_url": "https://example.com/chat"})
        assert r1.status_code != 429

        r2 = client.post("/v1/endpoints/probe", json={"endpoint_url": "https://example.com/chat"})
        assert r2.status_code != 429

        # 3rd request hits 429
        r3 = client.post("/v1/endpoints/probe", json={"endpoint_url": "https://example.com/chat"})
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers
    finally:
        probe_limiter.requests_per_minute = original_rpm
        probe_limiter.reset()
