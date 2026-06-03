"""Tests for the /health route and optional X-API-Key middleware."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from crossref_mcp import __version__
from crossref_mcp.http_auth import ApiKeyMiddleware


def test_health_route_returns_version():
    from crossref_mcp.server import mcp

    app = mcp.streamable_http_app()
    with TestClient(app) as tc:
        resp = tc.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__


def _guarded_app(key: str) -> Starlette:
    async def health(_req):
        return JSONResponse({"status": "ok"})

    async def protected(_req):
        return JSONResponse({"ok": True})

    app = Starlette(routes=[Route("/health", health), Route("/mcp", protected)])
    app.add_middleware(ApiKeyMiddleware, api_key=key)
    return app


def test_api_key_blocks_without_header():
    with TestClient(_guarded_app("secret")) as tc:
        assert tc.get("/mcp").status_code == 401
        assert tc.get("/mcp", headers={"X-API-Key": "wrong"}).status_code == 401
        assert tc.get("/mcp", headers={"X-API-Key": "secret"}).status_code == 200


def test_api_key_health_is_exempt():
    with TestClient(_guarded_app("secret")) as tc:
        # /health passes with no key even when auth is enabled.
        assert tc.get("/health").status_code == 200
