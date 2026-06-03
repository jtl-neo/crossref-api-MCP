# syntax=docker/dockerfile:1

# --- builder: install deps + project into a venv with uv ------------------
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.16 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Dependencies first (cache layer), then the project.
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# --- runtime: slim, non-root --------------------------------------------
FROM python:3.12-slim AS runtime

LABEL org.opencontainers.image.title="crossref-mcp" \
      org.opencontainers.image.description="MCP server wrapping the Crossref REST API" \
      org.opencontainers.image.source="https://github.com/jtl-neo/crossref-api-MCP" \
      org.opencontainers.image.licenses="MIT" \
      io.modelcontextprotocol.server.name="io.github.jtl-neo/crossref-mcp"

RUN useradd --create-home --uid 1000 app
WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src

ENV PATH="/app/.venv/bin:$PATH" \
    MCP_TRANSPORT=http \
    PYTHONUNBUFFERED=1

USER app
EXPOSE 8000
CMD ["crossref-mcp"]
