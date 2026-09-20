"""Black-box pack preview (plan command path)."""

from pathlib import Path

from agenteval.core.manifest import AgentCard
from agenteval.planning.plan_preview import build_blackbox_preview


def test_build_blackbox_preview_matches_suite_bootstrap_path(
    tmp_path: Path,
) -> None:
    manifest = tmp_path / "agent.card.yaml"
    manifest.write_text(
        (Path("examples/blackbox/refund_agent.card.yaml")).read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    card = AgentCard.from_yaml(manifest)
    pool, pack, coverage = build_blackbox_preview(card, manifest, None, max_tests=10)
    assert len(pool) > len(pack.tests)
    assert len(pack.tests) <= 10
    assert pack.agent_id == "refund-agent"
    assert coverage.axes
