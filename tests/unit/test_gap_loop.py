"""B5 gap loop: incremental pack extension from pool."""

from agenteval.planning.bootstrap import DEFAULT_PERSONAS, SuiteBootstrap
from agenteval.planning.gap_loop import SuiteGapExtender
from agenteval.planning.generator import CandidatePoolGenerator
from agenteval.planning.models import SuiteManifest, TestPack
from agenteval.planning.suite_store import SuiteStore


def test_gap_extend_appends_tests_from_pool() -> None:
    card_fp = "fp-gap"
    from agenteval.core.manifest import AgentCard, AgentCapability

    card = AgentCard(
        id="gap-agent",
        name="Gap Agent",
        version="1",
        archetype="TOOL_ACTION",
        capabilities=[
            AgentCapability(name="Refund", description="Process refunds"),
            AgentCapability(name="Lookup", description="Lookup orders"),
        ],
    )
    pool = CandidatePoolGenerator().build_pool(card.id, card.capabilities, DEFAULT_PERSONAS)
    assert len(pool) > 4

    opt = SuiteBootstrap(max_tests=2).build(card, card_fp)
    pack = opt[1]
    assert len(pack.tests) == 2

    manifest = SuiteStore.new_manifest(card.id, card_fp, "http://127.0.0.1:1")
    executed = list(pack.tests)

    result, changelog, new_pack = SuiteGapExtender().extend(
        agent_id=card.id,
        manifest=manifest,
        pool=pool,
        pack=pack,
        executed_tests=executed,
        triggered_by_run_id="run-1",
        max_pack_tests=4,
        max_add=2,
    )

    assert changelog is not None
    assert new_pack is not None
    assert not result.noop
    assert result.new_version == 2
    assert len(result.added_test_ids) >= 1
    assert len(new_pack.tests) > len(pack.tests)
    assert len(result.coverage_after.uncovered_tags) <= len(result.coverage_before.uncovered_tags)


def test_gap_extend_noop_when_fully_covered() -> None:
    from agenteval.core.manifest import AgentCard, AgentCapability

    card = AgentCard(
        id="full-agent",
        name="Full",
        version="1",
        archetype="TOOL_ACTION",
        capabilities=[AgentCapability(name="Refund", description="Refunds")],
    )
    pool, pack, _ = SuiteBootstrap(max_tests=50).build(card, "fp-full")
    manifest = SuiteStore.new_manifest(card.id, "fp-full", "")
    executed_tests = pool

    result, changelog, new_pack = SuiteGapExtender().extend(
        agent_id=card.id,
        manifest=manifest,
        pool=pool,
        pack=pack,
        executed_tests=executed_tests,
        triggered_by_run_id="run-1",
        max_pack_tests=len(pack.tests) + 5,
        max_add=3,
    )

    assert changelog is None
    assert new_pack is None
    assert result.noop
