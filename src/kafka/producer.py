"""Async-friendly wrapper around confluent_kafka.Producer.

`Producer.produce()` is non-blocking — it enqueues into librdkafka's
C-side queue and returns immediately. Delivery happens in librdkafka's
background thread. We must call `producer.poll(0)` periodically to
drain the delivery report queue (otherwise it grows without bound);
that's wired up by the API's lifespan task.
"""

from __future__ import annotations

from typing import Protocol

import structlog
from confluent_kafka import KafkaError, Message

from src.kafka.metrics import (
    CLICKS_DROPPED_TOTAL,
    CLICKS_PRODUCED_TOTAL,
)
from src.kafka.schema import ClickEvent, encode_click_event

logger = structlog.get_logger(__name__)


class KafkaProducerProtocol(Protocol):
    def produce(self, topic, key=None, value=None, on_delivery=None) -> None: ...
    def poll(self, timeout: float) -> int: ...
    def flush(self, timeout: float) -> int: ...


# Pre-bind the "delivery_failed" counter — it's only referenced from the
# static on_delivery callback so we bind it once at module load.
_DROPPED_DELIVERY_FAILED = CLICKS_DROPPED_TOTAL.labels(reason="delivery_failed")


class ClickProducer:
    """Sends ClickEvent payloads to a Kafka topic, keyed by url_id."""

    def __init__(self, producer: KafkaProducerProtocol, topic: str) -> None:
        self._producer = producer
        self._topic = topic
        # Bind labeled counters once — .labels() does dict lookup + tuple
        # hashing per call, which showed up at ~7% CPU on the worker
        # profile and is wasted work on the API's send path too.
        self._produced_counter = CLICKS_PRODUCED_TOTAL.labels(topic=topic)
        self._dropped_buffer_full_counter = CLICKS_DROPPED_TOTAL.labels(
            reason="buffer_full"
        )

    def send(self, event: ClickEvent) -> None:
        """Fire-and-forget produce. Drops + logs if librdkafka buffer is full."""
        try:
            self._producer.produce(
                topic=self._topic,
                key=str(event.url_id).encode("ascii"),
                value=encode_click_event(event),
                on_delivery=self._on_delivery,
            )
            self._produced_counter.inc()
        except BufferError:
            self._dropped_buffer_full_counter.inc()
            logger.warning("click_produce_buffer_full", url_id=event.url_id)

    def poll(self) -> None:
        """Non-blocking drain of librdkafka's delivery report queue."""
        self._producer.poll(0)

    def flush(self, timeout: float = 5.0) -> None:
        """Block up to `timeout` seconds for in-flight messages to be delivered."""
        self._producer.flush(timeout)

    @staticmethod
    def _on_delivery(err: KafkaError | None, _msg: Message) -> None:
        if err is not None:
            _DROPPED_DELIVERY_FAILED.inc()
            logger.warning("click_delivery_failed", error=str(err))
