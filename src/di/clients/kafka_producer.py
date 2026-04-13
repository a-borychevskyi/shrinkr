"""DI factory for the singleton ClickProducer.

Mirrors the Redis client pattern in src/di/clients/redis.py — one
producer per worker process, shared across all requests, lifespan-
managed in src/api/app.py.
"""

from functools import lru_cache

from confluent_kafka import Producer

from src.config.kafka import KafkaConfig
from src.kafka.producer import ClickProducer


@lru_cache(maxsize=1)
def get_click_producer() -> ClickProducer:
    config = KafkaConfig()
    raw_producer = Producer(
        {
            "bootstrap.servers": config.KAFKA_BOOTSTRAP_SERVERS,
            "linger.ms": config.KAFKA_PRODUCER_LINGER_MS,
            "queue.buffering.max.messages": config.KAFKA_PRODUCER_BUFFER_MAX_MESSAGES,
            # Acks=1 — leader-ack only, balances durability vs. latency.
            # Click stats are best-effort; full ISR ack isn't worth the cost.
            "acks": "1",
            "enable.idempotence": False,
            "client.id": "shrinkr-api",
        }
    )
    return ClickProducer(producer=raw_producer, topic=config.KAFKA_CLICKS_TOPIC)
