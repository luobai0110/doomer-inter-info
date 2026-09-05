# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PYTHON=/usr/local/bin/python \
    UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY data ./data
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.14-slim-bookworm

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Shanghai
WORKDIR /app

RUN apt-get update \
 && apt-get install -y --no-install-recommends tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
 && echo $TZ > /etc/timezone \
 && groupadd --system --gid 10001 inter-info \
 && useradd --system --uid 10001 --gid 10001 --no-create-home --home-dir /app --shell /usr/sbin/nologin inter-info \
 && mkdir -p /var/logs/inter \
 && chown inter-info:inter-info /app /var/logs/inter

COPY --from=builder --chown=inter-info:inter-info /app/.venv /app/.venv
COPY --from=builder --chown=inter-info:inter-info /app/app /app/app
COPY --from=builder --chown=inter-info:inter-info /app/data /app/data

USER inter-info
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
