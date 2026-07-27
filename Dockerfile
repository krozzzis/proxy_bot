# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

# Install dependencies first, separately from the project code, so the
# dependency layer stays cached across code-only changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev


FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends gosu \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system bot && useradd --system --gid bot --create-home bot

WORKDIR /app
COPY --from=builder --chown=bot:bot /app/.venv /app/.venv
COPY --from=builder --chown=bot:bot /app/locales /app/locales
COPY --from=builder --chown=bot:bot /app/src /app/src
COPY --from=builder --chown=bot:bot /app/pyproject.toml /app/pyproject.toml
COPY --chmod=755 docker-entrypoint.sh /docker-entrypoint.sh

ENV PATH="/app/.venv/bin:$PATH" \
    DATA_DIR=/app/data \
    LOGS_DIR=/app/logs \
    LOCALES_DIR=/app/locales \
    PYTHONUNBUFFERED=1

RUN mkdir -p /app/data /app/logs && chown -R bot:bot /app/data /app/logs

VOLUME ["/app/data", "/app/logs"]

# Stays root here so the entrypoint can fix bind-mounted volume ownership,
# then drops to "bot" via gosu before actually running the app.
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["proxy-bot"]
