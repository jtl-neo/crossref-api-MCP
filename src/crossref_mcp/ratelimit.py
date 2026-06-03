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


# Atomic token bucket in a single Lua script. Uses redis TIME as a shared clock
# so all replicas converge on one bucket. Returns {allowed, wait_seconds}.
_LUA_TOKEN_BUCKET = """
local t = redis.call('TIME')
local now = tonumber(t[1]) + tonumber(t[2]) / 1000000
local rate = tonumber(ARGV[1])
local capacity = tonumber(ARGV[2])
local d = redis.call('HMGET', KEYS[1], 'tokens', 'ts')
local tokens = tonumber(d[1])
local ts = tonumber(d[2])
if tokens == nil then tokens = capacity; ts = now end
local elapsed = now - ts
if elapsed < 0 then elapsed = 0 end
tokens = math.min(capacity, tokens + elapsed * rate)
local allowed = 0
local wait = 0
if tokens >= 1 then
  tokens = tokens - 1
  allowed = 1
else
  wait = (1 - tokens) / rate
end
redis.call('HSET', KEYS[1], 'tokens', tokens, 'ts', now)
redis.call('PEXPIRE', KEYS[1], math.ceil((capacity / rate) * 1000) + 1000)
return {allowed, tostring(wait)}
"""


class RedisTokenBucket:
    """Cross-replica token bucket backed by Redis + an atomic Lua script.

    All replicas sharing the same key + Redis converge on one rate. Degrades to
    a local InMemoryTokenBucket if Redis errors.
    """

    def __init__(
        self,
        redis,
        key: str = "crossref-mcp:ratelimit",
        limit: int = DEFAULT_LIMIT,
        interval_s: float = DEFAULT_INTERVAL_S,
    ):
        self._redis = redis
        self._key = key
        self._limit = max(1, limit)
        self._interval = interval_s if interval_s > 0 else DEFAULT_INTERVAL_S
        self._fallback = InMemoryTokenBucket(limit, interval_s)

    @property
    def _rate(self) -> float:
        return self._limit / self._interval

    def update(self, limit: int, interval_s: float) -> None:
        self._limit = max(1, limit)
        self._interval = interval_s if interval_s > 0 else DEFAULT_INTERVAL_S
        self._fallback.update(limit, interval_s)

    async def acquire(self) -> None:
        while True:
            try:
                allowed, wait = await self._redis.eval(
                    _LUA_TOKEN_BUCKET, 1, self._key, self._rate, self._limit
                )
            except Exception:  # noqa: BLE001 - degrade to local bucket
                await self._fallback.acquire()
                return
            if int(allowed) == 1:
                return
            await asyncio.sleep(min(float(wait), self._interval))


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
