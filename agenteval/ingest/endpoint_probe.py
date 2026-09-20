"""E2: lightweight HTTP endpoint probe for black-box agents."""

import json
import time
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentCard, ToolRequirement


class EndpointProbeResult(BaseModel):
    """Observable facts from a single probe POST (no LLM)."""

    model_config = ConfigDict(extra="forbid")

    endpoint_url: str
    reachable: bool
    http_status: int = 0
    latency_ms: float = 0.0
    response_keys: list[str] = Field(default_factory=list)
    inferred_tool_names: list[str] = Field(default_factory=list)
    error: str = ""
    raw_sample: dict[str, Any] = Field(default_factory=dict)


class EndpointProber:
    """POST a minimal chat payload; infer tools from JSON shape."""

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self.timeout_seconds = timeout_seconds

    def probe(self, endpoint_url: str) -> EndpointProbeResult:
        payload = {
            "prompt": "AgentEval connectivity probe. Reply briefly.",
            "messages": [{"role": "user", "content": "ping"}],
            "history": [],
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                status = resp.getcode()
                raw_bytes = resp.read()
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw_bytes = exc.read()
        except Exception as exc:
            return EndpointProbeResult(
                endpoint_url=endpoint_url,
                reachable=False,
                error=str(exc),
            )

        latency_ms = (time.perf_counter() - start) * 1000.0
        try:
            data = json.loads(raw_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            return EndpointProbeResult(
                endpoint_url=endpoint_url,
                reachable=200 <= status < 300,
                http_status=status,
                latency_ms=latency_ms,
                error="Response was not JSON",
            )

        if not isinstance(data, dict):
            return EndpointProbeResult(
                endpoint_url=endpoint_url,
                reachable=200 <= status < 300,
                http_status=status,
                latency_ms=latency_ms,
                error="JSON root was not an object",
            )

        tools = self._infer_tools(data)
        return EndpointProbeResult(
            endpoint_url=endpoint_url,
            reachable=200 <= status < 300,
            http_status=status,
            latency_ms=latency_ms,
            response_keys=sorted(data.keys()),
            inferred_tool_names=tools,
            raw_sample=self._redact_sample(data),
        )

    @staticmethod
    def _infer_tools(data: dict[str, Any]) -> list[str]:
        names: list[str] = []
        for key in ("tools", "tools_available", "declared_tools"):
            block = data.get(key)
            if isinstance(block, list):
                for item in block:
                    if isinstance(item, str):
                        names.append(item)
                    elif isinstance(item, dict) and item.get("name"):
                        names.append(str(item["name"]))
        tool_calls = data.get("tool_calls") or []
        if isinstance(tool_calls, list):
            for call in tool_calls:
                if isinstance(call, dict):
                    name = call.get("tool_name") or call.get("name")
                    if name:
                        names.append(str(name))
        # de-dupe preserve order
        seen: set[str] = set()
        ordered: list[str] = []
        for name in names:
            if name not in seen:
                seen.add(name)
                ordered.append(name)
        return ordered

    @staticmethod
    def _redact_sample(data: dict[str, Any]) -> dict[str, Any]:
        sample = {k: data[k] for k in list(data.keys())[:8]}
        if "thought" in sample and isinstance(sample["thought"], str):
            text = sample["thought"]
            sample["thought"] = text[:120] + ("…" if len(text) > 120 else "")
        return sample

    @staticmethod
    def merge_tools(card: AgentCard, probe: EndpointProbeResult) -> AgentCard:
        """Append probed tool names not already on the card."""
        if not probe.inferred_tool_names:
            return card
        existing = {t.name for t in card.tools_required}
        merged = list(card.tools_required)
        for name in probe.inferred_tool_names:
            if name in existing:
                continue
            merged.append(
                ToolRequirement(
                    name=name,
                    description="Inferred from endpoint probe (E2)",
                    required=False,
                )
            )
        return card.model_copy(update={"tools_required": merged})

    def try_fetch_openapi_tools(self, endpoint_url: str) -> list[str]:
        """Best-effort OpenAPI discovery at common paths (optional enrich)."""
        parsed = urlparse(endpoint_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        candidates = [
            urljoin(base + "/", "openapi.json"),
            urljoin(base + "/", "openapi.yaml"),
        ]
        names: list[str] = []
        for url in candidates:
            try:
                with urllib.request.urlopen(url, timeout=5.0) as resp:
                    if resp.getcode() != 200:
                        continue
                    text = resp.read().decode("utf-8")
                    if url.endswith(".json"):
                        spec = json.loads(text)
                        from agenteval.introspect.openapi import OpenAPIIntrospector

                        for tool in OpenAPIIntrospector().extract_tools(spec):
                            names.append(tool.name)
            except Exception:
                continue
        return names
