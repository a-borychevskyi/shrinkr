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
from concurrent.futures import TimeoutError as FuturesTimeoutError
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


class KafkaConsumerProtocol(Protocol):
    def poll(self, timeout: float) -> Any: ...
    def commit(self, message: Any = None, asynchronous: bool = True) -> Any: ...
    def close(self) -> None: ...
    def assignment(self) -> list[Any]: ...
    def get_watermark_offsets(
        self, partition: Any, timeout: float = 5.0
    ) -> tuple[int, int]: ...
    def position(self, partitions: list[Any]) -> list[Any]: ...
    def committed(self, partitions: list[Any], timeout: float = 5.0) -> list[Any]: ...


class ClickConsumer:
    def __init__(
        self,
        consumer: KafkaConsumerProtocol,
        repository: UrlStatsBulkRepository,
        batch_size: int,
        flush_interval_seconds: float,
        poll_timeout_seconds: float = 0.5,
        flush_timeout_seconds: float = 30.0,
    ) -> None:
        self._consumer = consumer
        self._repository = repository
        self._batcher: Batcher[ClickEvent] = Batcher(
            max_size=batch_size, max_linger_seconds=flush_interval_seconds
        )
        self._poll_timeout = poll_timeout_seconds
        self._flush_timeout = flush_timeout_seconds
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
        """Bridge a batch from the poll thread to the asyncio loop, blocking on completion.

        All confluent_kafka.Consumer calls (poll, commit, close, etc.) MUST happen
        on this poll thread — librdkafka is not documented to be thread-safe for
        cross-thread Consumer calls. We bridge the async insert to the asyncio
        loop, but the post-insert commit happens here, on the poll thread.
        """
        future = asyncio.run_coroutine_threadsafe(self._flush_batch(batch), loop)
        try:
            future.result(timeout=self._flush_timeout)
        except FuturesTimeoutError:
            logger.warning(
                "click_flush_timed_out",
                batch_size=len(batch),
                timeout_seconds=self._flush_timeout,
            )
            # Do not commit; offsets re-read on next poll.
            return
        except Exception:
            logger.exception("click_flush_failed", batch_size=len(batch))
            # Do not commit; offsets re-read on next poll.
            return
        else:
            # Insert succeeded; commit on this (poll) thread.
            self._consumer.commit(asynchronous=False)
        finally:
            self._update_lag_gauge()

    async def _flush_batch(self, batch: list[ClickEvent]) -> None:
        """Insert a batch via the async repository.

        Does NOT commit — that's done by _submit_flush on the poll thread
        after this coroutine completes successfully.
        """
        if not batch:
            return
        CLICKS_BATCH_SIZE.observe(len(batch))
        start = perf_counter()
        await self._repository.insert_many(batch)
        CLICKS_FLUSH_DURATION_SECONDS.observe(perf_counter() - start)
        CLICKS_INSERTED_TOTAL.inc(len(batch))

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
            committed = self._consumer.committed(assignment, timeout=1.0)
            for tp in committed:
                _, high = self._consumer.get_watermark_offsets(tp, timeout=1.0)
                # tp.offset == -1001 means no committed offset yet for this partition.
                committed_offset = tp.offset if tp.offset >= 0 else 0
                KAFKA_CONSUMER_LAG.labels(partition=str(tp.partition)).set(
                    max(high - committed_offset, 0)
                )
        except Exception:
            # Lag metric is best-effort; never crash the loop.
            logger.warning("click_lag_metric_update_failed", exc_info=True)
