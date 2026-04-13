"""Tiny Starlette app exposing /health, /ready, /metrics for the worker.

Runs on the asyncio event loop in the worker process. The poll loop
runs in a separate thread, so this server stays responsive even when
a Postgres flush is slow.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route


def build_app(
    is_poll_thread_alive: Callable[[], bool],
    is_ready: Callable[[], bool],
) -> Starlette:
    """Construct the worker's HTTP app.

    `is_poll_thread_alive` — used by /health (liveness). If the poll
    thread has died, K8s should restart the pod.

    `is_ready` — used by /ready (readiness). Should return True only
    once the consumer has joined the group AND the DB is reachable.
    """

    async def health(_request: Request) -> Response:
        if is_poll_thread_alive():
            return PlainTextResponse("ok")
        return PlainTextResponse("poll thread dead", status_code=503)

    async def ready(_request: Request) -> Response:
        if is_ready():
            return PlainTextResponse("ready")
        return PlainTextResponse("not ready", status_code=503)

    async def metrics(_request: Request) -> Response:
        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    return Starlette(
        routes=[
            Route("/health", health),
            Route("/ready", ready),
            Route("/metrics", metrics),
        ]
    )


def is_thread_alive(thread: threading.Thread) -> Callable[[], bool]:
    """Adapter to bind a Thread reference into a no-arg callable."""
    return thread.is_alive
