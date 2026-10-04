"""Unit tests for Target Connection Profiles, Header Resolution & Secret Masking (Slice 13.1)."""

import pytest
from pydantic import ValidationError

from agenteval.targets.models import (
    AuthType,
    TargetConnectionProfile,
    mask_secret_value,
    redact_sensitive_headers,
)


def test_auth_type_enum() -> None:
    assert AuthType.NONE.value == "none"
    assert AuthType.BEARER.value == "bearer"
    assert AuthType.API_KEY.value == "api_key"
    assert AuthType.CUSTOM.value == "custom"
    assert AuthType("bearer") is AuthType.BEARER


def test_mask_secret_value() -> None:
    assert mask_secret_value("") == ""
    assert mask_secret_value("short") == "***"
    assert mask_secret_value("123456") == "***"

    masked = mask_secret_value("sk-proj-9876543210abcdef")
    assert masked.startswith("sk-p")
    assert masked.endswith("cdef")
    assert "9876543210" not in masked
    assert "..." in masked


def test_redact_sensitive_headers() -> None:
    raw_headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer secret-token-xyz",
        "X-API-Key": "my-api-key-123456",
        "x-custom-secret": "super-private",
        "X-Tenant-Id": "tenant-42",
    }
    redacted = redact_sensitive_headers(raw_headers)
    assert redacted["Content-Type"] == "application/json"
    assert redacted["X-Tenant-Id"] == "tenant-42"
    assert redacted["Authorization"] != "Bearer secret-token-xyz"
    assert "secret-token-xyz" not in redacted["Authorization"]
    assert "123456" not in redacted["X-API-Key"]
    assert "super-private" not in redacted["x-custom-secret"]


def test_profile_defaults() -> None:
    profile = TargetConnectionProfile(endpoint_url="https://agent.example.com/chat")
    assert profile.endpoint_url == "https://agent.example.com/chat"
    assert profile.auth_type == AuthType.NONE
    assert profile.header_name is None
    assert profile.token_secret is None
    assert profile.custom_headers == {}
    assert profile.timeout_seconds == 15.0

    headers = profile.resolve_headers()
    assert headers["Content-Type"] == "application/json"
    assert "Authorization" not in headers


def test_profile_bearer_auth() -> None:
    profile = TargetConnectionProfile(
        endpoint_url="https://agent.example.com/chat",
        auth_type=AuthType.BEARER,
        token_secret="sk-agent-1234567890",
    )
    headers = profile.resolve_headers()
    assert headers["Authorization"] == "Bearer sk-agent-1234567890"
    assert headers["Content-Type"] == "application/json"


def test_profile_api_key_auth_default_header() -> None:
    profile = TargetConnectionProfile(
        endpoint_url="https://agent.example.com/chat",
        auth_type=AuthType.API_KEY,
        token_secret="test-api-key-abc",
    )
    headers = profile.resolve_headers()
    assert headers["X-API-Key"] == "test-api-key-abc"
    assert headers["Content-Type"] == "application/json"


def test_profile_api_key_auth_custom_header() -> None:
    profile = TargetConnectionProfile(
        endpoint_url="https://agent.example.com/chat",
        auth_type=AuthType.API_KEY,
        header_name="X-Custom-Auth",
        token_secret="test-api-key-abc",
    )
    headers = profile.resolve_headers()
    assert headers["X-Custom-Auth"] == "test-api-key-abc"
    assert "X-API-Key" not in headers


def test_profile_custom_auth() -> None:
    profile = TargetConnectionProfile(
        endpoint_url="https://agent.example.com/chat",
        auth_type=AuthType.CUSTOM,
        header_name="X-Gateway-Token",
        token_secret="token-xyz-789",
    )
    headers = profile.resolve_headers()
    assert headers["X-Gateway-Token"] == "token-xyz-789"


def test_profile_with_custom_headers_and_override() -> None:
    profile = TargetConnectionProfile(
        endpoint_url="https://agent.example.com/chat",
        auth_type=AuthType.BEARER,
        token_secret="my-secret-token",
        custom_headers={
            "X-Tenant-Id": "acme-corp",
            "Content-Type": "application/vnd.agent+json",
        },
    )
    headers = profile.resolve_headers()
    assert headers["Authorization"] == "Bearer my-secret-token"
    assert headers["X-Tenant-Id"] == "acme-corp"
    assert headers["Content-Type"] == "application/vnd.agent+json"


def test_profile_to_safe_dict() -> None:
    profile = TargetConnectionProfile(
        endpoint_url="https://agent.example.com/chat",
        auth_type=AuthType.BEARER,
        token_secret="secret-token-abcdef123456",
        custom_headers={
            "X-Tenant-Id": "acme-corp",
            "X-Extra-Secret": "sensitive-value-here",
        },
    )
    safe = profile.to_safe_dict()
    assert safe["endpoint_url"] == "https://agent.example.com/chat"
    assert safe["auth_type"] == "bearer"
    assert safe["token_secret"] != "secret-token-abcdef123456"
    assert "abcdef123456" not in safe["token_secret"]
    assert safe["custom_headers"]["X-Tenant-Id"] == "acme-corp"
    assert safe["custom_headers"]["X-Extra-Secret"] != "sensitive-value-here"


def test_profile_forbids_extra_fields() -> None:
    with pytest.raises(ValidationError):
        TargetConnectionProfile.model_validate(
            {"endpoint_url": "https://example.com", "unknown_field": "invalid"}
        )
