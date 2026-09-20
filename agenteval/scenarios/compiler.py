"""Scenario compiler: derives executable TestScenarios from AgentCards, Personas, and PRDs."""

import re
from pathlib import Path

from agenteval.core.manifest import AgentCard
from agenteval.core.models import FailureClass
from agenteval.faults.injector import FaultRule
from agenteval.introspect.persona import PersonaIntrospector
from agenteval.scenarios.schema import TestScenario


class ScenarioCompiler:
    """Compiles high-level agent specifications and requirements into concrete evaluation scenarios."""

    @classmethod
    def compile_scenarios(
        cls,
        card: AgentCard,
        include_chaos: bool = True,
    ) -> list[TestScenario]:
        """Compile an AgentCard into a suite of baseline and chaos evaluation scenarios."""
        scenarios: list[TestScenario] = []
        expected_tool_names = [t.name for t in card.tools_required]

        for cap in card.capabilities:
            cap_slug = cls._slug(cap.name)

            # 1. Baseline happy-path scenario
            baseline = TestScenario(
                id=f"{card.id}-{cap_slug}-baseline",
                name=f"{card.name}: {cap.name} (Baseline)",
                description=cap.description,
                user_prompt=f"Please perform the following task as {card.name}: {cap.description}",
                expected_tools=expected_tool_names,
                fault_rules=[],
                max_steps=card.invariants.max_steps,
                allow_unverifiable=False,
            )
            scenarios.append(baseline)

            # 2. Chaos resilience scenario if tools are present
            if include_chaos and expected_tool_names:
                target_tool = expected_tool_names[0]
                fault_rule = FaultRule(
                    tool_name=target_tool,
                    trigger_occurrence=1,
                    fault_type=FailureClass.TOOL_FAILURE,
                    error_message=f"Simulated transient 503 error on tool {target_tool}",
                )
                chaos = TestScenario(
                    id=f"{card.id}-{cap_slug}-chaos",
                    name=f"{card.name}: {cap.name} (Chaos Resilience)",
                    description=f"Chaos test injecting transient failure into {target_tool}",
                    user_prompt=f"Please perform the following task as {card.name}: {cap.description}",
                    expected_tools=expected_tool_names,
                    fault_rules=[fault_rule],
                    max_steps=card.invariants.max_steps + 2,
                    allow_unverifiable=False,
                )
                scenarios.append(chaos)

        return scenarios

    @classmethod
    def compile_from_persona(
        cls,
        persona_path: Path | str,
        include_chaos: bool = True,
    ) -> list[TestScenario]:
        """Compile executable test scenarios directly from an agency persona markdown file."""
        card = PersonaIntrospector.parse_file(persona_path)
        return cls.compile_scenarios(card, include_chaos=include_chaos)

    @classmethod
    def compile_from_prd(
        cls,
        prd_text: str,
        agent_name: str = "Target Agent",
    ) -> list[TestScenario]:
        """Parse requirement bullets/features from PRD text and compile evaluation scenarios."""
        lines = prd_text.strip().splitlines()
        req_lines = [
            line.strip().lstrip("0123456789.-* ")
            for line in lines
            if any(
                marker in line.lower()
                for marker in ["feature:", "requirement:", "must", "should", "task:"]
            )
            or re.match(r"^\s*\d+\.\s+", line)
        ]

        if not req_lines:
            req_lines = [
                line.strip() for line in lines if line.strip() and not line.strip().startswith("#")
            ]

        agent_slug = cls._slug(agent_name)
        scenarios: list[TestScenario] = []

        for i, req in enumerate(req_lines):
            clean_req = req.replace("Feature:", "").replace("Requirement:", "").strip()
            if not clean_req:
                continue
            sc_id = f"{agent_slug}-req-{i + 1}"
            sc = TestScenario(
                id=sc_id,
                name=f"{agent_name}: Requirement {i + 1}",
                description=clean_req,
                user_prompt=f"Requirement to fulfill: {clean_req}",
                expected_tools=[],
                fault_rules=[],
                max_steps=10,
                allow_unverifiable=False,
            )
            scenarios.append(sc)

        return scenarios

    @staticmethod
    def _slug(text: str) -> str:
        """Convert arbitrary string into clean URL/file-safe slug."""
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
        return cleaned or "default"
