# Profiling Shrinkr

Shrinkr emits continuous CPU profiles to Grafana Pyroscope. For targeted investigations, attach py-spy to a running container.

## Continuous profiling (Pyroscope)

**Where it runs:**
- `pyroscope` container on `http://localhost:4040` (direct UI) and as a Grafana data source.
- SDK initialized in `src/telemetry.py::setup_profiling`, called from `setup_telemetry()` — so both the API (`src/main.py`) and the worker (`src/worker/main.py`) push profiles.

**Labels on every profile sample:**
- `service_name` — `shrinkr` (API) or `shrinkr-worker` (worker)
- `env` — value of `APP_ENVIRONMENT`
- `instance` — container hostname
- `role` — `api` or `worker`

**Open the flamegraph:**
1. `docker compose -f docker/compose.yml up -d`
2. Open Grafana at `http://localhost:3000` (admin / admin)
3. Dashboards → `Shrinkr — Profiling`
4. For a load-test view, start Locust: `docker compose -f docker/compose.yml --profile load up -d locust` and drive traffic from `http://localhost:8089`

**Disable locally:**

Set `PYROSCOPE_ENABLED=false` in the env for the service you want quiet. Tests always run with profiling disabled via `tests/conftest.py`.

## Ad-hoc flamegraph (py-spy)

Use when Pyroscope shows a suspicious hotspot and you want a focused, higher-resolution sample without redeploying.

```bash
# API
docker exec -it the-app uv run py-spy record -o /tmp/api.svg --pid 1 --duration 30
docker cp the-app:/tmp/api.svg ./api.svg

# Worker
docker exec -it shrinkr-worker uv run py-spy record -o /tmp/worker.svg --pid 1 --duration 30
docker cp shrinkr-worker:/tmp/worker.svg ./worker.svg
```

Open the resulting `.svg` in a browser. py-spy needs no app changes — it attaches via ptrace (already allowed inside the container's own namespace).

**Live top view (no file):**

```bash
docker exec -it the-app uv run py-spy top --pid 1
```

## When to use which

| Question | Tool |
| --- | --- |
| Where does CPU go on average, over time, across all pods? | Pyroscope |
| What is this one process doing right now? | `py-spy top` |
| Capture a 30 s flamegraph during a Locust spike | `py-spy record` |
