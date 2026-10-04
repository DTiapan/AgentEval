"""LiteLLM route list: primary OpenAI-compatible infer host, then DeepSeek, then OpenRouter."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from agenteval.planning._utils import load_env

load_env()


@dataclass(frozen=True)
class LiteLlmRoute:
    label: str
    model: str
    api_key: str
    api_base: str | None = None


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def build_llm_routes() -> list[LiteLlmRoute]:
    """Ordered fallback routes for LiteLLM completion calls."""
    routes: list[LiteLlmRoute] = []

    primary_base = _strip_or_none(os.getenv("AGENTEVAL_PRIMARY_LLM_API_BASE"))
    primary_key = _strip_or_none(os.getenv("AGENTEVAL_PRIMARY_LLM_API_KEY"))
    primary_model = _strip_or_none(os.getenv("AGENTEVAL_PRIMARY_LLM_MODEL")) or "benius1"
    if primary_base and primary_key:
        base = primary_base.rstrip("/")
        if base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]
        model = primary_model
        if not model.startswith("openai/"):
            model = f"openai/{model}"
        routes.append(
            LiteLlmRoute(
                label="primary_infer",
                model=model,
                api_key=primary_key,
                api_base=base,
            )
        )

    deepseek_key = _strip_or_none(os.getenv("DEEPSEEK_API_KEY"))
    if deepseek_key:
        ds_model = _strip_or_none(os.getenv("AGENTEVAL_DEEPSEEK_MODEL")) or "deepseek/deepseek-chat"
        routes.append(
            LiteLlmRoute(label="deepseek", model=ds_model, api_key=deepseek_key, api_base=None)
        )

    openrouter_key = _strip_or_none(os.getenv("OPENROUTER_API_KEY"))
    if openrouter_key:
        raw = os.getenv("AGENTEVAL_REAL_AGENT_MODEL", "deepseek/deepseek-v4-flash-0731").strip()
        or_model = raw if raw.startswith("openrouter/") else f"openrouter/{raw}"
        routes.append(
            LiteLlmRoute(label="openrouter", model=or_model, api_key=openrouter_key, api_base=None)
        )

    openai_key = _strip_or_none(os.getenv("OPENAI_API_KEY"))
    if openai_key:
        oa_model = _strip_or_none(os.getenv("AGENTEVAL_OPENAI_MODEL")) or "gpt-4o-mini"
        routes.append(
            LiteLlmRoute(label="openai", model=oa_model, api_key=openai_key, api_base=None)
        )

    return routes


def any_llm_route_available() -> bool:
    return len(build_llm_routes()) > 0


def _route_kwargs(
    route: LiteLlmRoute,
    *,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    timeout: float | None,
    extra: dict[str, Any],
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": route.model,
        "messages": messages,
        "api_key": route.api_key,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "num_retries": 0,
        **extra,
    }
    if timeout is not None:
        kwargs["timeout"] = timeout
    if route.api_base:
        kwargs["api_base"] = route.api_base
    if route.label == "primary_infer":
        headers = dict(kwargs.get("extra_headers") or {})
        headers.setdefault(
            "User-Agent",
            _strip_or_none(os.getenv("AGENTEVAL_PRIMARY_LLM_USER_AGENT")) or "test-client",
        )
        kwargs["extra_headers"] = headers
    return kwargs


def completion_with_fallback(
    *,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1024,
    timeout: float | None = 6.0,
    explicit_api_key: str | None = None,
    explicit_model: str | None = None,
    **extra: Any,
) -> tuple[Any, LiteLlmRoute]:
    """Call litellm.completion on the first route that succeeds."""
    import litellm

    if explicit_api_key and explicit_api_key != "configured":
        model = explicit_model or os.getenv("AGENTEVAL_REAL_AGENT_MODEL", "deepseek/deepseek-v4-flash-0731")
        route = LiteLlmRoute(label="explicit", model=model, api_key=explicit_api_key)
        kwargs = _route_kwargs(
            route,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            extra=extra,
        )
        return litellm.completion(**kwargs), route

    routes = build_llm_routes()
    if not routes:
        raise RuntimeError(
            "No LLM routes configured. Set AGENTEVAL_PRIMARY_LLM_* or DEEPSEEK/OPENROUTER keys."
        )

    last_error: Exception | None = None
    for route in routes:
        kwargs = _route_kwargs(
            route,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            extra=extra,
        )
        try:
            return litellm.completion(**kwargs), route
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError(f"All LLM routes failed: {last_error}") from last_error
