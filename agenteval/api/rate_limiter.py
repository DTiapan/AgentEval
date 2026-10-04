"""Sliding-window in-memory rate limiter for compute- and token-intensive API endpoints."""

from __future__ import annotations

import os
import threading
import time

from fastapi import HTTPException, Request


def is_rate_limiting_enabled() -> bool:
    val = os.getenv("AGENTEVAL_RATE_LIMIT_ENABLED", "1").lower()
    return val not in ("0", "false", "no", "off")


class SlidingWindowRateLimiter:
    """Thread-safe sliding-window rate limiter per client IP or API key."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        name: str = "request",
        window_seconds: float = 60.0,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.name = name
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    def _resolve_client(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"key:{api_key[:12]}"
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return f"bearer:{auth[7:19]}"
        if request.client and request.client.host:
            return f"ip:{request.client.host}"
        return "ip:anonymous"

    def __call__(self, request: Request) -> None:
        if not is_rate_limiting_enabled():
            return

        client_id = self._resolve_client(request)
        now = time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            # Purge stale requests for this client
            timestamps = [t for t in self._hits.get(client_id, []) if t > cutoff]

            if len(timestamps) >= self.requests_per_minute:
                oldest = timestamps[0]
                retry_after = max(1, int(self.window_seconds - (now - oldest)) + 1)
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for {self.name}. Max {self.requests_per_minute} requests per {int(self.window_seconds)}s. Try again in {retry_after}s.",
                    headers={"Retry-After": str(retry_after)},
                )

            timestamps.append(now)
            self._hits[client_id] = timestamps

            # Memory safeguard: prune idle clients if dictionary grows
            if len(self._hits) > 2000:
                self._prune_stale(cutoff)

    def _prune_stale(self, cutoff: float) -> None:
        stale_keys = [k for k, ts in self._hits.items() if not ts or max(ts) <= cutoff]
        for k in stale_keys:
            self._hits.pop(k, None)

    def reset(self) -> None:
        """Clear all in-memory rate limiting state (for testing)."""
        with self._lock:
            self._hits.clear()


# Default instances for sensitive routes
probe_limiter = SlidingWindowRateLimiter(
    requests_per_minute=int(os.getenv("AGENTEVAL_RATE_LIMIT_PROBE_RPM", "60")),
    name="endpoint probe",
)

preview_limiter = SlidingWindowRateLimiter(
    requests_per_minute=int(os.getenv("AGENTEVAL_RATE_LIMIT_PREVIEW_RPM", "20")),
    name="suite preview",
)
