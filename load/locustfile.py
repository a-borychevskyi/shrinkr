"""Locust load test for Shrinkr.

Two user classes model the dominant traffic shapes:

- ``RedirectUser`` (weight 9) — seeds a handful of short codes on start and
  then hammers the redirect endpoint. After warmup every hit is a Redis
  cache hit, so this measures the cache-aside fast path.
- ``CreateUser`` (weight 1) — creates new short links and asserts the rate
  limiter behaves correctly when it kicks in (429 + ``Retry-After`` +
  ``X-RateLimit-*`` headers).

Prometheus metrics for the test run are exposed on ``:9646/metrics`` via an
in-process listener. Prometheus scrapes that endpoint and the
``shrinkr-locust`` Grafana dashboard renders the results live.
"""

from __future__ import annotations

import random
import uuid

from locust import FastHttpUser, between, events, task
from prometheus_client import Counter, Histogram, start_http_server

PROMETHEUS_PORT = 9646

REQUEST_COUNT = Counter(
    "locust_requests_total",
    "Total number of Locust-issued requests.",
    ["method", "name", "status"],
)
REQUEST_LATENCY = Histogram(
    "locust_request_duration_seconds",
    "Request latency as observed by Locust.",
    ["method", "name"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
USERS_GAUGE = Counter(
    "locust_users_spawned_total",
    "Cumulative count of spawned users.",
)


@events.init.add_listener
def _start_prometheus_server(environment, **_kwargs) -> None:  # type: ignore[no-untyped-def]
    """Expose Prometheus metrics on ``:9646`` from master/standalone only.

    Workers in a distributed run skip this to avoid fighting for the port.
    """
    runner = getattr(environment, "runner", None)
    if runner is not None and runner.__class__.__name__ == "WorkerRunner":
        return
    start_http_server(PROMETHEUS_PORT)


@events.request.add_listener
def _on_request(  # type: ignore[no-untyped-def]
    request_type,
    name,
    response_time,
    response_length,
    exception,
    **_kwargs,
) -> None:
    status = "success" if exception is None else "failure"
    REQUEST_COUNT.labels(request_type, name, status).inc()
    REQUEST_LATENCY.labels(request_type, name).observe(response_time / 1000.0)


@events.spawning_complete.add_listener
def _on_spawn(user_count, **_kwargs) -> None:  # type: ignore[no-untyped-def]
    USERS_GAUGE.inc(user_count)


SEED_URLS = [
    "https://example.com",
    "https://fastapi.tiangolo.com",
    "https://docs.python.org/3/",
    "https://grafana.com/",
    "https://prometheus.io/",
]


def _random_url() -> str:
    return f"https://load-test.example.com/{uuid.uuid4().hex}"


class RedirectUser(FastHttpUser):
    """Reads. Seeds short codes on start, then GETs the redirect endpoint."""

    weight = 9

    codes: list[str]

    def on_start(self) -> None:
        self.codes = []
        for url in SEED_URLS * 2:
            with self.client.post(
                "/v0/shortner/",
                json={"target_url": url},
                name="POST /v0/shortner/ [seed]",
                catch_response=True,
            ) as response:
                if response.status_code == 201:
                    code = response.json().get("payload", {}).get("short_code")
                    if isinstance(code, str) and code:
                        self.codes.append(code)
                        response.success()
                    else:
                        response.failure("no short_code in seed response")
                elif response.status_code == 429:
                    response.success()
                else:
                    response.failure(f"unexpected seed status {response.status_code}")

    @task
    def follow_redirect(self) -> None:
        if not self.codes:
            return
        code = random.choice(self.codes)
        with self.client.get(
            f"/{code}",
            name="GET /{short_code}",
            allow_redirects=False,
            catch_response=True,
        ) as response:
            if response.status_code == 302:
                response.success()
            else:
                response.failure(f"expected 302, got {response.status_code}")


class CreateUser(FastHttpUser):
    """Writes. POSTs new short URLs; asserts rate-limit behavior on 429."""

    weight = 1
    wait_time = between(0.1, 0.3)

    @task
    def create(self) -> None:
        with self.client.post(
            "/v0/shortner/",
            json={"target_url": _random_url()},
            name="POST /v0/shortner/",
            catch_response=True,
        ) as response:
            if response.status_code == 201:
                response.success()
            elif response.status_code == 429:
                missing = [
                    header
                    for header in (
                        "Retry-After",
                        "X-RateLimit-Limit",
                        "X-RateLimit-Remaining",
                    )
                    if header not in response.headers
                ]
                if missing:
                    response.failure(f"429 missing headers: {missing}")
                else:
                    response.success()
            else:
                response.failure(f"unexpected create status {response.status_code}")
