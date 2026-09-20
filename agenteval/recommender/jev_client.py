"""TypeSafe AI / Jev high-speed typed classifier client for AgentEval."""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentArchetype, AgentCard


class JevClassificationResult(BaseModel):
    """Sub-50ms typed inference verdict returned by TypeSafe AI / Jev."""

    model_config = ConfigDict(extra="forbid")

    archetype: AgentArchetype = Field(description="Primary classified archetype")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    recommended_metrics: list[str] = Field(
        default_factory=list, description="Recommended evaluation metric names"
    )
    risk_level: str = Field(
        default="medium", description="Operational risk tier: low, medium, high, critical"
    )
    latency_ms: float = Field(default=0.0, ge=0.0, description="Inference time in milliseconds")
    source: str = Field(
        default="typesafe_jev",
        description="Classifier origin (typesafe_jev, local_heuristic, local_heuristic_fallback)",
    )


class JevClassifierClient:
    """Client for TypeSafe AI / Jev typed agent classification with air-gapped local fallback."""

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout_seconds: float = 3.0,
    ) -> None:
        self.api_key = api_key or os.getenv("TYPESAFE_API_KEY") or os.getenv("JEV_API_KEY")
        self.api_url: str = (
            api_url or os.getenv("TYPESAFE_API_URL") or "https://api.typesafe.ai/v1/classify"
        )
        self.timeout_seconds = timeout_seconds

    def classify_agent(self, card: AgentCard) -> JevClassificationResult:
        """Classify agent DNA into standard archetype and recommended metric suite."""
        if not self.api_key:
            return self._local_fallback(card, source="local_heuristic")

        start_time = time.perf_counter()
        payload: dict[str, Any] = {
            "agent_id": card.id,
            "name": card.name,
            "archetype": card.archetype.value,
            "capabilities": [c.model_dump() for c in card.capabilities],
            "tools_required": [t.model_dump() for t in card.tools_required],
        }

        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        req = urllib.request.Request(self.api_url, data=body_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latency_ms = (time.perf_counter() - start_time) * 1000.0
                return JevClassificationResult(
                    archetype=AgentArchetype(data.get("archetype", card.archetype.value)),
                    confidence=float(data.get("confidence", 0.95)),
                    recommended_metrics=list(data.get("recommended_metrics", [])),
                    risk_level=str(data.get("risk_level", "medium")),
                    latency_ms=latency_ms,
                    source="typesafe_jev",
                )
        except Exception:
            return self._local_fallback(card, source="local_heuristic_fallback")

    def _local_fallback(self, card: AgentCard, source: str) -> JevClassificationResult:
        """Deterministic local scoring fallback when running in air-gapped CI or offline environments."""
        arch = card.archetype

        # Default recommended metrics based on archetype
        if arch == AgentArchetype.TOOL_ACTION:
            metrics = ["state_diff_delta_s", "tool_schema_conformity", "idempotency_score"]
            risk = "high"
        elif arch == AgentArchetype.CODING:
            metrics = ["code_syntax_validity", "test_pass_rate", "diff_minimality"]
            risk = "medium"
        elif arch == AgentArchetype.RAG:
            metrics = ["retrieval_faithfulness", "answer_relevance", "hallucination_detection"]
            risk = "medium"
        elif arch == AgentArchetype.SUPPORT:
            metrics = [
                "sentiment_stability",
                "unverifiable_claim_detection",
                "escalation_adherence",
            ]
            risk = "low"
        else:
            metrics = ["state_diff_delta_s", "tool_schema_conformity"]
            risk = "medium"

        return JevClassificationResult(
            archetype=arch,
            confidence=0.88,
            recommended_metrics=metrics,
            risk_level=risk,
            latency_ms=0.5,
            source=source,
        )
