"""Metric router and dynamic evaluation plan recommender."""

from agenteval.core.manifest import AgentArchetype, AgentCard
from agenteval.introspect.models import AgentDNA, IntrospectedTool
from agenteval.recommender.models import EvaluationPlan, MetricRecommendation


class MetricRouter:
    """Classifies agent archetypes and resolves calibrated Group A and Group B metric suites."""

    def classify(self, dna: AgentDNA) -> tuple[AgentArchetype, list[AgentArchetype], float]:
        """Infer primary and secondary agent archetypes with confidence scoring."""
        if dna.declared_archetype:
            return dna.declared_archetype, [], 1.0

        scores: dict[AgentArchetype, float] = dict.fromkeys(AgentArchetype, 0.1)

        text_corpus = (dna.prompt_intent or "").lower()
        tool_names = [t.name.lower() for t in dna.tools]
        tool_descriptions = [(t.description or "").lower() for t in dna.tools]
        all_tool_text = " ".join(tool_names + tool_descriptions)
        combined_text = f"{text_corpus} {all_tool_text}"

        # 1. RAG indicators
        rag_keywords = [
            "search",
            "knowledge",
            "doc",
            "retriev",
            "chunk",
            "embed",
            "passage",
            "q&a",
            "vector",
        ]
        rag_hits = sum(1 for kw in rag_keywords if kw in combined_text)
        if any("vector" in t or "retriev" in t or "search" in t for t in tool_names):
            rag_hits += 3
        scores[AgentArchetype.RAG] += rag_hits * 0.25

        # 2. Tool-Action indicators
        action_keywords = [
            "order",
            "payment",
            "charge",
            "sql",
            "database",
            "mutate",
            "refund",
            "cart",
            "write",
            "post",
        ]
        action_hits = sum(1 for kw in action_keywords if kw in combined_text)
        if any("sql" in t or "charge" in t or "payment" in t or "write" in t for t in tool_names):
            action_hits += 3
        scores[AgentArchetype.TOOL_ACTION] += action_hits * 0.25

        # 3. Coding indicators
        code_keywords = [
            "code",
            "patch",
            "git",
            "repo",
            "compile",
            "bug",
            "syntax",
            "refactor",
            "unittest",
        ]
        code_hits = sum(1 for kw in code_keywords if kw in combined_text)
        if any("bash" in t or "git" in t or "patch" in t or "compile" in t for t in tool_names):
            code_hits += 3
        scores[AgentArchetype.CODING] += code_hits * 0.25

        # 4. Support indicators
        support_keywords = [
            "customer",
            "support",
            "escalat",
            "ticket",
            "human",
            "pii",
            "crm",
            "policy",
        ]
        support_hits = sum(1 for kw in support_keywords if kw in combined_text)
        if any("escalat" in t or "ticket" in t or "email" in t for t in tool_names):
            support_hits += 3
        scores[AgentArchetype.SUPPORT] += support_hits * 0.25

        # 5. Swarm indicators
        swarm_keywords = ["swarm", "handoff", "delegate", "coordinat", "worker", "planner"]
        swarm_hits = sum(1 for kw in swarm_keywords if kw in combined_text)
        scores[AgentArchetype.SWARM] += swarm_hits * 0.3

        sorted_archetypes = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        primary, top_score = sorted_archetypes[0]

        total_score = sum(scores.values()) or 1.0
        confidence = min(0.99, max(0.65, round(top_score / total_score, 2)))

        secondaries = [
            arch for arch, sc in sorted_archetypes[1:] if sc > 0.5 and sc >= top_score * 0.5
        ]

        return primary, secondaries, confidence

    def recommend(self, target: AgentDNA | AgentCard) -> EvaluationPlan:
        """Generate a complete evaluation plan with Universal Core and Domain-Specific metrics."""
        if isinstance(target, AgentCard):
            dna = AgentDNA(
                declared_archetype=target.archetype,
                tools=[
                    IntrospectedTool(
                        name=r.name,
                        description=r.description,
                        parameters=r.schema_def or {},
                    )
                    for r in target.tools_required
                ],
                prompt_intent="; ".join(c.description for c in target.capabilities),
            )
            agent_id = target.id
        else:
            dna = target
            agent_id = "agent-under-test"

        primary_archetype, secondaries, confidence = self.classify(dna)

        # 1. Group A: Universal Core (MANDATORY on 100% of agents)
        universal_metrics: list[MetricRecommendation] = [
            MetricRecommendation(
                name="loop_efficiency",
                plane=2,
                group="UNIVERSAL_CORE",
                description="Detect infinite loops, consecutive duplicate tool thrashing, and max turn limits",
                evaluator_class="StepEfficiencyEvaluator",
                is_mandatory=True,
            ),
            MetricRecommendation(
                name="unverifiable_proof",
                plane=3,
                group="UNIVERSAL_CORE",
                description="Enforce no-guesswork verdicts: rejects self-reported claims lacking environmental evidence",
                evaluator_class="UnverifiableAssertionEvaluator",
                is_mandatory=True,
            ),
            MetricRecommendation(
                name="latency_and_token_cost",
                plane=8,
                group="UNIVERSAL_CORE",
                description="Track cost per task success and latency degradation",
                evaluator_class="CostAndLatencyEvaluator",
                is_mandatory=True,
            ),
            MetricRecommendation(
                name="consistency_pass_k",
                plane=4,
                group="UNIVERSAL_CORE",
                description="Evaluate non-deterministic variance and reliability floor across N repeated runs",
                evaluator_class="NonDeterminismEvaluator",
                is_mandatory=True,
            ),
        ]

        # 2. Group B: Domain-Specific Metrics
        domain_metrics: list[MetricRecommendation] = []
        fault_suggestions: list[str] = []

        all_target_archetypes = [primary_archetype] + secondaries

        if AgentArchetype.TOOL_ACTION in all_target_archetypes:
            domain_metrics.extend(
                [
                    MetricRecommendation(
                        name="state_diff_delta_s",
                        plane=3,
                        group="DOMAIN_SPECIFIC",
                        description="Cryptographically verify physical environment state mutations (files, DB tables)",
                        evaluator_class="StateDiffEvaluator",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="idempotency_safe_retry",
                        plane=4,
                        group="DOMAIN_SPECIFIC",
                        description="Assert retried operations supply idempotency keys without duplicate side-effects",
                        evaluator_class="IdempotencyScorer",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="tool_contract_validation",
                        plane=2,
                        group="DOMAIN_SPECIFIC",
                        description="Verify tool names and arguments adhere strictly to JSON/Pydantic schemas",
                        evaluator_class="ToolContractValidator",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="chaos_fault_recovery",
                        plane=4,
                        group="DOMAIN_SPECIFIC",
                        description="Test agent resilient recovery under synthetic tool timeouts and HTTP 503 errors",
                        evaluator_class="ToolFaultInjector",
                        is_mandatory=False,
                    ),
                ]
            )
            fault_suggestions.append(
                "Inject HTTP 503 Service Unavailable on 1st payment/mutation call"
            )
            fault_suggestions.append("Inject 1500ms timeout on remote API dependencies")

        if AgentArchetype.RAG in all_target_archetypes:
            domain_metrics.extend(
                [
                    MetricRecommendation(
                        name="rag_faithfulness",
                        plane=5,
                        group="DOMAIN_SPECIFIC",
                        description="Assert generated answer is strictly grounded in retrieved context chunks without hallucination",
                        evaluator_class="FaithfulnessScorer",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="rag_context_precision",
                        plane=5,
                        group="DOMAIN_SPECIFIC",
                        description="Measure signal-to-noise ratio of retrieved documents ranking relevant passages first",
                        evaluator_class="ContextPrecisionScorer",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="rag_context_recall",
                        plane=5,
                        group="DOMAIN_SPECIFIC",
                        description="Verify retrieved context contains all ground-truth facts required to answer",
                        evaluator_class="ContextRecallScorer",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="hallucination_index",
                        plane=5,
                        group="DOMAIN_SPECIFIC",
                        description="Detect ungrounded assertions and fabricated entities",
                        evaluator_class="HallucinationIndexScorer",
                        is_mandatory=False,
                    ),
                ]
            )
            fault_suggestions.append(
                "Inject empty retrieval result to test 'I don't know' fallback"
            )

        if AgentArchetype.CODING in all_target_archetypes:
            domain_metrics.extend(
                [
                    MetricRecommendation(
                        name="code_patch_syntax",
                        plane=5,
                        group="DOMAIN_SPECIFIC",
                        description="Validate generated code diff compiles without syntax errors",
                        evaluator_class="PatchSyntaxValidator",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="unit_test_delta",
                        plane=5,
                        group="DOMAIN_SPECIFIC",
                        description="Measure automated test pass delta (pre-patch vs post-patch)",
                        evaluator_class="UnitTestDeltaScorer",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="forbidden_file_scope_guard",
                        plane=3,
                        group="DOMAIN_SPECIFIC",
                        description="Verify agent only touched authorized files within task blast radius",
                        evaluator_class="FileMutationScopeGuard",
                        is_mandatory=False,
                    ),
                ]
            )

        if AgentArchetype.SUPPORT in all_target_archetypes:
            domain_metrics.extend(
                [
                    MetricRecommendation(
                        name="hitl_approval_guard",
                        plane=5,
                        group="DOMAIN_SPECIFIC",
                        description="Verify agent requests human approval before executing irreversible actions",
                        evaluator_class="HITLPolicyEvaluator",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="pii_leakage_detector",
                        plane=5,
                        group="DOMAIN_SPECIFIC",
                        description="Ensure sensitive user data (passwords, credit cards, PII) is redacted from observations",
                        evaluator_class="PIILeakageScorer",
                        is_mandatory=False,
                    ),
                ]
            )

        if AgentArchetype.SWARM in all_target_archetypes:
            domain_metrics.extend(
                [
                    MetricRecommendation(
                        name="handoff_success_rate",
                        plane=2,
                        group="DOMAIN_SPECIFIC",
                        description="Verify inter-agent delegation transfers required context without dropping state",
                        evaluator_class="HandoffEvaluator",
                        is_mandatory=False,
                    ),
                    MetricRecommendation(
                        name="deadlock_detector",
                        plane=2,
                        group="DOMAIN_SPECIFIC",
                        description="Detect circular dependencies and unresolvable agent handoff loops",
                        evaluator_class="DeadlockDetector",
                        is_mandatory=False,
                    ),
                ]
            )

        active_scorers = [m.name for m in universal_metrics + domain_metrics]

        return EvaluationPlan(
            agent_id=agent_id,
            primary_archetype=primary_archetype,
            secondary_archetypes=secondaries,
            confidence=confidence,
            universal_metrics=universal_metrics,
            domain_metrics=domain_metrics,
            active_scorers=active_scorers,
            fault_suggestions=fault_suggestions,
        )
