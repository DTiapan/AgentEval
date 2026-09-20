"""E1: requirements markdown → AgentCard."""

from pathlib import Path

from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.bootstrap import SuiteBootstrap


def test_refund_requirements_yield_capabilities() -> None:
    prd = Path("examples/blackbox/requirements.md")
    card = RequirementsIngestor.from_file(prd, agent_id="refund-agent")
    assert card.id == "refund-agent"
    assert len(card.capabilities) >= 4
    assert any("refund" in c.description.lower() for c in card.capabilities)


def test_prd_bootstrap_builds_pool() -> None:
    prd = Path("examples/blackbox/requirements.md")
    card = RequirementsIngestor.from_file(prd, agent_id="refund-agent")
    fp = SuiteBootstrap.fingerprint_prd(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=10).build(card, fp)
    assert len(pool) > len(pack.tests)
    assert len(pack.tests) <= 10
