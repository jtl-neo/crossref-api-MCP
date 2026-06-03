"""Optional Redis response cache (cache-aside).

Caches the *raw upstream envelope* keyed by normalized path+query, so raw and
simplified reads share one entry. Any Redis failure degrades to "no cache" — it
never breaks a tool call. mailto / secrets are excluded from the key.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from crossref_mcp.log import get_logger

log = get_logger("cache")

# Query keys injected for transport/politeness, never semantically meaningful.
_EXCLUDED_KEYS = frozenset({"mailto"})


def normalize_cache_key(namespace: str, path: str, params: dict[str, Any]) -> str:
    """Stable key: namespace + path + sorted semantic params (mailto excluded)."""
    items = sorted((k, str(v)) for k, v in (params or {}).items() if k not in _EXCLUDED_KEYS)
    digest = hashlib.sha256(json.dumps(items, sort_keys=True).encode()).hexdigest()[:24]
    return f"{namespace}:{path}:{digest}"


class ResponseCache:
    """Thin async cache-aside wrapper over a redis.asyncio client."""

    def __init__(self, redis: Any, namespace: str, ttl: int):
        self._redis = redis
        self.namespace = namespace
        self.ttl = ttl

    async def get(self, path: str, params: dict[str, Any]) -> dict | None:
        key = normalize_cache_key(self.namespace, path, params)
        try:
            raw = await self._redis.get(key)
        except Exception as exc:  # noqa: BLE001 - degrade, never propagate
            log.warning("cache get failed (%s); bypassing", exc)
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (ValueError, TypeError):
            return None

    async def set(self, path: str, params: dict[str, Any], value: dict) -> None:
        key = normalize_cache_key(self.namespace, path, params)
        try:
            await self._redis.set(key, json.dumps(value), ex=self.ttl)
        except Exception as exc:  # noqa: BLE001 - degrade, never propagate
            log.warning("cache set failed (%s); skipping", exc)

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:  # noqa: BLE001
            return False


def create_redis(redis_url: str) -> Any:
    """Build a redis.asyncio client. Imported lazily so redis stays optional."""
    from redis import asyncio as aioredis

    return aioredis.from_url(redis_url, decode_responses=True)
