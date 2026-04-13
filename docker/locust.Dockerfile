FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml uv.lock ./
# Stub README so the project metadata resolves; we skip installing the project
# itself via --no-install-project, but uv still parses pyproject.toml.
RUN touch README.md \
    && uv sync --group load --frozen --no-install-project

COPY load/ ./load/

ENV PATH="/app/.venv/bin:${PATH}"

EXPOSE 8089 9646

ENTRYPOINT ["locust", "-f", "/app/load/locustfile.py", "--web-host", "0.0.0.0"]
