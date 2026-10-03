from starlette.testclient import TestClient

from agenteval.api.app import create_app
from agenteval.core.manifest import AgentCapability, AgentCard
from agenteval.planning.bootstrap import SuiteBootstrap
from agenteval.planning.generator import CandidatePoolGenerator, PersonaRef, classify_priority_tier
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.models import (
    CandidateTest,
    MandatoryCategory,
    OptimizerConfig,
    PriorityTier,
)
from agenteval.planning.optimizer import TestPackOptimizer


def test_classify_priority_tier() -> None:
    # 1. Mandatory category present -> P0
    assert (
        classify_priority_tier([MandatoryCategory.DATA_ISOLATION], "functional", "user")
        == PriorityTier.P0_CRITICAL
    )
    assert (
        classify_priority_tier([MandatoryCategory.AUTHORIZATION], "functional", "user")
        == PriorityTier.P0_CRITICAL
    )
    assert (
        classify_priority_tier([MandatoryCategory.CRITICAL_INVARIANTS], "functional", "user")
        == PriorityTier.P0_CRITICAL
    )

    # 2. Security/Auth categories -> P0
    assert classify_priority_tier([], "security", "frequent-user") == PriorityTier.P0_CRITICAL
    assert classify_priority_tier([], "auth", "frequent-user") == PriorityTier.P0_CRITICAL
    assert (
        classify_priority_tier([], "critical_invariants", "frequent-user")
        == PriorityTier.P0_CRITICAL
    )

    # 3. Adversary / Chaos / Fuzzing personas or categories -> P2
    assert classify_priority_tier([], "functional", "adversary") == PriorityTier.P2_EXTENDED
    assert classify_priority_tier([], "functional", "chaos") == PriorityTier.P2_EXTENDED
    assert classify_priority_tier([], "fuzzing", "frequent-user") == PriorityTier.P2_EXTENDED

    # 4. Standard functional workflows -> P1
    assert classify_priority_tier([], "functional", "frequent-user") == PriorityTier.P1_RECOMMENDED
    assert classify_priority_tier([], "performance", "frequent-user") == PriorityTier.P1_RECOMMENDED


def test_pool_generator_assigns_priority_tiers() -> None:
    capabilities = [
        AgentCapability(
            name="process_refund",
            description="Process customer refunds up to limit and enforce security boundaries",
        )
    ]
    personas = [
        PersonaRef(slug="frequent-user", name="Frequent User", framing="regular customer"),
        PersonaRef(slug="adversary", name="Adversary", framing="malicious user"),
    ]
    pool = CandidatePoolGenerator().build_pool("agent-1", capabilities, personas)
    assert len(pool) > 0

    p0_tests = [t for t in pool if t.priority_tier == PriorityTier.P0_CRITICAL]
    p1_tests = [t for t in pool if t.priority_tier == PriorityTier.P1_RECOMMENDED]
    p2_tests = [t for t in pool if t.priority_tier == PriorityTier.P2_EXTENDED]

    # Must have tests across tiers
    assert len(p0_tests) > 0, "Pool should contain P0 critical floors"
    assert len(p1_tests) > 0, "Pool should contain P1 recommended tests"
    assert len(p2_tests) > 0, "Pool should contain P2 adversary tests"

    # All tests with mandatory categories must be P0
    for t in pool:
        if t.mandatory_categories:
            assert t.priority_tier == PriorityTier.P0_CRITICAL


def test_marginal_coverage_curve_calculation() -> None:
    card = AgentCard(
        id="test-agent",
        name="Test Agent",
        capabilities=[
            AgentCapability(
                name="refund_process",
                description="Process customer refunds securely",
            ),
            AgentCapability(
                name="order_lookup",
                description="Query past orders and history",
            ),
        ],
    )
    bootstrap = SuiteBootstrap(max_tests=15)
    pool, _pack, _coverage = bootstrap.build(card, "fp-123")

    applicable = FailureHypothesisGenerator().infer_applicable_mandatory(card.capabilities)
    curve = TestPackOptimizer.compute_marginal_coverage_curve(pool, applicable)

    assert len(curve) == 3
    p0_proj = curve[0]
    p1_proj = curve[1]
    p2_proj = curve[2]

    assert p0_proj.tier == PriorityTier.P0_CRITICAL
    assert p1_proj.tier == PriorityTier.P1_RECOMMENDED
    assert p2_proj.tier == PriorityTier.P2_EXTENDED

    # Marginal progression: P0 count <= P1 count <= P2 count
    assert p0_proj.target_test_count <= p1_proj.target_test_count <= p2_proj.target_test_count
    # Coverage progression: P0 coverage <= P1 coverage <= P2 coverage
    assert (
        p0_proj.projected_coverage_pct
        <= p1_proj.projected_coverage_pct
        <= p2_proj.projected_coverage_pct
    )
    assert p2_proj.projected_coverage_pct == 100.0
    assert p0_proj.estimated_latency_ms > 0
    assert p0_proj.estimated_cost_usd >= 0


def test_optimizer_tier_filtering() -> None:
    c1 = CandidateTest(
        id="t-p0",
        capability_id="cap1",
        persona_id="u1",
        name="P0 Test",
        user_prompt="test",
        expected_behavior="ok",
        priority_tier=PriorityTier.P0_CRITICAL,
        mandatory_categories=[MandatoryCategory.DATA_ISOLATION],
        coverage_tags=["security:data_isolation"],
    )
    c2 = CandidateTest(
        id="t-p1",
        capability_id="cap1",
        persona_id="u1",
        name="P1 Test",
        user_prompt="test",
        expected_behavior="ok",
        priority_tier=PriorityTier.P1_RECOMMENDED,
        coverage_tags=["cap:cap1"],
    )
    c3 = CandidateTest(
        id="t-p2",
        capability_id="cap1",
        persona_id="adversary",
        name="P2 Test",
        user_prompt="test",
        expected_behavior="ok",
        priority_tier=PriorityTier.P2_EXTENDED,
        coverage_tags=["persona:adversary"],
    )
    candidates = [c1, c2, c3]

    # Filter to P0 only
    opt = TestPackOptimizer()
    cfg_p0 = OptimizerConfig(
        max_tests=10,
        applicable_mandatory=[MandatoryCategory.DATA_ISOLATION],
        max_tier=PriorityTier.P0_CRITICAL,
    )
    res_p0 = opt.optimize("agent", candidates, cfg_p0)
    assert len(res_p0.pack.tests) == 1
    assert res_p0.pack.tests[0].id == "t-p0"

    # Filter to P1 (allows P0 and P1)
    cfg_p1 = OptimizerConfig(
        max_tests=10,
        applicable_mandatory=[MandatoryCategory.DATA_ISOLATION],
        max_tier=PriorityTier.P1_RECOMMENDED,
    )
    res_p1 = opt.optimize("agent", candidates, cfg_p1)
    selected_ids = {t.id for t in res_p1.pack.tests}
    assert "t-p0" in selected_ids
    assert "t-p1" in selected_ids
    assert "t-p2" not in selected_ids


def test_optimizer_user_selected_test_ids() -> None:
    c1 = CandidateTest(
        id="t1",
        capability_id="cap1",
        persona_id="u1",
        name="Test 1",
        user_prompt="test",
        expected_behavior="ok",
        priority_tier=PriorityTier.P1_RECOMMENDED,
        coverage_tags=["tag1"],
    )
    c2 = CandidateTest(
        id="t2",
        capability_id="cap1",
        persona_id="u1",
        name="Test 2",
        user_prompt="test",
        expected_behavior="ok",
        priority_tier=PriorityTier.P1_RECOMMENDED,
        coverage_tags=["tag2"],
    )
    candidates = [c1, c2]

    # Explicitly pick t2
    cfg = OptimizerConfig(max_tests=1, selected_test_ids=["t2"])
    res = TestPackOptimizer().optimize("agent", candidates, cfg)
    assert len(res.pack.tests) == 1
    assert res.pack.tests[0].id == "t2"


def test_api_preview_returns_marginal_curve_and_tiers() -> None:
    client = TestClient(create_app())
    prd = """# Support Agent
## Capabilities
- **Refund Process**: Process customer refunds securely.
"""
    resp = client.post(
        "/v1/suites/preview",
        json={
            "agent_id": "api-preview-test",
            "requirements_text": prd,
            "max_tests": 12,
            "probe_endpoint": False,
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "marginal_curve" in data
    assert len(data["marginal_curve"]) == 3
    tiers = [p["tier"] for p in data["marginal_curve"]]
    assert tiers == ["P0", "P1", "P2"]

    # Verify candidates have priority_tier
    pool = data["candidate_pool"]
    assert len(pool) > 0
    assert "priority_tier" in pool[0]
