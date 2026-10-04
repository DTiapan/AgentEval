"""HTTP/REST agent adapter for Bring Your Own Agent (BYOA) endpoints."""

from __future__ import annotations

import json
from typing import Any

import httpx

from agenteval.adapters.base import AgentAdapter
from agenteval.core.models import StepRecord, ToolCall
from agenteval.security.url_validator import (
    create_safe_client,
    is_private_allowed,
    validate_endpoint_url,
)


class HTTPAdapter(AgentAdapter):
    """Wraps an external HTTP/REST agent endpoint as an evaluatable target."""

    def __init__(
        self,
        endpoint_url: str,
        headers: dict[str, str] | None = None,
        timeout_seconds: float = 30.0,
        agent_id: str = "http-agent",
        allow_private: bool | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self.allow_private = is_private_allowed() if allow_private is None else allow_private
        validate_endpoint_url(endpoint_url, allow_private=self.allow_private)
        self.endpoint_url = endpoint_url
        self.headers = headers or {"Content-Type": "application/json"}
        self.timeout_seconds = timeout_seconds
        self.agent_id = agent_id
        if client is not None:
            self._client = client
            self._owns_client = False
        else:
            self._client = create_safe_client(
                allow_private=self.allow_private,
                timeout=self.timeout_seconds,
                headers=self.headers,
            )
            self._owns_client = True

    def step(
        self,
        user_prompt: str,
        history: list[StepRecord],
    ) -> tuple[str | None, list[ToolCall], bool]:
        """Send prompt and history to external HTTP endpoint and parse response."""
        payload: dict[str, Any] = {
            "prompt": user_prompt,
            "history": [
                {
                    "step_number": s.step_number,
                    "thought": s.thought,
                    "tool_calls": [tc.model_dump() for tc in s.tool_calls],
                    "tool_results": [tr.model_dump() for tr in s.tool_results],
                }
                for s in history
            ],
            "messages": [
                {"role": "user", "content": user_prompt},
                *[{"role": "assistant", "content": s.thought or ""} for s in history if s.thought],
            ],
        }

        try:
            resp = self._client.post(self.endpoint_url, json=payload)
            data = resp.json()
        except Exception as e:
            raise RuntimeError(f"HTTP request failed for {self.endpoint_url}: {e}") from e

        return self._parse_response(data)

    def _parse_response(self, data: dict[str, Any]) -> tuple[str | None, list[ToolCall], bool]:
        """Parse standardized or OpenAI-compatible agent response."""
        # 1. Standard format
        if "thought" in data or "tool_calls" in data:
            thought = data.get("thought")
            is_finished = bool(data.get("is_finished", False))
            raw_tools = data.get("tool_calls", [])
            tool_calls: list[ToolCall] = []
            for i, rt in enumerate(raw_tools):
                cid = rt.get("call_id") or rt.get("id") or f"http-call-{i}"
                tname = rt.get("tool_name") or rt.get("name", "unknown_tool")
                tool_calls.append(
                    ToolCall(
                        call_id=cid,
                        tool_name=tname,
                        arguments=rt.get("arguments", {}),
                        idempotency_key=rt.get("idempotency_key"),
                    )
                )
            if "is_finished" not in data and not tool_calls:
                is_finished = True
            return thought, tool_calls, is_finished

        # 2. OpenAI chat completion format
        if "choices" in data and isinstance(data["choices"], list) and len(data["choices"]) > 0:
            choice = data["choices"][0]
            message = choice.get("message", {})
            thought = message.get("content")
            raw_tools = message.get("tool_calls") or []
            tool_calls = []
            for i, rt in enumerate(raw_tools):
                cid = rt.get("id", f"call-{i}")
                fn = rt.get("function", {})
                tname = fn.get("name", "unknown_tool")
                raw_args = fn.get("arguments", {})
                if isinstance(raw_args, str):
                    try:
                        args = json.loads(raw_args)
                    except Exception:
                        args = {"raw": raw_args}
                else:
                    args = raw_args
                tool_calls.append(
                    ToolCall(
                        call_id=cid,
                        tool_name=tname,
                        arguments=args,
                    )
                )
            finish_reason = choice.get("finish_reason")
            is_finished = finish_reason == "stop" or (not tool_calls and bool(thought))
            return thought, tool_calls, is_finished

        # 3. Simple text response
        reply = data.get("reply") or data.get("output") or data.get("response") or str(data)
        return str(reply), [], True

    def close(self) -> None:
        """Close underlying HTTP client if owned by this adapter."""
        if getattr(self, "_owns_client", False):
            self._client.close()

    def __enter__(self) -> HTTPAdapter:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
