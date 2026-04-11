from prometheus_client import Counter, Histogram

cache_operations_total = Counter(
    "cache_operations_total",
    "Total number of cache operations",
    labelnames=["operation", "result"],
)

cache_operation_duration_seconds = Histogram(
    "cache_operation_duration_seconds",
    "Time spent on cache operations",
    labelnames=["operation"],
    buckets=(0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
)
