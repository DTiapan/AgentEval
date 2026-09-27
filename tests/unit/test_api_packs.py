"""Pack API and init with enabled_domain_packs."""

from pathlib import Path

from fastapi.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.db.suite_repository import SuiteRepository


def test_list_domain_packs_includes_fintech() -> None:
    client = TestClient(create_app())
    res = client.get("/v1/packs")
    assert res.status_code == 200
    packs = res.json()["packs"]
    assert any(p["id"] == "fintech" for p in packs)


def test_init_suite_with_enabled_domain_packs(tmp_path: Path, monkeypatch) -> None:
    db_file = tmp_path / "api-pack.db"
    monkeypatch.setenv("AGENTEVAL_USE_SQLITE", "1")
    monkeypatch.setenv("AGENTEVAL_DATABASE_URL", f"sqlite:///{db_file}")
    monkeypatch.delenv("AGENTEVAL_ENABLED_DOMAIN_PACKS", raising=False)
    client = TestClient(create_app())
    prd = "# Agent\n\n## Capabilities\n- Answer balance inquiries.\n"
    res = client.post(
        "/v1/suites",
        json={
            "requirements_text": prd,
            "agent_id": "api-pack-agent",
            "endpoint_url": "http://127.0.0.1:8765/chat",
            "probe_endpoint": False,
            "enabled_domain_packs": ["fintech"],
        },
    )
    assert res.status_code == 201
    repo = SuiteRepository(db_file)
    requirements = repo.load_normalized_requirements("api-pack-agent")
    repo.close()
    assert any(r.source_kind == "pack" for r in requirements)
