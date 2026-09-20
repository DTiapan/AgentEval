"""Scenario loader supporting YAML and JSON scenario suites."""

from pathlib import Path

import yaml

from agenteval.evaluators.state_diff import StateDiffAssertion
from agenteval.faults.injector import FaultRule
from agenteval.scenarios.schema import TestScenario


class ScenarioLoader:
    """Loads and validates test scenario files."""

    def load_file(self, file_path: Path) -> TestScenario:
        """Load a single scenario from a YAML or JSON file."""
        with open(file_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        state_assertions = None
        if "state_assertions" in data and data["state_assertions"]:
            state_assertions = StateDiffAssertion(**data["state_assertions"])

        fault_rules = []
        if "fault_rules" in data and data["fault_rules"]:
            fault_rules = [FaultRule(**r) for r in data["fault_rules"]]

        return TestScenario(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            user_prompt=data["user_prompt"],
            expected_tools=data.get("expected_tools", []),
            state_assertions=state_assertions,
            fault_rules=fault_rules,
            max_steps=data.get("max_steps", 10),
            allow_unverifiable=data.get("allow_unverifiable", False),
        )

    def load(self, target_path: Path) -> list[TestScenario]:
        """Load one or more scenarios from a file or directory."""
        path = Path(target_path)
        if path.is_file():
            return [self.load_file(path)]

        scenarios: list[TestScenario] = []
        for ext in ("*.yaml", "*.yml", "*.json"):
            for p in sorted(path.glob(ext)):
                scenarios.append(self.load_file(p))
        return scenarios
