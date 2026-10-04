"""Target Connection Profiles and Outbound Authentication (Slice 13).

Provides typed models, header synthesis, and secret redaction for authenticating
outbound HTTP requests to target agent endpoints.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

_SENSITIVE_KEY_SUBSTRINGS = (
    "auth",
    "token",
    "secret",
    "key",
    "password",
    "credential",
    "bearer",
)


def mask_secret_value(value: str, visible_chars: int = 4) -> str:
    """Mask sensitive secret string, revealing only a short prefix/suffix if long enough."""
    if not value:
        return ""
    if len(value) <= visible_chars * 2:
        return "***"
    prefix = value[:visible_chars]
    suffix = value[-visible_chars:]
    return f"{prefix}...{suffix}"


def redact_sensitive_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers where any sensitive header value is safely masked."""
    result: dict[str, str] = {}
    for k, v in headers.items():
        k_lower = k.lower()
        if any(substring in k_lower for substring in _SENSITIVE_KEY_SUBSTRINGS):
            if k_lower == "authorization" and v.lower().startswith("bearer "):
                raw_token = v[7:].strip()
                result[k] = f"Bearer {mask_secret_value(raw_token)}"
            else:
                result[k] = mask_secret_value(v)
        else:
            result[k] = v
    return result


class AuthType(StrEnum):
    """Supported authentication strategies for outbound agent endpoints."""

    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    CUSTOM = "custom"


class TargetConnectionProfile(BaseModel):
    """Configuration for connecting and authenticating to an outbound agent target."""

    model_config = ConfigDict(extra="forbid")

    endpoint_url: str = Field(description="Agent endpoint URL")
    auth_type: AuthType = Field(default=AuthType.NONE, description="Authentication scheme")
    header_name: str | None = Field(
        default=None,
        description="Header name (defaults to Authorization for Bearer, X-API-Key for API Key)",
    )
    token_secret: str | None = Field(
        default=None,
        description="Bearer token or API key secret value",
    )
    custom_headers: dict[str, str] = Field(
        default_factory=dict,
        description="Additional custom HTTP headers (e.g. X-Tenant-Id, X-Org-Id)",
    )
    timeout_seconds: float = Field(
        default=15.0,
        ge=1.0,
        le=300.0,
        description="Timeout in seconds for outbound calls to this target",
    )

    def resolve_headers(self) -> dict[str, str]:
        """Synthesize concrete HTTP headers to send with requests to the target agent."""
        headers: dict[str, str] = {"Content-Type": "application/json"}

        # Apply any custom headers first
        headers.update(self.custom_headers)

        # Apply authentication scheme if configured
        if self.auth_type == AuthType.BEARER and self.token_secret:
            target_header = self.header_name or "Authorization"
            headers[target_header] = f"Bearer {self.token_secret}"
        elif self.auth_type == AuthType.API_KEY and self.token_secret:
            target_header = self.header_name or "X-API-Key"
            headers[target_header] = self.token_secret
        elif self.auth_type == AuthType.CUSTOM and self.header_name and self.token_secret:
            headers[self.header_name] = self.token_secret

        return headers

    def to_safe_dict(self) -> dict[str, Any]:
        """Return a dictionary representation with sensitive secret values masked."""
        data = self.model_dump(mode="json")
        if self.token_secret:
            data["token_secret"] = mask_secret_value(self.token_secret)
        if self.custom_headers:
            data["custom_headers"] = redact_sensitive_headers(self.custom_headers)
        return data
