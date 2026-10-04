"""Unit tests for API CORS origin policy and preflight handling (Slice 2)."""

import pytest
from starlette.testclient import TestClient

from agenteval.api.app import create_app, get_allowed_cors_origins


def test_get_allowed_cors_origins_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTEVAL_CORS_ORIGINS", raising=False)
    origins = get_allowed_cors_origins()
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:8766" in origins
    assert "http://127.0.0.1:8766" in origins
    assert len(origins) == 4


def test_get_allowed_cors_origins_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        "AGENTEVAL_CORS_ORIGINS",
        " https://console.agenteval.app, https://staging.agenteval.app , ,",
    )
    origins = get_allowed_cors_origins()
    assert origins == ["https://console.agenteval.app", "https://staging.agenteval.app"]


def test_get_allowed_cors_origins_wildcard(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_CORS_ORIGINS", "*")
    origins = get_allowed_cors_origins()
    assert origins == ["*"]


def test_cors_default_origins_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTEVAL_CORS_ORIGINS", raising=False)
    client = TestClient(create_app())

    # Allowed local Vite origin
    resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"

    # Allowed local 127.0.0.1 origin
    resp_ip = client.get("/health", headers={"Origin": "http://127.0.0.1:5173"})
    assert resp_ip.status_code == 200
    assert resp_ip.headers.get("access-control-allow-origin") == "http://127.0.0.1:5173"


def test_cors_unauthorized_origin_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTEVAL_CORS_ORIGINS", raising=False)
    client = TestClient(create_app())

    # Untrusted external origin
    resp = client.get("/health", headers={"Origin": "http://evil.com"})
    assert resp.status_code == 200
    # Starlette CORSMiddleware does NOT set access-control-allow-origin for disallowed origins
    assert "access-control-allow-origin" not in resp.headers


def test_cors_custom_origins_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_CORS_ORIGINS", "https://app.agenteval.internal")
    client = TestClient(create_app())

    # Allowed custom domain
    resp = client.get("/health", headers={"Origin": "https://app.agenteval.internal"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "https://app.agenteval.internal"

    # Default Vite origin is no longer allowed when overridden
    resp_default = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "access-control-allow-origin" not in resp_default.headers


def test_cors_wildcard_forces_credentials_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTEVAL_CORS_ORIGINS", "*")
    client = TestClient(create_app())

    resp = client.get("/health", headers={"Origin": "https://anywhere.com"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"
    # Must NOT set allow-credentials to true when wildcard is used (W3C compliance)
    assert resp.headers.get("access-control-allow-credentials") != "true"


def test_cors_preflight_options_accepted_for_allowed_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTEVAL_CORS_ORIGINS", raising=False)
    client = TestClient(create_app())

    resp = client.options(
        "/v1/suites",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert "POST" in resp.headers.get("access-control-allow-methods", "")


def test_cors_preflight_options_rejected_for_disallowed_origin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AGENTEVAL_CORS_ORIGINS", raising=False)
    client = TestClient(create_app())

    resp = client.options(
        "/v1/suites",
        headers={
            "Origin": "http://evil.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # For disallowed origins, preflight does not return allow-origin
    assert "access-control-allow-origin" not in resp.headers
