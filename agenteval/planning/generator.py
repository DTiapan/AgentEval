"""Candidate test pool generator: persona × capability × hypothesis (B2)."""

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentCapability
from agenteval.planning.hypothesis_templates import FailureHypothesisGenerator
from agenteval.planning.models import CandidateTest


class PersonaRef(BaseModel):
    """Minimal persona identity for pool generation (from dynamic personas or fixtures)."""

    model_config = ConfigDict(extra="forbid")

    slug: str
    name: str
    framing: str = Field(description="Short role description for prompt prefix")


class CandidatePoolGenerator:
    """Builds a deterministic candidate pool without executing tests."""

    def __init__(self, hypothesis_generator: FailureHypothesisGenerator | None = None) -> None:
        self._hypotheses = hypothesis_generator or FailureHypothesisGenerator()

    def build_pool(
        self,
        agent_id: str,
        capabilities: list[AgentCapability],
        personas: list[PersonaRef],
    ) -> list[CandidateTest]:
        """Cross-product of capabilities, applicable hypotheses, and personas."""
        if not capabilities or not personas:
            return []

        pool: list[CandidateTest] = []
        for cap in capabilities:
            cap_id = cap.requirement_id()
            for hyp in self._hypotheses.generate_for_capability(cap):
                for persona in personas:
                    test_id = f"{cap_id}-{hyp.template_id}-{persona.slug}"
                    user_prompt = (
                        f"You are acting as {persona.name} ({persona.framing}).\n\n"
                        f"{hyp.task_prompt}"
                    )
                    tags = list(hyp.coverage_tags)
                    tags.append(f"persona:{persona.slug}")
                    pool.append(
                        CandidateTest(
                            id=test_id,
                            capability_id=cap_id,
                            persona_id=persona.slug,
                            name=f"{cap.name}: {hyp.failure_mode} [{persona.name}]",
                            user_prompt=user_prompt,
                            expected_behavior=hyp.expected_behavior,
                            coverage_tags=tags,
                            mandatory_categories=hyp.mandatory_categories,
                            category=hyp.category,
                            failure_mode=hyp.failure_mode,
                            rationale=(
                                f"Template {hyp.template_id} for capability '{cap.name}' "
                                f"with persona '{persona.slug}' (agent={agent_id})."
                            ),
                            template_id=hyp.template_id,
                            execution_cost=1.0,
                        )
                    )
        return pool
