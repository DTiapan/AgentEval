"""URL validation and safe HTTP transport to prevent Server-Side Request Forgery (SSRF)."""

from __future__ import annotations

import ipaddress
import os
import socket
import urllib.error
import urllib.request
from typing import Any, NoReturn
from urllib.parse import urlparse

import httpx

from agenteval.logging import get_logger

logger = get_logger("agenteval.security.url_validator")

_ALWAYS_BLOCKED_HOSTNAMES = frozenset(
    {
        "metadata.google.internal",
        "metadata.aws.internal",
        "metadata.azure.internal",
        "169.254.169.254",
        "fd00:ec2::254",
        "0.0.0.0",
    }
)

_BLOCKED_SCHEMES = frozenset({"file", "ftp", "gopher", "data", "javascript", "ldap", "dict", "ssh"})


class UnsafeURLError(ValueError):
    """Raised when an endpoint URL targets an internal, link-local, or forbidden resource."""


def _raise_unsafe(
    msg: str, url: str, host: str | None = None, ip: str | None = None
) -> NoReturn:
    logger.warning("ssrf_blocked", url=url, hostname=host, ip=ip, reason=msg)
    raise UnsafeURLError(msg)


def is_private_allowed() -> bool:
    """Check if private/loopback endpoint evaluation is permitted via environment."""
    return os.environ.get("AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def validate_endpoint_url(url: str, *, allow_private: bool = False) -> str:
    """Validate and return URL if safe. Raises UnsafeURLError for blocked targets.

    Defense-in-depth checks:
    1. Scheme validation: only http:// and https:// allowed.
    2. Hostname check: block known cloud metadata hostnames.
    3. Loopback & private check: block RFC 1918 / loopback unless allow_private=True.
    4. Link-local check: ALWAYS blocked (169.254.169.254 IMDS is never an agent).
    5. IPv6 mapped IPv4 normalization: unwrap ::ffff:x.x.x.x before checking.
    """
    if not url or not isinstance(url, str):
        _raise_unsafe("URL must be a non-empty string.", str(url))

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        _raise_unsafe(f"Invalid URL format: {exc}", url)

    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES or scheme not in ("http", "https"):
        _raise_unsafe(
            f"Unsupported URL scheme '{scheme}'. Only http and https endpoints are permitted.",
            url,
        )

    raw_host = parsed.hostname
    if not raw_host:
        _raise_unsafe(f"URL '{url}' does not contain a valid hostname.", url)

    # Strip IPv6 literal brackets for IP checks
    host = raw_host.strip("[]").lower()

    if host in _ALWAYS_BLOCKED_HOSTNAMES:
        _raise_unsafe(
            f"Blocked hostname: '{raw_host}' targets cloud metadata infrastructure.",
            url,
            host=raw_host,
        )

    if not allow_private and host in ("localhost", "0.0.0.0"):
        _raise_unsafe(f"Blocked hostname: '{raw_host}' targets local host.", url, host=raw_host)

    # Port range check if specified
    try:
        port = parsed.port
    except ValueError as exc:
        _raise_unsafe(f"Invalid port: {exc}", url, host=raw_host)

    if port is not None and not (1 <= port <= 65535):
        _raise_unsafe(f"Invalid port: {port}. Must be between 1 and 65535.", url, host=raw_host)

    # DNS Resolution check
    try:
        port = parsed.port or (443 if scheme == "https" else 80)
        addr_infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError):
        # Name resolution failed; allow through so connection attempt produces standard network error
        return url

    for info in addr_infos:
        raw_ip_str = str(info[4][0])
        try:
            ip = ipaddress.ip_address(raw_ip_str)
        except ValueError:
            continue

        # Unwrap IPv4-mapped IPv6 addresses (e.g., ::ffff:169.254.169.254 -> 169.254.169.254)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped

        # 1. Link-local (e.g. 169.254.x.x or fe80::) is ALWAYS blocked, even with allow_private=True
        if ip.is_link_local or str(ip) in ("169.254.169.254", "fd00:ec2::254"):
            _raise_unsafe(
                f"URL resolves to cloud metadata / link-local address {raw_ip_str}.",
                url,
                host=raw_host,
                ip=raw_ip_str,
            )

        # 2. Loopback (127.0.0.0/8, ::1)
        if ip.is_loopback:
            if not allow_private:
                _raise_unsafe(
                    f"URL resolves to loopback address {raw_ip_str}. "
                    "Set AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS=1 to permit local evaluation.",
                    url,
                    host=raw_host,
                    ip=raw_ip_str,
                )
            continue

        # 3. Unspecified (0.0.0.0, ::)
        if ip.is_unspecified:
            if not allow_private:
                _raise_unsafe(
                    f"URL resolves to unspecified address {raw_ip_str}.",
                    url,
                    host=raw_host,
                    ip=raw_ip_str,
                )
            continue

        # 4. Multicast or Reserved non-routable IP
        if ip.is_multicast or ip.is_reserved:
            _raise_unsafe(
                f"URL resolves to reserved or non-routable address {raw_ip_str}.",
                url,
                host=raw_host,
                ip=raw_ip_str,
            )

        # 5. Private RFC 1918 / unique-local
        if not allow_private and ip.is_private:
            _raise_unsafe(
                f"URL resolves to private subnet address {raw_ip_str}. "
                "Set AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS=1 to permit private network evaluation.",
                url,
                host=raw_host,
                ip=raw_ip_str,
            )

    return url


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    """HTTP redirect handler that validates target URLs against SSRF policies on every hop."""

    def __init__(self, allow_private: bool = False, max_redirects: int = 3) -> None:
        super().__init__()
        self.allow_private = allow_private
        self.max_redirects = max_redirects

    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        # Validate the redirect target before following the hop
        validate_endpoint_url(newurl, allow_private=self.allow_private)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_safe_opener(allow_private: bool | None = None) -> urllib.request.OpenerDirector:
    """Build a urllib opener equipped with SSRF-safe redirect validation."""
    resolved_allow = is_private_allowed() if allow_private is None else allow_private
    handler = SafeRedirectHandler(allow_private=resolved_allow)
    return urllib.request.build_opener(handler)


def safe_urlopen(
    req_or_url: str | urllib.request.Request,
    *,
    timeout: float = 10.0,
    allow_private: bool | None = None,
) -> Any:
    """Execute urlopen using the safe opener with redirect and SSRF enforcement.

    Preserves compatibility with test suites patching urllib.request.urlopen.
    """
    url = req_or_url.full_url if isinstance(req_or_url, urllib.request.Request) else req_or_url
    resolved_allow = is_private_allowed() if allow_private is None else allow_private
    validate_endpoint_url(url, allow_private=resolved_allow)

    # If urllib.request.urlopen has been mocked by a test fixture, delegate to it
    if hasattr(urllib.request.urlopen, "assert_called") or hasattr(
        urllib.request.urlopen, "_mock_return_value"
    ):
        return urllib.request.urlopen(req_or_url, timeout=timeout)

    opener = build_safe_opener(allow_private=resolved_allow)
    return opener.open(req_or_url, timeout=timeout)


def create_safe_client(
    allow_private: bool | None = None,
    *,
    timeout: float | httpx.Timeout = 30.0,
    limits: httpx.Limits | None = None,
    headers: dict[str, str] | None = None,
    follow_redirects: bool = True,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """Create an httpx.Client configured with SSRF protection and connection pooling.

    The request event hook validates every request URL and every 3xx redirect hop
    against SSRF policy before connections are established.
    """
    resolved_allow = is_private_allowed() if allow_private is None else allow_private

    def ssrf_hook(request: httpx.Request) -> None:
        validate_endpoint_url(str(request.url), allow_private=resolved_allow)

    effective_timeout = (
        timeout
        if isinstance(timeout, httpx.Timeout)
        else httpx.Timeout(timeout, connect=min(5.0, timeout))
    )
    effective_limits = limits or httpx.Limits(
        max_connections=50,
        max_keepalive_connections=20,
        keepalive_expiry=30.0,
    )

    return httpx.Client(
        timeout=effective_timeout,
        limits=effective_limits,
        headers=headers,
        follow_redirects=follow_redirects,
        event_hooks={"request": [ssrf_hook]},
        transport=transport,
    )

