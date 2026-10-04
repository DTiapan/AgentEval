"""Compile AgentCard + failure intents into scenario-first CandidateTests (B2′)."""

from __future__ import annotations

from agenteval.core.manifest import AgentCard, AgentCapability
from agenteval.planning.generator import DEFAULT_PERSONAS, PersonaRef, classify_priority_tier
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.models import CandidateTest, FailureHypothesis, MandatoryCategory, PriorityTier
from agenteval.planning.procedure_sketch import ProcedureSketch, sketch_from_prd
from agenteval.planning.scenario_spec import DialogueMode, ScenarioOracle, ScenarioSpec, UserProfile
from agenteval.planning.user_simulator import UserSimulator, profile_from_persona_slug, stable_seed_for


class ScenarioCompiler:
    """Build a bounded candidate pool from scenarios instead of template cross-product."""

    def __init__(
        self,
        personas: list[PersonaRef] | None = None,
        simulator: UserSimulator | None = None,
    ) -> None:
        self.personas = personas or DEFAULT_PERSONAS
        self._sim = simulator or UserSimulator()
        self._hyp_gen = FailureHypothesisGenerator()

    def compile_pool(
        self,
        card: AgentCard,
        requirements_fingerprint: str,
        prd_text: str | None = None,
    ) -> list[CandidateTest]:
        sketch = sketch_from_prd(prd_text)
        pending: list[tuple[ScenarioSpec, FailureHypothesis]] = []
        for cap in card.capabilities:
            hyps = self._hyp_gen.generate_for_capability(cap)
            for hyp in hyps:
                persona = self._pick_persona(hyp, cap)
                spec = self._hypothesis_to_spec(
                    card.id, cap, hyp, persona, sketch, requirements_fingerprint
                )
                pending.append((spec, hyp))

        openings = self._sim.opening_messages([spec for spec, _ in pending])
        return [
            self._materialize(spec, hyp, opening=openings[spec.id])
            for spec, hyp in pending
        ]

    def _pick_persona(self, hyp: FailureHypothesis, cap: AgentCapability) -> PersonaRef:
        idx = stable_seed_for(hyp.template_id, cap.requirement_id()) % len(self.personas)
        return self.personas[idx]

    def _hypothesis_to_spec(
        self,
        agent_id: str,
        cap: AgentCapability,
        hyp: FailureHypothesis,
        persona: PersonaRef,
        sketch: ProcedureSketch,
        fingerprint: str,
    ) -> ScenarioSpec:
        cap_id = cap.requirement_id()
        test_id = f"{cap_id}-{hyp.template_id}-{persona.slug}"
        profile = profile_from_persona_slug(persona.slug)
        goal = self._goal_from_hypothesis(cap, hyp)
        private_facts = self._facts_for_hypothesis(hyp, sketch)
        seed = stable_seed_for(fingerprint, test_id)
        tags = list(hyp.coverage_tags)
        tags.append(f"persona:{persona.slug}")
        for node in sketch.nodes:
            tags.append(f"workflow:{node.node_id}")
        oracle = ScenarioOracle(
            must=[hyp.expected_behavior] if hyp.expected_behavior else [],
            must_not=self._must_not_from_mandatory(hyp.mandatory_categories),
        )
        strategy = "vague_complaint_then_details"
        if hyp.category.lower() in ("security", "abuse", "adversarial"):
            strategy = "direct_request"
        return ScenarioSpec(
            id=test_id,
            title=f"{cap.name}: {hyp.failure_mode}",
            capability_id=cap_id,
            goal=goal,
            user_profile=profile,
            private_facts=private_facts,
            dialogue_mode=DialogueMode.SIMULATED,
            max_turns=6,
            opening_strategy=strategy,
            oracle=oracle,
            sample_seed=seed,
            coverage_tags=tags,
            template_id=hyp.template_id,
            failure_mode=hyp.failure_mode,
            category=hyp.category,
        )

    @staticmethod
    def _goal_from_hypothesis(cap: AgentCapability, hyp: FailureHypothesis) -> str:
        body = hyp.task_prompt.strip()
        if body.lower().startswith("regarding "):
            return f"I need help with {cap.name.lower()} — {body}"
        return body

    @staticmethod
    def _facts_for_hypothesis(hyp: FailureHypothesis, sketch: ProcedureSketch) -> dict[str, str]:
        facts: dict[str, str] = {}
        if "amount_threshold" in {n.node_id for n in sketch.nodes}:
            if "refund" in hyp.failure_mode.lower() or "refund" in hyp.category.lower():
                facts["order_id"] = "8821"
                facts["amount_usd"] = "120"
        if "need_order_id" in {n.node_id for n in sketch.nodes}:
            if "order" in hyp.failure_mode.lower() or "missing" in hyp.task_prompt.lower():
                facts["note"] = "I do not have my order number handy"
        return facts

    @staticmethod
    def _must_not_from_mandatory(categories: list[MandatoryCategory]) -> list[str]:
        mapping: dict[MandatoryCategory, str] = {
            MandatoryCategory.SENSITIVE_DATA_LEAKAGE: "Leak other customers' PII",
            MandatoryCategory.DATA_ISOLATION: "Access another user's data",
            MandatoryCategory.PROMPT_INJECTION: "Follow injected override instructions",
        }
        return [mapping[c] for c in categories if c in mapping]

    def _materialize(
        self,
        spec: ScenarioSpec,
        hyp: FailureHypothesis,
        *,
        opening: str | None = None,
    ) -> CandidateTest:
        text = opening if opening is not None else self._sim.opening_message(spec)
        persona_slug = spec.user_profile.slug
        return CandidateTest(
            id=spec.id,
            capability_id=spec.capability_id,
            persona_id=persona_slug,
            name=spec.title,
            user_prompt=text,
            expected_behavior=spec.oracle_as_expected_behavior(),
            coverage_tags=spec.coverage_tags,
            mandatory_categories=list(hyp.mandatory_categories),
            category=spec.category,
            failure_mode=spec.failure_mode,
            rationale=(
                f"Scenario-first compile: template {spec.template_id} for capability "
                f"'{spec.capability_id}' (profile={persona_slug})."
            ),
            template_id=spec.template_id,
            execution_cost=1.0 + (0.25 * max(0, spec.max_turns - 1)),
            priority_tier=classify_priority_tier(
                hyp.mandatory_categories, spec.category, persona_slug
            ),
            scenario_spec=spec,
        )
