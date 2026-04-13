"""Verify at-least-once delivery: simulate a worker crash after the
Postgres insert but before the Kafka commit. Restart the consumer
and assert the same offsets are re-read (duplicate inserts appear).
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone
from typing import Any

import pytest
from confluent_kafka import Consumer, Producer
from sqlalchemy import func, select
from sqlalchemy import insert as sa_insert
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.kafka import KafkaContainer
from testcontainers.postgres import PostgresContainer

from src.kafka.producer import ClickProducer
from src.kafka.schema import ClickEvent
from src.kafka.topics import CLICKS_TOPIC
from src.orm.models import UrlStats
from src.orm.models.base import Base
from src.orm.models.url import Url
from src.worker.consumer import ClickConsumer
from src.worker.repository import UrlStatsBulkRepository


# Module-scoped fixtures, renamed to avoid collision with session-scoped
# fixtures in tests/integration/conftest.py.
@pytest.fixture(scope="module")
def at_least_once_kafka_container():
    with KafkaContainer() as kafka:
        yield kafka


@pytest.fixture(scope="module")
def at_least_once_postgres_container():
    with PostgresContainer("postgres:18.0-alpine") as pg:
        yield pg


class _FailingCommitConsumer:
    """Thin Python wrapper around a real confluent_kafka.Consumer that
    raises RuntimeError on every commit() call.

    confluent_kafka.Consumer is a C-extension type (cimpl.Consumer) whose
    methods are read-only slots, so patch.object cannot replace them.
    Wrapping in a pure-Python class lets us intercept commit() while
    delegating all other calls to the real consumer.
    """

    def __init__(self, real: Consumer) -> None:
        self._real = real

    def poll(self, timeout: float) -> Any:
        return self._real.poll(timeout)

    def commit(self, message: Any = None, asynchronous: bool = True) -> Any:
        raise RuntimeError("simulated crash before commit")

    def close(self) -> None:
        self._real.close()

    def assignment(self) -> list[Any]:
        return self._real.assignment()

    def get_watermark_offsets(
        self, partition: Any, timeout: float = 5.0
    ) -> tuple[int, int]:
        return self._real.get_watermark_offsets(partition, timeout)

    def position(self, partitions: list[Any]) -> list[Any]:
        return self._real.position(partitions)

    def committed(self, partitions: list[Any], timeout: float = 5.0) -> list[Any]:
        return self._real.committed(partitions, timeout)


def _build_consumer(bootstrap: str) -> Consumer:
    c = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": "at-least-once-group",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    c.subscribe([CLICKS_TOPIC])
    return c


@pytest.mark.asyncio
async def test_at_least_once_delivery(
    at_least_once_kafka_container, at_least_once_postgres_container
):
    bootstrap = at_least_once_kafka_container.get_bootstrap_server()
    pg_url = at_least_once_postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )

    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            sa_insert(Url).values(id=1, short_code="abc", target_url="https://x")
        )

    repo = UrlStatsBulkRepository(engine=engine)

    # Produce 5 events.
    raw_producer = Producer({"bootstrap.servers": bootstrap, "linger.ms": 5})
    producer = ClickProducer(producer=raw_producer, topic=CLICKS_TOPIC)
    ts = datetime.now(timezone.utc)
    for i in range(5):
        producer.send(
            ClickEvent(
                url_id=1,
                user_agent=f"ua-{i}",
                ip_address="ip",
                occurred_at=ts,
            )
        )
    raw_producer.flush(timeout=10)

    # First consumer run: use a wrapper that raises on commit(), simulating
    # a worker crash in the brief window after Postgres insert succeeded but
    # before the offset commit lands.  confluent_kafka.Consumer is a C
    # extension type with read-only method slots, so patch.object cannot
    # replace commit() — we delegate through _FailingCommitConsumer instead.
    # The poll thread catches the exception in _submit_flush and continues
    # without committing, so on restart the next consumer re-reads the same
    # offsets and re-inserts.
    raw_consumer_a = _build_consumer(bootstrap)
    failing_consumer_a = _FailingCommitConsumer(raw_consumer_a)
    click_consumer_a = ClickConsumer(
        consumer=failing_consumer_a,  # type: ignore[arg-type]
        repository=repo,
        batch_size=5,
        flush_interval_seconds=0.5,
        poll_timeout_seconds=0.2,
    )

    loop = asyncio.get_running_loop()
    thread_a = threading.Thread(
        target=click_consumer_a.run_poll_loop, args=(loop,), daemon=True
    )
    thread_a.start()
    # Let the consumer process the batch and try (and fail) to commit
    # multiple times — Postgres still gets the inserts because commit
    # is the LAST step in _submit_flush after future.result() succeeds.
    await asyncio.sleep(3)
    click_consumer_a.stop()
    thread_a.join(timeout=5)

    # At this point rows have been inserted but the commit failed, so
    # offsets aren't advanced. Counts should be >= 5.
    async with engine.connect() as conn:
        first_count = (
            await conn.execute(select(func.count()).select_from(UrlStats))
        ).scalar_one()
    assert first_count >= 5, (
        f"expected at least 5 rows after first run, got {first_count}"
    )

    # Second consumer run: no commit interception, same group id → re-reads
    # from un-committed offsets and re-inserts.
    consumer_b = _build_consumer(bootstrap)
    click_consumer_b = ClickConsumer(
        consumer=consumer_b,
        repository=repo,
        batch_size=5,
        flush_interval_seconds=0.5,
        poll_timeout_seconds=0.2,
    )
    thread_b = threading.Thread(
        target=click_consumer_b.run_poll_loop, args=(loop,), daemon=True
    )
    thread_b.start()
    await asyncio.sleep(3)
    click_consumer_b.stop()
    thread_b.join(timeout=5)

    async with engine.connect() as conn:
        final_count = (
            await conn.execute(select(func.count()).select_from(UrlStats))
        ).scalar_one()

    # At-least-once: final >= first + 5 (re-reads of un-committed batch
    # produce duplicates, which is the whole point).
    assert final_count >= first_count + 5, (
        f"expected duplicates from re-read; first={first_count} final={final_count}"
    )

    await engine.dispose()
