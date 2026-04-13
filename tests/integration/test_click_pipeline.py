"""End-to-end pipeline test: produce N events through ClickProducer,
run ClickConsumer briefly, assert N rows appear in url_stats.

Uses testcontainers to spin up real Kafka (KRaft mode) and Postgres
in Docker. Skipped automatically if Docker is unavailable.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timezone

import pytest
from confluent_kafka import Consumer, Producer
from sqlalchemy import insert as sa_insert
from sqlalchemy import select
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


@pytest.fixture(scope="module")
def pipeline_kafka_container():
    with KafkaContainer() as kafka:
        yield kafka


@pytest.fixture(scope="module")
def pipeline_postgres_container():
    with PostgresContainer("postgres:18.0-alpine") as pg:
        yield pg


@pytest.mark.asyncio
async def test_end_to_end_click_pipeline(
    pipeline_kafka_container, pipeline_postgres_container
):
    bootstrap = pipeline_kafka_container.get_bootstrap_server()
    pg_url = pipeline_postgres_container.get_connection_url().replace(
        "postgresql+psycopg2", "postgresql+asyncpg"
    )

    engine = create_async_engine(pg_url)
    async with engine.begin() as conn:
        # Create just the schema for the test.
        await conn.run_sync(Base.metadata.create_all)
        # Seed a row in `urls` so the FK on url_stats.url_id is satisfied.
        await conn.execute(
            sa_insert(Url).values(id=1, short_code="abc", target_url="https://x")
        )

    # Producer
    raw_producer = Producer({"bootstrap.servers": bootstrap, "linger.ms": 5})
    click_producer = ClickProducer(producer=raw_producer, topic=CLICKS_TOPIC)

    # Consumer
    raw_consumer = Consumer(
        {
            "bootstrap.servers": bootstrap,
            "group.id": "test-pipeline-group",
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
        }
    )
    raw_consumer.subscribe([CLICKS_TOPIC])

    repo = UrlStatsBulkRepository(engine=engine)
    click_consumer = ClickConsumer(
        consumer=raw_consumer,
        repository=repo,
        batch_size=10,
        flush_interval_seconds=0.5,
        poll_timeout_seconds=0.2,
    )

    # Produce 25 events.
    ts = datetime.now(timezone.utc)
    for i in range(25):
        click_producer.send(
            ClickEvent(
                url_id=1,
                user_agent=f"ua-{i}",
                ip_address="1.2.3.4",
                occurred_at=ts,
            )
        )
    raw_producer.flush(timeout=10)

    # Run the consumer in its own thread for up to 10 seconds, polling
    # for row count every 200ms.
    loop = asyncio.get_running_loop()
    thread = threading.Thread(
        target=click_consumer.run_poll_loop, args=(loop,), daemon=True
    )
    thread.start()
    try:

        async def _row_count() -> int:
            async with engine.connect() as conn:
                result = await conn.execute(select(UrlStats))
                return len(result.all())

        deadline = loop.time() + 10
        count = 0
        while loop.time() < deadline:
            count = await _row_count()
            if count >= 25:
                break
            await asyncio.sleep(0.2)
        assert count == 25, f"expected 25 rows, found {count}"
    finally:
        click_consumer.stop()
        thread.join(timeout=5)
        await engine.dispose()
