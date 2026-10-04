"""B2′ scenario-first compiler tests."""

from pathlib import Path

from agenteval.ingest.bootstrap import AgentBootstrap
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.scenario_config import legacy_b2_enabled, scenario_first_enabled
from agenteval.planning.scenario_compiler import ScenarioCompiler

FIXTURE_PRD = Path(__file__).resolve().parents[1] / "fixtures" / "prd" / "support_refund_policy.md"


def test_scenario_first_enabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("AGENTEVAL_LEGACY_B2", raising=False)
    monkeypatch.setenv("AGENTEVAL_SCENARIO_FIRST", "1")
    assert scenario_first_enabled() is True
    assert legacy_b2_enabled() is False


def test_legacy_b2_disables_scenario_first(monkeypatch) -> None:
    monkeypatch.setenv("AGENTEVAL_LEGACY_B2", "1")
    assert scenario_first_enabled() is False


def test_compiler_no_meta_persona_prefix() -> None:
    prd = FIXTURE_PRD.read_text(encoding="utf-8")
    card, fp, _ = AgentBootstrap.from_text(prd, agent_id="support-refund-demo")
    pool = ScenarioCompiler().compile_pool(card, fp, prd)
    assert len(pool) >= 3
    for test in pool:
        assert "you are acting as" not in test.user_prompt.lower()
        assert test.scenario_spec is not None
        assert test.scenario_spec.goal


def test_suite_bootstrap_scenario_pool(monkeypatch) -> None:
    monkeypatch.delenv("AGENTEVAL_LEGACY_B2", raising=False)
    monkeypatch.setenv("AGENTEVAL_SCENARIO_FIRST", "1")
    prd = FIXTURE_PRD.read_text(encoding="utf-8")
    card, fp, _ = AgentBootstrap.from_text(prd, agent_id="support-refund-demo")
    pool, pack, _ = SuiteBootstrap(max_tests=8).build(card, fp, prd_text=prd)
    assert pack.tests
    for test in pool:
        if test.scenario_spec is not None:
            assert "you are acting as" not in test.user_prompt.lower()
