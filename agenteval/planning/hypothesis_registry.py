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
_EXTERNAL_DEP_KEYWORDS = (
    "external",
    "webhook",
    "third-party",
    "vendor",
    "partner",
    "downstream",
    "gateway",
    "integration",
    "http",
    "rest",
    "remote",
)
_MULTI_STEP_KEYWORDS = (
    "workflow",
    "multi-step",
    "pipeline",
    "process",
    "sequence",
    "order",
    "chain",
    "flow",
    "stage",
    "step",
    "lifecycle",
)
_RATE_LIMIT_KEYWORDS = (
    "batch",
    "stream",
    "bulk",
    "sync",
    "poll",
    "scrape",
    "rate",
    "limit",
    "burst",
    "throttle",
)
_CONCURRENCY_KEYWORDS = (
    "concurrent",
    "parallel",
    "lock",
    "transaction",
    "shared",
    "inventory",
    "seat",
    "balance",
    "transfer",
    "refund",
    "counter",
)
_READ_ONLY_KEYWORDS = (
    "read",
    "view",
    "get",
    "fetch",
    "search",
    "list",
    "query",
    "lookup",
    "find",
    "status",
    "check",
)


_STRONG_MUTATION_KEYWORDS = (
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
    "purge",
)


@dataclass(frozen=True)
class CapabilitySignals:
    """Derived signals from capability text for template applicability."""

    text: str
    is_mutating: bool
    is_sensitive: bool
    has_integration: bool
    is_irreversible: bool
    has_external_dependency: bool = False
    has_multi_step: bool = False
    has_rate_limit: bool = False
    has_concurrency: bool = False
    is_read_only: bool = False


def capability_signals(capability: AgentCapability) -> CapabilitySignals:
    text = f"{capability.name} {capability.description}".lower()
    has_read_intent = any(k in text for k in _READ_ONLY_KEYWORDS)
    has_strong_mutation = any(k in text for k in _STRONG_MUTATION_KEYWORDS)
    is_read_only = has_read_intent and not has_strong_mutation
    is_mutating = not is_read_only and any(k in text for k in _MUTATION_KEYWORDS)

    return CapabilitySignals(
        text=text,
        is_mutating=is_mutating,
        is_sensitive=any(k in text for k in _SENSITIVE_KEYWORDS),
        has_integration=any(k in text for k in _INTEGRATION_KEYWORDS),
        is_irreversible=any(k in text for k in _IRREVERSIBLE_KEYWORDS),
        has_external_dependency=any(k in text for k in _EXTERNAL_DEP_KEYWORDS),
        has_multi_step=any(k in text for k in _MULTI_STEP_KEYWORDS),
        has_rate_limit=any(k in text for k in _RATE_LIMIT_KEYWORDS),
        has_concurrency=any(k in text for k in _CONCURRENCY_KEYWORDS),
        is_read_only=is_read_only,
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
