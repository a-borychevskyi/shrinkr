"""Prometheus metrics for the Kafka click pipeline.

Defined once and imported by both the API (producer side) and the
worker (consumer side). Keeping label cardinality low is intentional
— `partition` is 0..N where N is small (3), and `reason` is a fixed
enum of two values.
"""

from prometheus_client import Counter, Gauge, Histogram  # type: ignore

CLICKS_PRODUCED_TOTAL = Counter(
    "clicks_produced_total",
    "Number of click events successfully enqueued into the Kafka producer buffer",
    labelnames=["topic"],
)

CLICKS_DROPPED_TOTAL = Counter(
    "clicks_dropped_total",
    "Number of click events dropped before reaching Kafka",
    labelnames=["reason"],  # buffer_full | delivery_failed
)

CLICKS_CONSUMED_TOTAL = Counter(
    "clicks_consumed_total",
    "Number of click events polled from Kafka by the worker",
    labelnames=["partition"],
)

CLICKS_INSERTED_TOTAL = Counter(
    "clicks_inserted_total",
    "Number of click rows successfully inserted into url_stats by the worker",
)

CLICKS_MALFORMED_TOTAL = Counter(
    "clicks_malformed_total",
    "Number of malformed click events skipped by the worker (subset of clicks_consumed_total — every poll is counted, decoded or not)",
)

CLICKS_BATCH_SIZE = Histogram(
    "clicks_batch_size",
    "Size of each batch flushed by the worker",
    buckets=(1, 5, 10, 25, 50, 100, 250, 500, 1000),
)

CLICKS_FLUSH_DURATION_SECONDS = Histogram(
    "clicks_flush_duration_seconds",
    "Wall-clock duration of each Postgres bulk insert performed by the worker",
)

KAFKA_CONSUMER_LAG = Gauge(
    "kafka_consumer_lag",
    "Difference between high-water mark and committed offset per partition",
    labelnames=["partition"],
)
