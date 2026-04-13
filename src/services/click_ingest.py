"""Batched click-event ingestion.

The redirect handler enqueues a ``ClickEvent`` per request rather than
awaiting an ``INSERT``. A background consumer drains the queue, flushes
rows in a single multi-row ``INSERT`` on a short interval, and commits.

This removes both the per-click transaction cost (one ``fsync`` per
redirect) and the ``RETURNING`` round-trip from SQLAlchemy's ORM path,
which together were dominating Postgres-side CPU under load.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import structlog
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.orm.models import UrlStats

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class ClickEvent:
    url_id: int
    user_agent: str
    ip_address: str


class ClickIngester:
    """Collects click events in memory and flushes them in batches.

    One instance per worker process. Events are dropped (with a warning
    log) when the queue is full — click analytics is best-effort, and
    unbounded queueing would let the ingester consume memory under
    sustained overload.
    """

    def __init__(
        self,
        engine: AsyncEngine,
        batch_size: int = 100,
        flush_interval: float = 0.1,
        max_queue_size: int = 10_000,
    ) -> None:
        self._engine = engine
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue: asyncio.Queue[ClickEvent] = asyncio.Queue(maxsize=max_queue_size)
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    def enqueue(self, event: ClickEvent) -> None:
        """Fire-and-forget enqueue; drops silently-but-logged if queue is full."""
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("click_ingest_queue_full", dropped_url_id=event.url_id)

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._consume(), name="click-ingester")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._stop.set()
        await self._task
        self._task = None

    async def _consume(self) -> None:
        while not self._stop.is_set():
            batch = await self._collect_batch()
            if batch:
                await self._flush(batch)
        await self._drain_remaining()

    async def _collect_batch(self) -> list[ClickEvent]:
        try:
            first = await asyncio.wait_for(self._queue.get(), timeout=0.5)
        except TimeoutError:
            return []

        batch: list[ClickEvent] = [first]
        loop = asyncio.get_event_loop()
        deadline = loop.time() + self._flush_interval
        while len(batch) < self._batch_size:
            remaining = deadline - loop.time()
            if remaining <= 0:
                break
            try:
                batch.append(
                    await asyncio.wait_for(self._queue.get(), timeout=remaining)
                )
            except TimeoutError:
                break
        return batch

    async def _drain_remaining(self) -> None:
        batch: list[ClickEvent] = []
        while not self._queue.empty():
            batch.append(self._queue.get_nowait())
            if len(batch) >= self._batch_size:
                await self._flush(batch)
                batch = []
        if batch:
            await self._flush(batch)

    async def _flush(self, batch: list[ClickEvent]) -> None:
        rows = [
            {
                "url_id": event.url_id,
                "user_agent": event.user_agent,
                "ip_address": event.ip_address,
            }
            for event in batch
        ]
        try:
            async with self._engine.begin() as conn:
                await conn.execute(insert(UrlStats), rows)
        except Exception:
            logger.exception("click_ingest_flush_failed", batch_size=len(batch))
