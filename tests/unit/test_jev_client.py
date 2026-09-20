"""Unit tests for TypeSafe AI / Jev classifier client."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agenteval.core.manifest import AgentArchetype, AgentCard
from agenteval.recommender.jev_client import JevClassificationResult, JevClassifierClient


@pytest.fixture
def sample_card() -> AgentCard:
    return AgentCard(
        id="order-agent",
        name="Order Processor",
        archetype=AgentArchetype.TOOL_ACTION,
    )


def test_jev_client_offline_fallback(
    monkeypatch: pytest.MonkeyPatch, sample_card: AgentCard
) -> None:
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    monkeypatch.delenv("JEV_API_KEY", raising=False)

    client = JevClassifierClient()
    result = client.classify_agent(sample_card)

    assert isinstance(result, JevClassificationResult)
    assert result.archetype == AgentArchetype.TOOL_ACTION
    assert result.source == "local_heuristic"
    assert result.confidence >= 0.8
    assert result.risk_level in ["low", "medium", "high", "critical"]


def test_jev_client_remote_success(monkeypatch: pytest.MonkeyPatch, sample_card: AgentCard) -> None:
    monkeypatch.setenv("JEV_API_KEY", "jev_live_key_123")

    mock_resp_data = {
        "archetype": "TOOL_ACTION",
        "confidence": 0.98,
        "recommended_metrics": ["state_diff_delta_s", "tool_schema_conformity"],
        "risk_level": "high",
        "latency_ms": 38.5,
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_resp_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        client = JevClassifierClient()
        result = client.classify_agent(sample_card)

        assert mock_urlopen.called
        assert result.source == "typesafe_jev"
        assert result.archetype == AgentArchetype.TOOL_ACTION
        assert result.confidence == 0.98
        assert "state_diff_delta_s" in result.recommended_metrics


def test_jev_client_remote_error_fallback(
    monkeypatch: pytest.MonkeyPatch, sample_card: AgentCard
) -> None:
    monkeypatch.setenv("JEV_API_KEY", "jev_live_key_123")

    with patch("urllib.request.urlopen", side_effect=Exception("API Timeout")):
        client = JevClassifierClient()
        result = client.classify_agent(sample_card)

        # Must not crash, should fall back to local heuristic
        assert result.source == "local_heuristic_fallback"
        assert result.archetype == AgentArchetype.TOOL_ACTION
