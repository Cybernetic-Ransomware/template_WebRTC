FROM python:3.12-slim AS builder

# libsrtp2-dev: headers needed by pylibsrtp (aiortc) if wheel falls back to source compile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsrtp2-dev \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install deps before copying source so Docker reuses this layer on code-only changes
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY backend/ backend/
RUN uv sync --frozen --no-dev --no-editable


FROM python:3.12-slim

# libsrtp2-1: runtime shared lib; curl: used by the compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsrtp2-1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --system --no-create-home appuser

WORKDIR /app

COPY --from=builder /app/.venv .venv

ENV PATH="/app/.venv/bin:$PATH"
USER appuser
EXPOSE 8080

CMD ["python", "-m", "webrtc_template"]
