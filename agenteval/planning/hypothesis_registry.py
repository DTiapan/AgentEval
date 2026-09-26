"""Metaprogramming registry for declarative hypothesis templates."""

from collections.abc import Callable, Iterator
from dataclasses import dataclass

from agenteval.core.manifest import AgentCapability
from agenteval.planning.models import MandatoryCategory

_SENSITIVE_KEYWORDS = (
    "auth",
    "account",
    "customer",
    "user",
    "pii",
    "password",
    "payment",
    "card",
    "admin",
    "privilege",
    "credential",
    "ssn",
    "hipaa",
)
_MUTATION_KEYWORDS = (
    "refund",
    "delete",
    "remove",
    "transfer",
    "write",
    "update",
    "create",
    "charge",
    "pay",
    "mutate",
    "cancel",
    "issue",
    "submit",
    "order",
)
_INTEGRATION_KEYWORDS = (
    "api",
    "integration",
    "webhook",
    "external",
    "service",
    "database",
    "sync",
)
_IRREVERSIBLE_KEYWORDS = ("refund", "delete", "transfer", "charge", "cancel", "purge")


@dataclass(frozen=True)
class CapabilitySignals:
    """Derived signals from capability text for template applicability."""

    text: str
    is_mutating: bool
    is_sensitive: bool
    has_integration: bool
    is_irreversible: bool


def capability_signals(capability: AgentCapability) -> CapabilitySignals:
    text = f"{capability.name} {capability.description}".lower()
    return CapabilitySignals(
        text=text,
        is_mutating=any(k in text for k in _MUTATION_KEYWORDS),
        is_sensitive=any(k in text for k in _SENSITIVE_KEYWORDS),
        has_integration=any(k in text for k in _INTEGRATION_KEYWORDS),
        is_irreversible=any(k in text for k in _IRREVERSIBLE_KEYWORDS),
    )


def base_coverage_tags(
    cap_id: str, failure_tag: str, category: str, coverage_tag: str
) -> list[str]:
    tags = [f"cap:{cap_id}", f"failure:{failure_tag}"]
    if category == "security":
        tags.append(f"security:{coverage_tag}")
    return tags


@dataclass(frozen=True)
class HypothesisTemplateSpec:
    """Registered template definition."""

    template_id: str
    category: str
    failure_mode: str
    coverage_tag: str
    mandatory: tuple[MandatoryCategory, ...]
    applies: Callable[[CapabilitySignals], bool]
    task_prompt: Callable[[AgentCapability], str]
    expected_behavior: str
    execution_cost: float = 1.0


_REGISTRY: list[HypothesisTemplateSpec] = []


def register_hypothesis(
    template_id: str,
    *,
    category: str,
    failure_mode: str,
    coverage_tag: str,
    mandatory: tuple[MandatoryCategory, ...] = (),
    applies: Callable[[CapabilitySignals], bool] | None = None,
    execution_cost: float = 1.0,
    expected_behavior: str,
    task_prompt: Callable[[AgentCapability], str],
) -> HypothesisTemplateSpec:
    """Register one hypothesis template (catalog is built at import time)."""
    spec = HypothesisTemplateSpec(
        template_id=template_id,
        category=category,
        failure_mode=failure_mode,
        coverage_tag=coverage_tag,
        mandatory=mandatory,
        applies=applies or (lambda _s: True),
        task_prompt=task_prompt,
        expected_behavior=expected_behavior,
        execution_cost=execution_cost,
    )
    _REGISTRY.append(spec)
    return spec


def iter_templates() -> Iterator[HypothesisTemplateSpec]:
    return iter(_REGISTRY)


def clear_registry_for_tests() -> None:
    """Test-only: reset registry."""
    _REGISTRY.clear()
