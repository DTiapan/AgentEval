"""Suite sync: prune on removed capabilities (DR-011)."""

from pathlib import Path

import yaml

from agenteval.core.manifest import AgentCard
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.suite_store import SuiteStore
from agenteval.planning.suite_sync import SuiteSynchronizer


def _write_manifest(path: Path, capabilities: list[dict[str, str]]) -> None:
    doc = {
        "id": "sync-agent",
        "name": "Sync Test Agent",
        "archetype": "TOOL_ACTION",
        "capabilities": capabilities,
    }
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")


def test_suite_sync_prunes_removed_capability(tmp_path: Path) -> None:
    root = tmp_path / "suites"
    manifest_v1 = tmp_path / "v1.yaml"
    _write_manifest(
        manifest_v1,
        [
            {"name": "Issue Refund", "description": "Refund orders"},
            {"name": "Lookup Order", "description": "Find orders"},
        ],
    )
    card_v1 = AgentCard.from_yaml(manifest_v1)
    fp = SuiteBootstrap.fingerprint_files(manifest_v1, None)
    pool, pack, _ = SuiteBootstrap(max_tests=12).build(card_v1, fp)
    store = SuiteStore(root)
    store.init_suite(
        SuiteStore.new_manifest("sync-agent", fp, "http://127.0.0.1:1/chat"),
        pool,
        pack,
        force=True,
    )
    lookup_req_id = next(
        c.requirement_id() for c in card_v1.capabilities if c.description == "Find orders"
    )
    assert any(t.capability_id == lookup_req_id for t in pack.tests)

    manifest_v2 = tmp_path / "v2.yaml"
    _write_manifest(
        manifest_v2,
        [{"name": "Issue Refund", "description": "Refund orders only now"}],
    )
    card_v2 = AgentCard.from_yaml(manifest_v2)
    result = SuiteSynchronizer(max_tests=12).sync(store, "sync-agent", card_v2, manifest_v2, None)

    assert not result.noop
    assert result.removed_capabilities == [lookup_req_id]
    assert result.new_version == 2

    updated_pack = store.load_pack("sync-agent")
    assert all(t.capability_id != lookup_req_id for t in updated_pack.tests)
    assert (root / "sync-agent" / "archive" / "pruned_v2.json").exists()
    assert (root / "sync-agent" / "sync_changelog.jsonl").exists()
