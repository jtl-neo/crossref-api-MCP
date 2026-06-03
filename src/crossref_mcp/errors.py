"""Unified error hierarchy for Crossref API interactions.

Naming is fixed here and only *extended* (never renamed) in later milestones,
so existing imports stay stable.
"""

from __future__ import annotations

import httpx


class CrossrefError(Exception):
    """Base class for all Crossref client errors."""

    def __init__(self, message: str, *, status: int | None = None, detail: str | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.detail = detail

    def to_dict(self) -> dict:
        """Render as an MCP-friendly structured error payload."""
        out: dict = {"type": type(self).__name__, "message": self.message}
        if self.status is not None:
            out["status"] = self.status
        if self.detail:
            out["detail"] = self.detail
        return out


class NotFoundError(CrossrefError):
    """404 — DOI / resource does not exist."""


class BadRequestError(CrossrefError):
    """400 / 422 — malformed query or parameters."""


class RateLimitError(CrossrefError):
    """429 — rate limited (after retries are exhausted)."""

    def __init__(self, message: str, *, retry_after: float | None = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class UpstreamError(CrossrefError):
    """5xx — Crossref server-side error."""


class TimeoutError(CrossrefError):  # noqa: A001 - intentional domain-specific name
    """Network timeout / connection error."""


def _truncate(text: str, limit: int = 300) -> str:
    text = text.strip()
    return text if len(text) <= limit else text[:limit] + "…"


def error_from_response(response: httpx.Response, *, context: str | None = None) -> CrossrefError:
    """Map an HTTP response to the appropriate CrossrefError subclass."""
    status = response.status_code
    body = _truncate(response.text)
    where = f" ({context})" if context else ""
    if status == 404:
        return NotFoundError(f"Not found{where}", status=status, detail=body)
    if status in (400, 422):
        return BadRequestError(f"Bad request{where}", status=status, detail=body)
    if status == 429:
        retry_after = response.headers.get("Retry-After")
        ra = float(retry_after) if retry_after and retry_after.isdigit() else None
        return RateLimitError(f"Rate limited{where}", status=status, detail=body, retry_after=ra)
    if status >= 500:
        return UpstreamError(f"Upstream error{where}", status=status, detail=body)
    return CrossrefError(f"HTTP {status}{where}", status=status, detail=body)
