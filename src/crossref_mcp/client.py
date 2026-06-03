"""Async Crossref API client: polite pool, basic retry, error mapping.

Full token-bucket rate limiting and dynamic header-based throttling land in M4;
a hook (`_throttle`) is left here as the extension point.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from crossref_mcp import __version__
from crossref_mcp.config import Settings, get_settings
from crossref_mcp.errors import CrossrefError, TimeoutError, error_from_response
from crossref_mcp.log import get_logger
from crossref_mcp.normalize import normalize_doi
from crossref_mcp.ratelimit import (
    InMemoryTokenBucket,
    RateLimiter,
    parse_rate_limit_headers,
)

log = get_logger("client")

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class CrossrefClient:
    """Thin async wrapper over the Crossref REST API."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        max_retries: int = 3,
        limiter: RateLimiter | None = None,
        backoff_base: float = 0.5,
        backoff_max: float = 8.0,
    ):
        self.settings = settings or get_settings()
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.backoff_max = backoff_max
        self.limiter = limiter or InMemoryTokenBucket()
        self._client = httpx.AsyncClient(
            base_url=self.settings.crossref_base_url,
            timeout=self.settings.crossref_timeout,
            headers=self._default_headers(),
        )
        if not self.settings.crossref_mailto:
            log.warning(
                "CROSSREF_MAILTO is not set; requests use the low-priority pool. "
                "Set it to join Crossref's polite pool."
            )

    def _default_headers(self) -> dict[str, str]:
        mailto = self.settings.crossref_mailto
        ua = f"crossref-mcp/{__version__}"
        if mailto:
            ua += f" (mailto:{mailto})"
        headers = {"User-Agent": ua}
        if self.settings.crossref_plus_token:
            # Sent alongside the UA, never replacing it.
            headers["Crossref-Plus-API-Token"] = self.settings.crossref_plus_token
        return headers

    async def _throttle(self) -> None:
        """Block until the rate limiter grants a token."""
        await self.limiter.acquire()

    def _update_limiter(self, resp: httpx.Response) -> None:
        limit, interval = parse_rate_limit_headers(resp.headers)
        if limit is not None and interval is not None:
            self.limiter.update(limit, interval)

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        """GET a path, always injecting mailto, with token-bucket throttling and
        exponential backoff retry (honoring Retry-After on 429)."""
        query = dict(params or {})
        if self.settings.crossref_mailto:
            query.setdefault("mailto", self.settings.crossref_mailto)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            await self._throttle()
            retry_after: float | None = None
            try:
                resp = await self._client.get(path, params=query)
            except httpx.TimeoutException as exc:
                last_exc = TimeoutError(f"Request timed out: {path}", detail=str(exc))
                log.warning("timeout on %s (attempt %d)", path, attempt + 1)
            except httpx.TransportError as exc:
                last_exc = TimeoutError(f"Connection error: {path}", detail=str(exc))
                log.warning("transport error on %s (attempt %d)", path, attempt + 1)
            else:
                self._update_limiter(resp)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code not in _RETRYABLE_STATUS:
                    # 404 / 400 etc — do not retry.
                    raise error_from_response(resp, context=path)
                err = error_from_response(resp, context=path)
                last_exc = err
                retry_after = getattr(err, "retry_after", None)
                log.warning("retryable %d on %s (attempt %d)", resp.status_code, path, attempt + 1)

            if attempt < self.max_retries:
                backoff = min(self.backoff_base * 2**attempt, self.backoff_max)
                await asyncio.sleep(retry_after if retry_after is not None else backoff)

        assert last_exc is not None
        raise last_exc

    # --- works endpoints -------------------------------------------------

    async def search_works(self, params: dict[str, Any]) -> dict:
        return await self._get("/works", params)

    async def get_work(self, doi: str) -> dict:
        data = await self._get(f"/works/{normalize_doi(doi)}")
        return data.get("message", data)

    async def get_work_agency(self, doi: str) -> dict:
        data = await self._get(f"/works/{normalize_doi(doi)}/agency")
        return data.get("message", data)

    # --- generic resource endpoints (M3) --------------------------------

    async def get_resource_list(self, resource: str, params: dict[str, Any]) -> dict:
        """GET /{resource} — returns the full envelope (has message.items)."""
        return await self._get(f"/{resource}", params)

    async def get_resource(self, resource: str, ident: str) -> dict:
        """GET /{resource}/{id} — returns the inner message."""
        data = await self._get(f"/{resource}/{ident}")
        return data.get("message", data)

    async def get_resource_works(self, resource: str, ident: str, params: dict[str, Any]) -> dict:
        """GET /{resource}/{id}/works — returns the full envelope."""
        return await self._get(f"/{resource}/{ident}/works", params)

    # --- lifecycle -------------------------------------------------------

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> CrossrefClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()


__all__ = ["CrossrefClient", "CrossrefError"]
