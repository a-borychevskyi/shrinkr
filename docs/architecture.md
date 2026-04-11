# Architecture

## Overview

Shrinkr follows a **layered architecture** with clear separation of concerns:

```
Request → FastAPI Router → Service → Repository → Database / Cache
```

Each layer has a single responsibility and communicates only with its immediate neighbours.

## Layers

### API Layer (`src.api`)

FastAPI routers and Pydantic request/response schemas.  Routes are versioned under
`/api/v0/` to allow future breaking changes without disrupting existing clients.

- **Endpoints** — thin handlers that validate input, call a service, and return a response.
- **Schemas** — Pydantic v2 models for request bodies and JSON responses.
- **Exception handlers** — translate application exceptions into consistent JSON error responses.

### Service Layer (`src.services`)

Business logic lives here.  Services are injected via FastAPI's `Depends()` and
operate on domain models, never on ORM objects directly.

Key services:

- `UrlService` — create, retrieve, soft-delete, and restore shortened URLs.
- `UrlStatsService` — record and query click analytics.

### Repository Layer (`src.repositories`)

Data access abstraction.  Each repository provides CRUD operations for a single
aggregate and is backed by either PostgreSQL (via SQLAlchemy) or Redis (cache).

- `UrlRepository` / `UrlCacheRepository`
- `UrlStatsRepository` / `UrlStatsCacheRepository`

A **Unit of Work** (`src.repositories.uow`) wraps database sessions to guarantee
transactional consistency.

### ORM Layer (`src.orm`)

SQLAlchemy 2.0 mapped classes, plus reusable **filter** and **sorter** models that
translate query parameters into SQLAlchemy `where` / `order_by` clauses.

### Dependency Injection (`src.di`)

Provider functions that wire everything together.  FastAPI's `Depends()` resolves
the full dependency graph at request time — no global state.

## Cross-Cutting Concerns

### Observability

- **Structured logging** via structlog (JSON in production, pretty-print in dev).
- **Distributed tracing** via OpenTelemetry with auto-instrumentation for FastAPI,
  SQLAlchemy, and Redis.
- **Prometheus metrics** for cache hit/miss rates and DB operation counts.

### Rate Limiting

Sliding-window counter algorithm implemented in Redis with a Lua script for
atomicity.  Applied per-IP on link creation; system routes are exempt.

### Caching

Hot links are cached in Redis with a configurable TTL.  On redirect the cache is
checked first; a miss falls through to PostgreSQL.  Cache entries are invalidated
on delete.

## Deployment

```{mermaid}
graph LR
    Client --> ALB[ALB / Ingress]
    ALB --> App[FastAPI<br>ECS / K8s]
    App --> Redis[(Redis)]
    App --> PG[(PostgreSQL)]
```

Infrastructure is defined as code:

- **Docker** — multi-stage build, non-root user, health checks.
- **Kubernetes** — Deployment, Service, Ingress, HPA (2–10 replicas).
- **Terraform** — VPC, RDS, ElastiCache, ECS Fargate, ALB on AWS.
