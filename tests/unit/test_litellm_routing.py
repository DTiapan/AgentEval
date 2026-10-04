"""LLM provider fallback routing."""

from agenteval.planning.litellm_routing import build_llm_routes


def test_build_routes_primary_then_deepseek_then_openrouter(monkeypatch) -> None:
    monkeypatch.setenv("AGENTEVAL_PRIMARY_LLM_API_BASE", "https://infer.example/v1")
    monkeypatch.setenv("AGENTEVAL_PRIMARY_LLM_API_KEY", "pk-test")
    monkeypatch.setenv("AGENTEVAL_PRIMARY_LLM_MODEL", "benius1")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    routes = build_llm_routes()
    assert [r.label for r in routes] == ["primary_infer", "deepseek", "openrouter"]
    assert routes[0].model == "openai/benius1"
    assert routes[0].api_base == "https://infer.example/v1"


def test_primary_base_strips_chat_completions_suffix(monkeypatch) -> None:
    monkeypatch.setenv(
        "AGENTEVAL_PRIMARY_LLM_API_BASE",
        "https://infer.example/v1/chat/completions",
    )
    monkeypatch.setenv("AGENTEVAL_PRIMARY_LLM_API_KEY", "pk-test")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    routes = build_llm_routes()
    assert routes[0].api_base == "https://infer.example/v1"
