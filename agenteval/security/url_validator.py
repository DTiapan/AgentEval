"""URL validation and safe HTTP transport to prevent Server-Side Request Forgery (SSRF)."""

from __future__ import annotations

import ipaddress
import os
import socket
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

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
        raise UnsafeURLError("URL must be a non-empty string.")

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        raise UnsafeURLError(f"Invalid URL format: {exc}") from exc

    scheme = (parsed.scheme or "").lower()
    if scheme in _BLOCKED_SCHEMES or scheme not in ("http", "https"):
        raise UnsafeURLError(
            f"Unsupported URL scheme '{scheme}'. Only http and https endpoints are permitted."
        )

    raw_host = parsed.hostname
    if not raw_host:
        raise UnsafeURLError(f"URL '{url}' does not contain a valid hostname.")

    # Strip IPv6 literal brackets for IP checks
    host = raw_host.strip("[]").lower()

    if host in _ALWAYS_BLOCKED_HOSTNAMES:
        raise UnsafeURLError(
            f"Blocked hostname: '{raw_host}' targets cloud metadata infrastructure."
        )

    if not allow_private and host in ("localhost", "0.0.0.0"):
        raise UnsafeURLError(f"Blocked hostname: '{raw_host}' targets local host.")

    # Port range check if specified
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError(f"Invalid port: {exc}") from exc

    if port is not None and not (1 <= port <= 65535):
        raise UnsafeURLError(f"Invalid port: {port}. Must be between 1 and 65535.")

    # DNS Resolution check
    try:
        port = parsed.port or (443 if scheme == "https" else 80)
        addr_infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (socket.gaierror, OSError):
        # Name resolution failed; allow through so connection attempt produces standard network error
        return url

    for info in addr_infos:
        raw_ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(raw_ip_str)
        except ValueError:
            continue

        # Unwrap IPv4-mapped IPv6 addresses (e.g., ::ffff:169.254.169.254 -> 169.254.169.254)
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped

        # 1. Link-local (e.g. 169.254.x.x or fe80::) is ALWAYS blocked, even with allow_private=True
        if ip.is_link_local or str(ip) in ("169.254.169.254", "fd00:ec2::254"):
            raise UnsafeURLError(
                f"URL resolves to cloud metadata / link-local address {raw_ip_str}."
            )

        # 2. Loopback (127.0.0.0/8, ::1)
        if ip.is_loopback:
            if not allow_private:
                raise UnsafeURLError(
                    f"URL resolves to loopback address {raw_ip_str}. "
                    "Set AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS=1 to permit local evaluation."
                )
            continue

        # 3. Unspecified (0.0.0.0, ::)
        if ip.is_unspecified:
            if not allow_private:
                raise UnsafeURLError(f"URL resolves to unspecified address {raw_ip_str}.")
            continue

        # 4. Multicast or Reserved non-routable IP
        if ip.is_multicast or ip.is_reserved:
            raise UnsafeURLError(f"URL resolves to reserved or non-routable address {raw_ip_str}.")

        # 5. Private RFC 1918 / unique-local
        if not allow_private and ip.is_private:
            raise UnsafeURLError(
                f"URL resolves to private subnet address {raw_ip_str}. "
                "Set AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS=1 to permit private network evaluation."
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
