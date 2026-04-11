# Shrinkr Documentation

**Shrinkr** is a production-grade URL shortener with analytics, built with FastAPI, PostgreSQL, and Redis.

## Quick Start

```bash
# Run with Docker Compose
docker-compose up

# API docs available at
# http://localhost:8000/docs   (Swagger UI)
# http://localhost:8000/redoc  (ReDoc)
```

## Contents

```{toctree}
:maxdepth: 2
:caption: Guide

architecture
api
configuration
```

```{toctree}
:maxdepth: 2
:caption: Reference

apidocs/index
```

## Tech Stack

| Component      | Technology                            |
|----------------|---------------------------------------|
| Framework      | FastAPI (async)                       |
| Database       | PostgreSQL 16 via SQLAlchemy 2.0      |
| Cache          | Redis                                 |
| Observability  | OpenTelemetry + structlog             |
| Infra          | Docker, Kubernetes, Terraform (AWS)   |
| CI/CD          | GitHub Actions                        |
