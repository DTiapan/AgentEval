"""Slice 1: freeze writes requirements + test_cases to SQLite v2 tables."""

from pathlib import Path

from agenteval.db.suite_repository import SuiteRepository
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.suite_store import SuiteStore


def test_init_suite_persists_normalized_rows(tmp_path: Path) -> None:
    db = tmp_path / "freeze.db"
    prd = (
        "# Refund Agent\n\n"
        "## Capabilities\n"
        "- Process customer refund requests within the $100 ceiling.\n"
        "- Lookup order status and delivery tracking.\n"
    )
    card = RequirementsIngestor.from_text(prd, agent_id="norm-agent")
    fp = RequirementsIngestor.fingerprint_text(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=8).build(card, fp)
    manifest = SuiteStore.new_manifest("norm-agent", fp, "http://127.0.0.1:8765/chat")

    repo = SuiteRepository(db)
    repo.init_suite(
        manifest,
        pool,
        pack,
        agent_card_json=card.model_dump_json(),
        requirements_text=prd,
    )

    requirements = repo.load_normalized_requirements("norm-agent")
    test_cases = repo.load_normalized_test_cases("norm-agent")
    repo.close()

    assert len(requirements) == len(card.capabilities)
    stable_ids = {r.stable_id for r in requirements}
    assert all(c.requirement_id() in stable_ids for c in card.capabilities)

    assert len(test_cases) == len(pack.tests)
    assert all(tc.test_data_json for tc in test_cases)
    linked = [tc for tc in test_cases if tc.criterion_ids]
    assert len(linked) == len(pack.tests)
