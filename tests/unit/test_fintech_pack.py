"""Fintech domain pack v0 and registry."""

from pathlib import Path

from agenteval.db.suite_repository import SuiteRepository
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.packs.registry import discover_domain_packs, load_domain_pack
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.suite_store import SuiteStore
from agenteval_packs.fintech.pack import FintechPack


def test_fintech_pack_manifest_and_controls() -> None:
    pack = FintechPack()
    assert pack.manifest.name == "fintech"
    reqs = pack.mandatory_requirements(pack.contribute_options())
    assert len(reqs) == 3
    controls = pack.compliance_controls()
    assert len(controls) == 3
    assert all(c.pack_name == "fintech" for c in controls)


def test_discover_fintech_entry_point() -> None:
    packs = discover_domain_packs()
    assert "fintech" in packs
    loaded = load_domain_pack("fintech")
    assert loaded is not None
    assert loaded.manifest.version == "0.1.0"


def test_freeze_merges_fintech_pack_requirements(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AGENTEVAL_ENABLED_DOMAIN_PACKS", "fintech")
    db = tmp_path / "pack-freeze.db"
    prd = "# Agent\n\n## Capabilities\n- Answer balance inquiries.\n"
    card = RequirementsIngestor.from_text(prd, agent_id="pack-agent")
    fp = RequirementsIngestor.fingerprint_text(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=4).build(card, fp)
    manifest = SuiteStore.new_manifest("pack-agent", fp, "http://127.0.0.1:8765/chat")

    repo = SuiteRepository(db)
    repo.init_suite(
        manifest,
        pool,
        pack,
        agent_card_json=card.model_dump_json(),
        requirements_text=prd,
    )
    requirements = repo.load_normalized_requirements("pack-agent")
    repo.close()

    spec_count = len(card.capabilities)
    pack_rows = [r for r in requirements if r.source_kind == "pack"]
    assert len(requirements) == spec_count + 3
    assert len(pack_rows) == 3
    assert {r.stable_id for r in pack_rows} == {
        "fintech.disclosure.refund_ceiling",
        "fintech.limits.no_unauthorized_transfer",
        "fintech.audit.retain_decision_rationale",
    }


def test_freeze_without_env_does_not_add_pack_rows(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AGENTEVAL_ENABLED_DOMAIN_PACKS", raising=False)
    db = tmp_path / "no-pack.db"
    prd = "# Agent\n\n## Capabilities\n- Answer balance inquiries.\n"
    card = RequirementsIngestor.from_text(prd, agent_id="plain-agent")
    fp = RequirementsIngestor.fingerprint_text(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=4).build(card, fp)
    manifest = SuiteStore.new_manifest("plain-agent", fp, "http://127.0.0.1:8765/chat")

    repo = SuiteRepository(db)
    repo.init_suite(manifest, pool, pack, agent_card_json=card.model_dump_json())
    requirements = repo.load_normalized_requirements("plain-agent")
    repo.close()

    assert all(r.source_kind == "spec" for r in requirements)
