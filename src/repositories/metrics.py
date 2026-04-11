from opentelemetry import metrics

meter = metrics.get_meter(__name__)

cache_operations_total = meter.create_counter(
    name="cache.operations",
    description="Total number of cache operations",
)

cache_operation_duration_seconds = meter.create_histogram(
    name="cache.operation.duration",
    description="Time spent on cache operations",
    unit="s",
)
