"""Kafka consumer + Postgres bulk-insert worker.

confluent_kafka.Consumer.poll() is sync and blocking. We run the poll
loop in a dedicated thread (`run_poll_loop`) and bridge the resulting
batches back to the asyncio event loop via run_coroutine_threadsafe,
which lets the worker's HTTP server (Starlette on the asyncio loop)
keep responding to liveness probes during slow Postgres flushes.

Commit semantics: at-least-once. We only commit offsets after a
successful Postgres insert. A worker crash mid-flow can cause
duplicate inserts on the next read — acceptable for click counts.
The reverse (commit-before-insert) would lose clicks on crash.
"""

from __future__ import annotations

import asyncio
import threading
from time import perf_counter
from typing import Any, Protocol

import structlog

from src.kafka.metrics import (
    CLICKS_BATCH_SIZE,
    CLICKS_CONSUMED_TOTAL,
    CLICKS_FLUSH_DURATION_SECONDS,
    CLICKS_INSERTED_TOTAL,
    CLICKS_MALFORMED_TOTAL,
    KAFKA_CONSUMER_LAG,
)
from src.kafka.schema import ClickEvent, decode_click_event
from src.worker.batcher import Batcher
from src.worker.repository import UrlStatsBulkRepository

logger = structlog.get_logger(__name__)


class _KafkaConsumerProtocol(Protocol):
    def poll(self, timeout: float) -> Any: ...
    def commit(self, message: Any = None, asynchronous: bool = True) -> None: ...
    def close(self) -> None: ...
    def assignment(self) -> list[Any]: ...
    def get_watermark_offsets(
        self, partition: Any, timeout: float = 5.0
    ) -> tuple[int, int]: ...
    def position(self, partitions: list[Any]) -> list[Any]: ...


class ClickConsumer:
    def __init__(
        self,
        consumer: _KafkaConsumerProtocol,
        repository: UrlStatsBulkRepository,
        batch_size: int,
        flush_interval_seconds: float,
        poll_timeout_seconds: float = 0.5,
    ) -> None:
        self._consumer = consumer
        self._repository = repository
        self._batcher: Batcher[ClickEvent] = Batcher(
            max_size=batch_size, max_linger_seconds=flush_interval_seconds
        )
        self._poll_timeout = poll_timeout_seconds
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run_poll_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Blocking poll loop intended to run in its own thread."""
        try:
            while not self._stop.is_set():
                msg = self._consumer.poll(timeout=self._poll_timeout)
                if msg is not None and msg.error() is None:
                    CLICKS_CONSUMED_TOTAL.labels(partition=str(msg.partition())).inc()
                    event = self._decode_or_skip(msg)
                    if event is not None:
                        self._batcher.add(event)
                if self._batcher.should_flush():
                    batch = self._batcher.drain()
                    self._submit_flush(loop, batch)

            # Drain on shutdown.
            if len(self._batcher) > 0:
                self._submit_flush(loop, self._batcher.drain())
            self._update_lag_gauge()
        finally:
            self._consumer.close()

    def _submit_flush(
        self, loop: asyncio.AbstractEventLoop, batch: list[ClickEvent]
    ) -> None:
        """Bridge a batch from the poll thread to the asyncio loop, blocking on completion."""
        future = asyncio.run_coroutine_threadsafe(self._flush_batch(batch), loop)
        try:
            future.result()  # Block — we want backpressure, not parallel flushes.
        except Exception:
            logger.exception("click_flush_failed", batch_size=len(batch))
            # Don't commit; next poll re-reads same offsets.
        self._update_lag_gauge()

    async def _flush_batch(self, batch: list[ClickEvent]) -> None:
        if not batch:
            return
        CLICKS_BATCH_SIZE.observe(len(batch))
        start = perf_counter()
        await self._repository.insert_many(batch)
        CLICKS_FLUSH_DURATION_SECONDS.observe(perf_counter() - start)
        CLICKS_INSERTED_TOTAL.inc(len(batch))
        # Only commit after successful insert — at-least-once semantics.
        self._consumer.commit(asynchronous=False)

    def _decode_or_skip(self, msg: Any) -> ClickEvent | None:
        try:
            return decode_click_event(msg.value())
        except ValueError as exc:
            CLICKS_MALFORMED_TOTAL.inc()
            logger.warning(
                "click_message_malformed",
                error=str(exc),
                partition=msg.partition(),
            )
            # Commit and skip so a poison message can't block the partition.
            self._consumer.commit(message=msg, asynchronous=False)
            return None

    def _update_lag_gauge(self) -> None:
        try:
            assignment = self._consumer.assignment()
            if not assignment:
                return
            positions = self._consumer.position(assignment)
            for tp in positions:
                _, high = self._consumer.get_watermark_offsets(tp, timeout=1.0)
                committed_or_position = tp.offset if tp.offset >= 0 else 0
                KAFKA_CONSUMER_LAG.labels(partition=str(tp.partition)).set(
                    max(high - committed_or_position, 0)
                )
        except Exception:
            # Lag metric is best-effort; never crash the loop.
            logger.debug("click_lag_metric_update_failed", exc_info=True)
