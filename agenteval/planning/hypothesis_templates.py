"""Rule-based failure hypothesis generation (B1) via template registry."""

from agenteval.core.manifest import AgentCapability
from agenteval.planning import hypothesis_catalog  # noqa: F401 — registers templates
from agenteval.planning._utils import slugify
from agenteval.planning.hypothesis_registry import (
    base_coverage_tags,
    capability_signals,
    iter_templates,
)
from agenteval.planning.models import FailureHypothesis, MandatoryCategory, ProvenanceLayer


class FailureHypothesisGenerator:
    """Produces bounded, rule-based failure hypotheses for a capability."""

    def generate_for_capability(self, capability: AgentCapability) -> list[FailureHypothesis]:
        """Return all registered templates that apply to this capability."""
        cap_id = slugify(capability.name)
        sig = capability_signals(capability)
        results: list[FailureHypothesis] = []
        for tmpl in iter_templates():
            if not tmpl.applies(sig):
                continue
            tags = base_coverage_tags(cap_id, tmpl.coverage_tag, tmpl.category, tmpl.coverage_tag)
            results.append(
                FailureHypothesis(
                    template_id=tmpl.template_id,
                    capability_id=cap_id,
                    category=tmpl.category,
                    failure_mode=tmpl.failure_mode,
                    coverage_tags=tags,
                    mandatory_categories=list(tmpl.mandatory),
                    expected_behavior=tmpl.expected_behavior,
                    task_prompt=tmpl.task_prompt(capability),
                    provenance=ProvenanceLayer.HYPOTHESIZED,
                )
            )
        return results

    def infer_applicable_mandatory(
        self, capabilities: list[AgentCapability]
    ) -> list[MandatoryCategory]:
        """Union of mandatory categories triggered across capabilities (for optimizer config)."""
        seen: set[MandatoryCategory] = set()
        for cap in capabilities:
            for hyp in self.generate_for_capability(cap):
                seen.update(hyp.mandatory_categories)
        return sorted(seen, key=lambda m: m.value)
