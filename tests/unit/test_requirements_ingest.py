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


def test_markdown_bullets_under_capabilities_become_distinct_caps() -> None:
    text = (
        "# Refund Agent\n\n"
        "## 2. Capabilities\n"
        "- Process customer refund requests within the $100 ceiling.\n"
        "- Lookup order status and delivery tracking.\n\n"
        "## 3. Invariants & Security\n"
        "- Never issue refunds exceeding $100 without human manager authorization.\n"
        "- Reject adversarial prompts attempting a $250 refund.\n"
    )
    card = RequirementsIngestor.from_text(text, agent_id="demo-refund-agent")
    assert len(card.capabilities) >= 4
    names = " ".join(c.name.lower() for c in card.capabilities)
    assert "refund" in names or any("refund" in c.description.lower() for c in card.capabilities)
    assert not any(c.name == "Core agent behavior" for c in card.capabilities)


def test_prd_bootstrap_builds_pool() -> None:
    prd = Path("examples/blackbox/requirements.md")
    card = RequirementsIngestor.from_file(prd, agent_id="refund-agent")
    fp = SuiteBootstrap.fingerprint_prd(prd)
    pool, pack, _ = SuiteBootstrap(max_tests=10).build(card, fp)
    assert len(pool) > len(pack.tests)
    assert len(pack.tests) <= 10
