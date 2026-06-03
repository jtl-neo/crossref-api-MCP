"""Optional X-API-Key middleware for the HTTP transport.

Active only when MCP_API_KEY is set. /health is always exempt so container
health checks and external probes keep working. Comparison is timing-safe.
"""

from __future__ import annotations

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

EXEMPT_PATHS = frozenset({"/health"})


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, api_key: str):
        super().__init__(app)
        self.api_key = api_key

    async def dispatch(self, request: Request, call_next):
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)
        provided = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(provided, self.api_key):
            return JSONResponse(
                {"error": {"type": "Unauthorized", "message": "Invalid or missing X-API-Key"}},
                status_code=401,
            )
        return await call_next(request)
