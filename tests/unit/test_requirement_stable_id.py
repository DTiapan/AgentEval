"""FR-B-02: stable requirement IDs."""

from agenteval.core.requirement_ids import requirement_stable_id
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.suite_store import SuiteStore
from agenteval.planning.suite_sync import SuiteSynchronizer


def test_requirement_stable_id_is_deterministic() -> None:
    text = "Must process refunds within the $100 ceiling."
    assert requirement_stable_id(text) == requirement_stable_id(text)
    assert requirement_stable_id(text).startswith("req-")


def test_heading_rename_keeps_requirement_id() -> None:
    body = "Must never issue refunds exceeding $100 without manager approval."
    text_v1 = f"# Agent\n\n## 2. Refund requirements\n{body}\n"
    text_v2 = f"# Agent\n\n## 9. Renamed section\n{body}\n"
    c1 = RequirementsIngestor.from_text(text_v1, agent_id="a").capabilities[0]
    c2 = RequirementsIngestor.from_text(text_v2, agent_id="a").capabilities[0]
    assert c1.requirement_id() == c2.requirement_id()


def test_suite_sync_keeps_tests_when_only_heading_renames(tmp_path) -> None:
    body = "Refund orders up to the policy limit without bypassing approval."
    text_v1 = f"# Agent\n\n## 2. Capabilities\n- {body}\n"
    text_v2 = f"# Agent\n\n## 5. Capabilities (renamed)\n- {body}\n"
    card_v1 = RequirementsIngestor.from_text(text_v1, agent_id="sync-heading")
    card_v2 = RequirementsIngestor.from_text(text_v2, agent_id="sync-heading")
    fp1 = RequirementsIngestor.fingerprint_text(text_v1)
    fp2 = RequirementsIngestor.fingerprint_text(text_v2)
    pool, pack, _coverage = SuiteBootstrap(max_tests=8).build(card_v1, fp1)
    store = SuiteStore(tmp_path / "suites")
    manifest = SuiteStore.new_manifest("sync-heading", fp1, "http://127.0.0.1:1/chat")
    store.init_suite(manifest, pool, pack, force=True)

    old_manifest = store.load_manifest("sync-heading")
    old_pool = store.load_pool("sync-heading")
    old_pack = store.load_pack("sync-heading")
    outcome = SuiteSynchronizer(max_tests=8).compute_sync(
        agent_id="sync-heading",
        card=card_v2,
        new_fingerprint=fp2,
        old_manifest=old_manifest,
        old_pool=old_pool,
        old_pack=old_pack,
    )
    assert outcome.result.removed_capabilities == []
    assert outcome.pack is not None
    assert len(outcome.pack.tests) == len(old_pack.tests)
