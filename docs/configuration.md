# Configuration

Shrinkr is configured entirely through environment variables, loaded via
[pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).

All settings are defined in `src.config` and can be overridden in a `.env` file at
the project root.

## Application

| Variable          | Default       | Description                     |
|-------------------|---------------|---------------------------------|
| `APP_HOST`        | `0.0.0.0`    | Bind address                    |
| `APP_PORT`        | `8000`        | Bind port                       |
| `APP_LOG_LEVEL`   | `info`        | Log level (debug/info/warning)  |
| `APP_ENVIRONMENT` | `development` | `development` or `production`   |
| `APP_WORKERS`     | `1`           | Uvicorn worker count            |

## Database

| Variable    | Default                       | Description             |
|-------------|-------------------------------|-------------------------|
| `DB_HOST`   | `localhost`                   | PostgreSQL host         |
| `DB_PORT`   | `5432`                        | PostgreSQL port         |
| `DB_USER`   | `postgres`                    | Database user           |
| `DB_PASS`   | `postgres`                    | Database password       |
| `DB_NAME`   | `shrinkr`                     | Database name           |

## Redis

| Variable      | Default     | Description       |
|---------------|-------------|-------------------|
| `REDIS_HOST`  | `localhost` | Redis host        |
| `REDIS_PORT`  | `6379`      | Redis port        |
| `REDIS_DB`    | `0`         | Redis database    |

## Rate Limiter

| Variable               | Default | Description                        |
|------------------------|---------|------------------------------------|
| `RATE_LIMIT_REQUESTS`  | `10`    | Max requests per window            |
| `RATE_LIMIT_WINDOW`    | `60`    | Window size in seconds             |
| `RATE_LIMIT_PREFIX`    | `rl:`   | Redis key prefix for rate limits   |

## OpenTelemetry

| Variable              | Default                          | Description                    |
|-----------------------|----------------------------------|--------------------------------|
| `OTEL_ENDPOINT`       | `http://localhost:4317`          | OTLP collector endpoint        |
| `OTEL_SERVICE_NAME`   | `shrinkr`                        | Service name in traces         |

:::{note}
Refer to the actual `src.config` modules for the canonical list of all settings
and their validators — the tables above cover the most commonly changed values.
:::
