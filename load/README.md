# Load testing (Locust)

A small Locust-based load-testing harness for Shrinkr. It exercises the two
hot paths (redirect + create) and streams its own request metrics into the
existing Prometheus + Grafana stack, so a load run shows up live on the
**Shrinkr / Locust** dashboard.

## What it measures

| User class     | Weight | Endpoint              | Notes                                                                 |
|----------------|--------|-----------------------|-----------------------------------------------------------------------|
| `RedirectUser` | 9      | `GET /{short_code}`   | Seeds 10 codes on start, then follows random ones. Cache-hot path.    |
| `CreateUser`   | 1      | `POST /v0/shortner/`  | Creates fresh links. 429 is treated as success if the rate-limit headers are all present. |

Metrics exposed on `http://locust:9646/metrics`:

- `locust_requests_total{method, name, status}` — counter
- `locust_request_duration_seconds` — histogram (p50 / p95 / p99 computed in Grafana)
- `locust_users_spawned_total` — counter

## Running it

Everything runs inside Docker Compose via the `load` profile, so the
default `docker compose up` flow is untouched.

```bash
# Start the full stack + Locust
docker compose -f docker/compose.yml --profile load up --build

# Locust web UI
open http://localhost:8089                # admin: none; pick users + spawn rate

# Grafana — Shrinkr / Locust dashboard
open http://localhost:3000                # admin / admin

# Prometheus — confirm the 'locust' target is UP
open http://localhost:9090/targets
```

### Headless (no UI)

```bash
docker compose -f docker/compose.yml --profile load run --rm locust \
  --headless -u 100 -r 10 -t 60s --html /tmp/report.html
```

### Running locally (not in Docker)

```bash
uv sync --group load
uv run locust -f load/locustfile.py --host http://localhost:8000
```

## Tuning the run

Good starting points:

| Goal                               | Users | Spawn rate | Duration |
|------------------------------------|-------|------------|----------|
| Smoke test                         | 10    | 2/s        | 30s      |
| Steady-state redirect load         | 100   | 10/s       | 2m       |
| Provoke the rate limiter           | 200   | 20/s       | 1m       |

## How it plugs into Prometheus + Grafana

1. The Locust container exposes `:9646/metrics` (via `prometheus_client` in
   `locustfile.py`).
2. `docker/prometheus/prometheus.yml` has a `locust` scrape job targeting
   `locust:9646` every 5 seconds.
3. The **Shrinkr / Locust** dashboard is auto-provisioned from
   `docker/grafana/provisioning/dashboards/json/shrinkr-locust.json`.

## Out of scope for this POC

- CI integration (load tests are not good merge gates).
- Distributed master/worker Locust deployments.
- Auth — the API has none.
