FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /bin/

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .


FROM python:3.12-slim

LABEL org.opencontainers.image.title="shrinkr" \
      org.opencontainers.image.description="Production-grade URL shortener with analytics" \
      org.opencontainers.image.source="https://github.com/andriiboryshevskyi/url-shortner"

RUN groupadd --system app && useradd --system --gid app --shell /usr/sbin/nologin app

WORKDIR /app

COPY --from=builder /app/.venv .venv
COPY --from=builder /app/src src
COPY --from=builder /app/alembic alembic
COPY --from=builder /app/alembic.ini .

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/v0/system/health')"

CMD ["gunicorn", "src.main:app", \
    "--bind", "0.0.0.0:8000", \
    "--workers", "4", \
    "--worker-class", "uvicorn.workers.UvicornWorker"]
