"""Unit tests for SSRF URL validation and safe HTTP handlers."""

from unittest.mock import MagicMock, patch

import pytest

from agenteval.security.url_validator import (
    SafeRedirectHandler,
    UnsafeURLError,
    is_private_allowed,
    validate_endpoint_url,
)


def test_valid_public_urls() -> None:
    assert (
        validate_endpoint_url("https://api.openai.com/v1/chat") == "https://api.openai.com/v1/chat"
    )
    assert validate_endpoint_url("http://example.com:8080/agent") == "http://example.com:8080/agent"
    assert (
        validate_endpoint_url("https://agents.enterprise.com/v1")
        == "https://agents.enterprise.com/v1"
    )


def test_invalid_schemes() -> None:
    invalid = [
        "file:///etc/passwd",
        "ftp://ftp.example.com/files",
        "gopher://127.0.0.1:70/",
        "data:text/plain;base64,SGVsbG8=",
        "javascript:alert(1)",
        "ldap://127.0.0.1:389/",
        "",
        "just-a-string",
    ]
    for url in invalid:
        with pytest.raises(UnsafeURLError, match="scheme|valid URL|non-empty"):
            validate_endpoint_url(url)


def test_cloud_metadata_blocked_unconditionally() -> None:
    blocked_targets = [
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://metadata.aws.internal/latest/meta-data/",
        "http://metadata.azure.internal/",
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.169.254:80/computeMetadata/v1/",
        "http://[fd00:ec2::254]/latest/meta-data/",
        "http://[fe80::1]/link-local",
    ]
    for url in blocked_targets:
        # Blocked when private is disallowed
        with pytest.raises(UnsafeURLError, match="Blocked hostname|link-local|metadata"):
            validate_endpoint_url(url, allow_private=False)
        # MUST STILL be blocked even when allow_private=True (cloud metadata is never a valid agent)
        with pytest.raises(UnsafeURLError, match="Blocked hostname|link-local|metadata"):
            validate_endpoint_url(url, allow_private=True)


def test_loopback_and_private_blocked_by_default() -> None:
    private_targets = [
        "http://127.0.0.1:8770/chat",
        "http://localhost:8770/chat",
        "http://0.0.0.0:8000/",
        "http://[::1]:8000/chat",
        "http://10.0.0.5:8000/chat",
        "http://172.16.1.1:8000/chat",
        "http://192.168.1.100:8000/chat",
        "http://[::ffff:127.0.0.1]:8000/chat",
        "http://[::ffff:10.0.0.1]:8000/chat",
    ]
    for url in private_targets:
        with pytest.raises(UnsafeURLError, match="private|loopback|Blocked hostname|unspecified"):
            validate_endpoint_url(url, allow_private=False)


def test_loopback_and_private_allowed_when_explicitly_enabled() -> None:
    private_targets = [
        "http://127.0.0.1:8770/chat",
        "http://localhost:8770/chat",
        "http://10.0.0.5:8000/chat",
        "http://172.16.1.1:8000/chat",
        "http://192.168.1.100:8000/chat",
    ]
    for url in private_targets:
        assert validate_endpoint_url(url, allow_private=True) == url


def test_env_var_private_endpoints(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS", raising=False)
    assert not is_private_allowed()

    monkeypatch.setenv("AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS", "1")
    assert is_private_allowed()

    monkeypatch.setenv("AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS", "true")
    assert is_private_allowed()

    monkeypatch.setenv("AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS", "false")
    assert not is_private_allowed()

    monkeypatch.setenv("AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS", "0")
    assert not is_private_allowed()


def test_dns_resolution_failure_treated_gracefully() -> None:
    # A non-existent hostname that fails DNS lookup should not raise UnsafeURLError
    # (it passes SSRF validation, and let the HTTP client raise standard connection error)
    with patch("socket.getaddrinfo", side_effect=OSError("DNS lookup failed")):
        url = "http://nonexistent-agent-domain-xyz.example/chat"
        assert validate_endpoint_url(url, allow_private=False) == url


def test_safe_redirect_handler_blocks_ssrf_hop() -> None:
    handler = SafeRedirectHandler(allow_private=False)
    req = MagicMock()
    req.get_method.return_value = "GET"
    fp = MagicMock()

    # Safe redirect
    new_req = handler.redirect_request(
        req, fp, 302, "Found", {}, "https://safe-domain.com/new-path"
    )
    assert new_req is not None

    # Malicious redirect to cloud metadata
    with pytest.raises(UnsafeURLError, match="metadata|Blocked"):
        handler.redirect_request(req, fp, 302, "Found", {}, "http://metadata.google.internal/token")

    # Malicious redirect to loopback
    with pytest.raises(UnsafeURLError, match="loopback|private"):
        handler.redirect_request(req, fp, 302, "Found", {}, "http://127.0.0.1:8000/internal")


def test_invalid_ports() -> None:
    with pytest.raises(UnsafeURLError, match="Invalid port"):
        validate_endpoint_url("http://example.com:70000/chat")
    with pytest.raises(UnsafeURLError, match="Invalid port"):
        validate_endpoint_url("http://example.com:0/chat")


def test_missing_hostname() -> None:
    with pytest.raises(UnsafeURLError, match="valid hostname"):
        validate_endpoint_url("http:///chat")


def test_multicast_address() -> None:
    with pytest.raises(UnsafeURLError, match="reserved or non-routable"):
        validate_endpoint_url("http://224.0.0.1/chat")


def test_safe_urlopen_blocks_ssrf() -> None:
    from agenteval.security.url_validator import safe_urlopen

    with pytest.raises(UnsafeURLError):
        safe_urlopen("http://metadata.google.internal/computeMetadata/v1/")


def test_safe_urlopen_executes_safely() -> None:
    from agenteval.security.url_validator import safe_urlopen

    with patch("urllib.request.OpenerDirector.open") as mock_open:
        mock_open.return_value = MagicMock(status=200)
        resp = safe_urlopen("https://api.openai.com/v1/chat", timeout=5.0)
        assert resp.status == 200
        mock_open.assert_called_once()


def test_endpoint_prober_blocks_ssrf() -> None:
    from agenteval.ingest.endpoint_probe import EndpointProber

    prober = EndpointProber(allow_private=False)
    res = prober.probe("http://metadata.google.internal/computeMetadata/v1/")
    assert not res.reachable
    assert "SSRF protection" in res.error

    res_ip = prober.probe("http://169.254.169.254/latest/meta-data/")
    assert not res_ip.reachable
    assert "SSRF protection" in res_ip.error


def test_blackbox_runner_blocks_ssrf() -> None:
    from agenteval.planning.blackbox_runner import BlackboxRunner

    with pytest.raises(UnsafeURLError):
        BlackboxRunner("http://169.254.169.254/computeMetadata/v1/", allow_private=False)

    with pytest.raises(UnsafeURLError):
        BlackboxRunner("http://metadata.google.internal/token", allow_private=False)


def test_http_adapter_blocks_ssrf() -> None:
    from agenteval.adapters.http import HTTPAdapter

    with pytest.raises(UnsafeURLError):
        HTTPAdapter("http://169.254.169.254/computeMetadata/v1/", allow_private=False)


def test_probe_api_route_blocks_ssrf(monkeypatch: pytest.MonkeyPatch) -> None:
    from starlette.testclient import TestClient

    from agenteval.api.app import create_app

    # Ensure private endpoints disallowed in this test
    monkeypatch.setenv("AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS", "0")
    app = create_app()
    client = TestClient(app)

    response = client.post(
        "/v1/endpoints/probe",
        json={"endpoint_url": "http://metadata.google.internal/computeMetadata/v1/"},
    )
    assert response.status_code == 422
    assert "SSRF protection" in response.json()["detail"]
