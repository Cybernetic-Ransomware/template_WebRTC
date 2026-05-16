FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libsrtp2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m pip install --upgrade pip --break-system-packages && \
    pip install uv --break-system-packages

COPY ./pyproject.toml ./uv.lock ./
RUN uv sync --no-cache --no-dev --no-install-project

COPY ./backend ./backend
RUN uv sync --no-cache --no-dev


FROM python:3.12-slim AS runtime

LABEL authors="aleksander.marszalki"
LABEL name="webrtc-template-signaling"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libsrtp2-1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

ENV PATH="/app/.venv/bin:/usr/local/bin:$PATH"

WORKDIR /app

COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
RUN chmod -R +x /app/.venv/bin/

COPY --chown=appuser:appgroup ./backend ./backend

USER appuser

EXPOSE 8080/tcp

CMD ["python", "-m", "webrtc_template"]
