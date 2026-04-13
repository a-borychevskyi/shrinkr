"""Worker process entrypoint.

Boots:
- Database (shared with the API)
- Confluent Kafka consumer subscribed to the clicks topic
- ClickConsumer with bulk-insert repository
- Starlette HTTP server for /health /ready /metrics on WORKER_HTTP_PORT
- Poll loop in a dedicated thread

Shutdown is triggered by SIGTERM / SIGINT: stop the poll thread,
flush any pending batch, commit, close consumer, dispose engine.
"""

from __future__ import annotations

import asyncio
import signal
import threading
from typing import cast

import structlog
import uvicorn
from confluent_kafka import Consumer

from src.config.kafka import KafkaConfig
from src.di.orm.database import get_db
from src.kafka.topics import CLICKS_TOPIC
from src.logging import setup_logging
from src.telemetry import setup_telemetry
from src.worker.consumer import ClickConsumer, KafkaConsumerProtocol
from src.worker.http import build_app, is_thread_alive
from src.worker.repository import UrlStatsBulkRepository

logger = structlog.get_logger(__name__)


async def _async_main() -> None:
    config = KafkaConfig()
    db = get_db()
    repository = UrlStatsBulkRepository(engine=db.async_engine)

    raw_consumer = Consumer(
        {
            "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
            "group.id": config.KAFKA_CONSUMER_GROUP,
            "enable.auto.commit": False,
            "auto.offset.reset": "earliest",
            "client.id": "shrinkr-worker",
        }
    )
    raw_consumer.subscribe([CLICKS_TOPIC])

    logger.info(
        "worker_starting",
        topic=CLICKS_TOPIC,
        group=config.KAFKA_CONSUMER_GROUP,
        bootstrap_servers=config.KAFKA_BOOTSTRAP_SERVERS,
        batch_size=config.KAFKA_CONSUMER_BATCH_SIZE,
        flush_interval_ms=config.KAFKA_CONSUMER_FLUSH_INTERVAL_MS,
        http_port=config.WORKER_HTTP_PORT,
    )

    click_consumer = ClickConsumer(
        consumer=cast(KafkaConsumerProtocol, raw_consumer),
        repository=repository,
        batch_size=config.KAFKA_CONSUMER_BATCH_SIZE,
        flush_interval_seconds=config.KAFKA_CONSUMER_FLUSH_INTERVAL_MS / 1000,
        poll_timeout_seconds=config.KAFKA_CONSUMER_POLL_TIMEOUT_MS / 1000,
    )

    loop = asyncio.get_running_loop()
    poll_thread = threading.Thread(
        target=click_consumer.run_poll_loop,
        args=(loop,),
        name="click-poll-loop",
        daemon=True,
    )

    ready_flag = threading.Event()

    def _is_ready() -> bool:
        return ready_flag.is_set() and poll_thread.is_alive()

    app = build_app(
        is_poll_thread_alive=is_thread_alive(poll_thread),
        is_ready=_is_ready,
    )

    uvicorn_config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=config.WORKER_HTTP_PORT,
        log_level="info",
        lifespan="off",
    )
    server = uvicorn.Server(uvicorn_config)

    poll_thread.start()
    # Mark ready as soon as the poll thread is up. (For a stricter check
    # we'd wait for partition assignment via on_assign callback — left as
    # a future improvement; documented in the design spec.)
    ready_flag.set()
    logger.info("worker_ready", http_port=config.WORKER_HTTP_PORT)

    stop_event = asyncio.Event()

    def _request_stop() -> None:
        logger.info("worker_shutdown_signal_received")
        stop_event.set()

    loop.add_signal_handler(signal.SIGTERM, _request_stop)
    loop.add_signal_handler(signal.SIGINT, _request_stop)

    server_task = asyncio.create_task(server.serve(), name="worker-http-server")

    await stop_event.wait()

    logger.info("worker_shutting_down")
    click_consumer.stop()
    poll_thread.join(timeout=15.0)
    server.should_exit = True
    await server_task
    await db.stop()


def run() -> None:
    """Console-script entrypoint.

    Invoked as `python -m src.worker.main`.
    """
    setup_logging()
    setup_telemetry()
    asyncio.run(_async_main())


if __name__ == "__main__":
    run()
