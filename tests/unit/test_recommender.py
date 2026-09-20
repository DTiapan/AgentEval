"""Unit tests for the 4-layer Metric Recommender Pipeline."""

from agenteval.core.manifest import AgentArchetype, AgentCard
from agenteval.introspect.models import AgentDNA, IntrospectedTool
from agenteval.recommender.router import MetricRouter


def test_metric_router_classifies_rag_agent() -> None:
    """Test classifier identifies RAG archetype from retrieval tools and keywords."""
    dna = AgentDNA(
        prompt_intent="Find information from internal knowledge base and answer user questions",
        tools=[
            IntrospectedTool(
                name="vector_search_docs",
                description="Query dense vector index for relevant passages",
                parameters={"query": {"type": "string"}},
                required_args=["query"],
            )
        ],
    )

    router = MetricRouter()
    archetype, secondaries, confidence = router.classify(dna)

    assert archetype == AgentArchetype.RAG
    assert confidence >= 0.70


def test_metric_router_classifies_tool_action_agent() -> None:
    """Test classifier identifies Tool-Action archetype from state mutation tools."""
    dna = AgentDNA(
        prompt_intent="Process customer refund and update database",
        tools=[
            IntrospectedTool(name="charge_payment", description="Credit card charge"),
            IntrospectedTool(name="execute_sql_mutation", description="Update database table"),
        ],
    )

    router = MetricRouter()
    archetype, secondaries, confidence = router.classify(dna)

    assert archetype == AgentArchetype.TOOL_ACTION
    assert confidence >= 0.70


def test_metric_router_generates_evaluation_plan_with_universal_and_domain_groups() -> None:
    """Test recommendation engine combines Group A Universal Core with Group B Domain Metrics."""
    card = AgentCard(
        id="support-agent-v1",
        name="Customer Support Agent",
        archetype=AgentArchetype.SUPPORT,
    )

    router = MetricRouter()
    plan = router.recommend(card)

    assert plan.agent_id == "support-agent-v1"
    assert plan.primary_archetype == AgentArchetype.SUPPORT

    # 1. Assert Universal Core (Group A) present on ALL plans
    universal_names = [m.name for m in plan.universal_metrics]
    assert "loop_efficiency" in universal_names
    assert "unverifiable_proof" in universal_names
    assert "latency_and_token_cost" in universal_names

    # 2. Assert Domain-Specific (Group B) contains Support metrics
    domain_names = [m.name for m in plan.domain_metrics]
    assert "hitl_approval_guard" in domain_names
    assert "pii_leakage_detector" in domain_names

    # 3. Assert active scorers compiled
    assert len(plan.active_scorers) >= 4


def test_metric_router_recommends_rag_triad_for_rag_agent() -> None:
    """Test recommendation for RAG includes Faithfulness, Precision, and Recall."""
    card = AgentCard(
        id="doc-researcher",
        name="Documentation Researcher",
        archetype=AgentArchetype.RAG,
    )

    router = MetricRouter()
    plan = router.recommend(card)

    domain_names = [m.name for m in plan.domain_metrics]
    assert "rag_faithfulness" in domain_names
    assert "rag_context_precision" in domain_names
    assert "rag_context_recall" in domain_names
    assert "hallucination_index" in domain_names
