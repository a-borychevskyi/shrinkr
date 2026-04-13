"""Verify a malformed message doesn't block the partition: it's
logged, committed, and skipped; subsequent valid messages still
flow through to Postgres.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone

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
def poison_kafka_container():
    with KafkaContainer() as kafka:
        yield kafka


@pytest.fixture(scope="module")
def poison_postgres_container():
    with PostgresContainer("postgres:18.0-alpine") as pg:
        yield pg


@pytest.mark.asyncio
async def test_poison_message_is_skipped(
    poison_kafka_container, poison_postgres_container
):
    bootstrap = poison_kafka_container.get_bootstrap_server()
    pg_url = poison_postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )

    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            sa_insert(Url).values(id=1, short_code="abc", target_url="https://x")
        )

    raw_producer = Producer({"bootstrap.servers": bootstrap, "linger.ms": 5})

    # Produce: poison first, then 2 valid events.
    raw_producer.produce(topic=CLICKS_TOPIC, key=b"1", value=b"not json at all")

    click_producer = ClickProducer(producer=raw_producer, topic=CLICKS_TOPIC)
    ts = datetime.now(timezone.utc)
    click_producer.send(
        ClickEvent(url_id=1, user_agent="ua-1", ip_address="ip", occurred_at=ts)
    )
    click_producer.send(
        ClickEvent(url_id=1, user_agent="ua-2", ip_address="ip", occurred_at=ts)
    )
    raw_producer.flush(timeout=10)

    consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": "poison-group",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    consumer.subscribe([CLICKS_TOPIC])

    repo = UrlStatsBulkRepository(engine=engine)
    click_consumer = ClickConsumer(
        consumer=consumer,
        repository=repo,
        batch_size=2,
        flush_interval_seconds=0.5,
        poll_timeout_seconds=0.2,
    )

    loop = asyncio.get_running_loop()
    thread = threading.Thread(
        target=click_consumer.run_poll_loop, args=(loop,), daemon=True
    )
    thread.start()
    try:
        deadline = loop.time() + 10
        count = 0
        while loop.time() < deadline:
            async with engine.connect() as conn:
                count = (
                    await conn.execute(select(func.count()).select_from(UrlStats))
                ).scalar_one()
            if count >= 2:
                break
            await asyncio.sleep(0.2)
        assert count == 2, (
            f"expected 2 rows (poison skipped, 2 valid inserted), got {count}"
        )
    finally:
        click_consumer.stop()
        thread.join(timeout=5)
        await engine.dispose()
