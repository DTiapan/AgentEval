"""Tool contract validator: pre-execution schema, required arguments, and boundary assertions."""

from dataclasses import dataclass
from typing import Any

from agenteval.core.models import ToolCall


@dataclass
class ParameterSpec:
    """Specification of expected parameter type and constraints."""

    param_type: type | tuple[type, ...]
    required: bool = True
    min_value: float | None = None
    max_value: float | None = None
    allowed_values: list[Any] | None = None


@dataclass
class ToolSpec:
    """Specification of expected tool parameters."""

    tool_name: str
    parameters: dict[str, ParameterSpec]


@dataclass
class ContractValidationResult:
    """Outcome of pre-execution parameter checking."""

    is_valid: bool
    violations: list[str]


class ToolContractValidator:
    """Asserts that tool calls conform to strict typed parameter contracts before invocation."""

    def __init__(self, specs: dict[str, ToolSpec] | None = None) -> None:
        self.specs = specs or {}

    def validate(self, call: ToolCall) -> ContractValidationResult:
        """Validate tool call arguments against registered ToolSpec."""
        if call.tool_name not in self.specs:
            # Unspecified tools pass contract check by default
            return ContractValidationResult(is_valid=True, violations=[])

        spec = self.specs[call.tool_name]
        violations: list[str] = []

        # Check required and parameter validity
        for param_name, param_spec in spec.parameters.items():
            if param_name not in call.arguments:
                if param_spec.required:
                    violations.append(f"Missing required parameter: '{param_name}'")
                continue

            val = call.arguments[param_name]
            if not isinstance(val, param_spec.param_type):
                violations.append(
                    f"Parameter '{param_name}' expected type {param_spec.param_type}, got {type(val)}"
                )
                continue

            # Boundary checks for numbers
            if isinstance(val, (int, float)):
                if param_spec.min_value is not None and val < param_spec.min_value:
                    violations.append(
                        f"Parameter '{param_name}' value {val} is below minimum {param_spec.min_value}"
                    )
                if param_spec.max_value is not None and val > param_spec.max_value:
                    violations.append(
                        f"Parameter '{param_name}' value {val} exceeds maximum {param_spec.max_value}"
                    )

            # Enum checks
            if param_spec.allowed_values is not None and val not in param_spec.allowed_values:
                violations.append(
                    f"Parameter '{param_name}' value {val} not in allowed values: {param_spec.allowed_values}"
                )

        return ContractValidationResult(is_valid=len(violations) == 0, violations=violations)
