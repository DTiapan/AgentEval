"""E2: lightweight HTTP endpoint probe for black-box agents."""

from __future__ import annotations

import json
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field

from agenteval.core.manifest import AgentCard, ToolRequirement
from agenteval.security.url_validator import (
    UnsafeURLError,
    create_safe_client,
    is_private_allowed,
    validate_endpoint_url,
)
from agenteval.targets import TargetConnectionProfile


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

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        allow_private: bool | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.allow_private = is_private_allowed() if allow_private is None else allow_private
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = create_safe_client(
                allow_private=self.allow_private,
                timeout=self.timeout_seconds,
            )
            self._owns_client = True

    def probe(
        self,
        endpoint_url: str,
        *,
        headers: dict[str, str] | None = None,
        profile: TargetConnectionProfile | None = None,
    ) -> EndpointProbeResult:
        effective_url = profile.endpoint_url if profile and profile.endpoint_url else endpoint_url
        try:
            validate_endpoint_url(effective_url, allow_private=self.allow_private)
        except UnsafeURLError as exc:
            return EndpointProbeResult(
                endpoint_url=effective_url,
                reachable=False,
                error=f"SSRF protection: {exc}",
            )

        effective_headers: dict[str, str] = {"Content-Type": "application/json"}
        if profile is not None:
            effective_headers.update(profile.resolve_headers())
        if headers is not None:
            effective_headers.update(headers)

        payload = {
            "prompt": "AgentEval connectivity probe. Reply briefly.",
            "messages": [{"role": "user", "content": "ping"}],
            "history": [],
        }
        start = time.perf_counter()
        try:
            resp = self._client.post(effective_url, json=payload, headers=effective_headers)
            status = resp.status_code
        except UnsafeURLError as exc:
            return EndpointProbeResult(
                endpoint_url=effective_url,
                reachable=False,
                error=f"SSRF protection: {exc}",
            )
        except httpx.HTTPError as exc:
            return EndpointProbeResult(
                endpoint_url=effective_url,
                reachable=False,
                error=str(exc),
            )
        except Exception as exc:
            return EndpointProbeResult(
                endpoint_url=effective_url,
                reachable=False,
                error=str(exc),
            )

        latency_ms = (time.perf_counter() - start) * 1000.0
        try:
            data = resp.json()
        except Exception:
            error_msg = ""
            if not (200 <= status < 300):
                error_msg = f"HTTP {status}"
            else:
                error_msg = "Response was not JSON"
            return EndpointProbeResult(
                endpoint_url=effective_url,
                reachable=200 <= status < 300,
                http_status=status,
                latency_ms=latency_ms,
                error=error_msg,
            )

        if not isinstance(data, dict):
            error_msg = ""
            if not (200 <= status < 300):
                error_msg = f"HTTP {status}"
            else:
                error_msg = "JSON root was not an object"
            return EndpointProbeResult(
                endpoint_url=effective_url,
                reachable=200 <= status < 300,
                http_status=status,
                latency_ms=latency_ms,
                error=error_msg,
            )

        tools = self._infer_tools(data)
        error_msg = ""
        if not (200 <= status < 300):
            error_msg = f"HTTP {status}"
            if "detail" in data:
                error_msg += f": {data['detail']}"
            elif "error" in data:
                error_msg += f": {data['error']}"

        return EndpointProbeResult(
            endpoint_url=effective_url,
            reachable=200 <= status < 300,
            http_status=status,
            latency_ms=latency_ms,
            response_keys=sorted(data.keys()),
            inferred_tool_names=tools,
            raw_sample=self._redact_sample(data),
            error=error_msg,
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

    def try_fetch_openapi_tools(
        self,
        endpoint_url: str,
        *,
        headers: dict[str, str] | None = None,
    ) -> list[str]:
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
                resp = self._client.get(url, timeout=5.0, headers=headers)
                if resp.status_code != 200:
                    continue
                text = resp.text
                if url.endswith(".json"):
                    spec = json.loads(text)
                    from agenteval.introspect.openapi import OpenAPIIntrospector

                    for tool in OpenAPIIntrospector().extract_tools(spec):
                        names.append(tool.name)
            except Exception:
                continue
        return names

    def close(self) -> None:
        """Close underlying HTTP client if owned by this prober."""
        if getattr(self, "_owns_client", False):
            self._client.close()

    def __enter__(self) -> EndpointProber:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
