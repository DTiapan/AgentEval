import pytest
from fastapi.testclient import TestClient

from agenteval.api.app import create_app


@pytest.fixture
def client_with_auth(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("AGENTEVAL_API_KEY", "secret123")
    app = create_app()
    return TestClient(app)


def test_health_unauthenticated(client_with_auth: TestClient) -> None:
    res = client_with_auth.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_v1_endpoints_require_auth(client_with_auth: TestClient) -> None:
    res = client_with_auth.get("/v1/packs")
    assert res.status_code == 401
    assert "Missing API Key" in res.json()["detail"]


def test_v1_endpoints_allow_valid_x_api_key(client_with_auth: TestClient) -> None:
    res = client_with_auth.get("/v1/packs", headers={"X-API-Key": "secret123"})
    assert res.status_code == 200
    assert "packs" in res.json()


def test_v1_endpoints_allow_valid_bearer_token(client_with_auth: TestClient) -> None:
    res = client_with_auth.get("/v1/packs", headers={"Authorization": "Bearer secret123"})
    assert res.status_code == 200
    assert "packs" in res.json()


def test_v1_endpoints_reject_invalid_key(client_with_auth: TestClient) -> None:
    res = client_with_auth.get("/v1/packs", headers={"X-API-Key": "wrong"})
    assert res.status_code == 401
    assert "Invalid API Key" in res.json()["detail"]


def test_auth_bypassed_if_no_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTEVAL_API_KEY", raising=False)
    monkeypatch.setenv("AGENTEVAL_API_KEY", "")
    app = create_app()
    client = TestClient(app)
    res = client.get("/v1/packs")
    assert res.status_code == 200
    assert "packs" in res.json()
