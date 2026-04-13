from typing import Annotated

from pydantic import Field

from src.config.base import BaseConfig


class KafkaConfig(BaseConfig):
    KAFKA_BOOTSTRAP_SERVERS: Annotated[
        str, Field(..., description="Comma-separated list of Kafka bootstrap servers")
    ]
    KAFKA_CLICKS_TOPIC: Annotated[
        str, Field(default="clicks", description="Topic for click events")
    ]
    KAFKA_CONSUMER_GROUP: Annotated[
        str,
        Field(
            default="click-ingester-group", description="Consumer group for the worker"
        ),
    ]
    KAFKA_PRODUCER_BUFFER_MAX_MESSAGES: Annotated[
        int,
        Field(
            default=100_000,
            description="Max messages buffered in librdkafka before produce() raises BufferError",
        ),
    ]
    KAFKA_PRODUCER_LINGER_MS: Annotated[
        int,
        Field(
            default=10, description="Producer linger.ms — batches messages client-side"
        ),
    ]
    KAFKA_CONSUMER_BATCH_SIZE: Annotated[
        int,
        Field(
            default=100, description="Worker batches this many messages before flushing"
        ),
    ]
    KAFKA_CONSUMER_FLUSH_INTERVAL_MS: Annotated[
        int,
        Field(
            default=100,
            description="Worker flushes after this long even if batch isn't full",
        ),
    ]
    KAFKA_CONSUMER_POLL_TIMEOUT_MS: Annotated[
        int,
        Field(default=500, description="consumer.poll() timeout in ms"),
    ]
    WORKER_HTTP_PORT: Annotated[
        int,
        Field(
            default=8001,
            description="Port the worker exposes /health, /ready, /metrics on",
        ),
    ]
