from opentelemetry import metrics  # type: ignore[attr-defined]

meter = metrics.get_meter(__name__)

cache_operations_total = meter.create_counter(
    name="cache.operations",
    description="Total number of cache operations",
)

# Buckets target sub-millisecond to ~quarter-second — Redis GET/SET on a
# local pool is typically 0.3–2 ms, so the default OTel SDK boundaries
# (which jump 0 → 5s) collapse every sample into one bucket and make
# histogram_quantile useless.
_CACHE_OP_BUCKETS_SECONDS = (
    0.0005,
    0.001,
    0.002,
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
)

cache_operation_duration_seconds = meter.create_histogram(
    name="cache.operation.duration",
    description="Time spent on cache operations",
    unit="s",
    explicit_bucket_boundaries_advisory=_CACHE_OP_BUCKETS_SECONDS,
)
