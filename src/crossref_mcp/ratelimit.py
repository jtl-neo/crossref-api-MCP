"""Rate limiting. In-memory token bucket for now.

The `RateLimiter` protocol is the seam M9 extends with a Redis-backed bucket for
multi-replica deployments — this is single-process / single-replica only.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Protocol

# Fallback when Crossref sends no rate-limit headers (its documented default).
DEFAULT_LIMIT = 50
DEFAULT_INTERVAL_S = 1.0

_INTERVAL_RE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*([smh]?)\s*$")
_UNIT_SECONDS = {"": 1.0, "s": 1.0, "m": 60.0, "h": 3600.0}


def parse_rate_limit_headers(headers) -> tuple[int | None, float | None]:
    """Extract (limit, interval_seconds) from X-Rate-Limit-* response headers.

    Returns (None, None) when absent or unparseable, so callers keep their
    current settings rather than crashing.
    """
    limit_raw = headers.get("X-Rate-Limit-Limit")
    interval_raw = headers.get("X-Rate-Limit-Interval")
    limit: int | None = None
    interval: float | None = None
    if limit_raw and limit_raw.isdigit():
        limit = int(limit_raw)
    if interval_raw:
        m = _INTERVAL_RE.match(interval_raw)
        if m:
            value, unit = float(m.group(1)), m.group(2)
            seconds = value * _UNIT_SECONDS[unit]
            interval = seconds if seconds > 0 else None
    return limit, interval


class RateLimiter(Protocol):
    async def acquire(self) -> None: ...
    def update(self, limit: int, interval_s: float) -> None: ...


class InMemoryTokenBucket:
    """Classic token bucket guarded by an asyncio.Lock."""

    def __init__(self, limit: int = DEFAULT_LIMIT, interval_s: float = DEFAULT_INTERVAL_S):
        self._lock = asyncio.Lock()
        self._configure(limit, interval_s)
        self.tokens = float(self.capacity)
        self.last = time.monotonic()

    def _configure(self, limit: int, interval_s: float) -> None:
        self.capacity = max(1, limit)
        self.refill_rate = self.capacity / interval_s if interval_s > 0 else float(self.capacity)

    def update(self, limit: int, interval_s: float) -> None:
        """Re-tune from observed server headers; never raise the count of held tokens."""
        self._configure(limit, interval_s)
        self.tokens = min(self.tokens, float(self.capacity))

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last
                self.last = now
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return
                deficit = 1.0 - self.tokens
                await asyncio.sleep(deficit / self.refill_rate)
