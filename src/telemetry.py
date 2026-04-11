from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.config.otel import OtelConfig


def setup_telemetry() -> None:
    """Configure OpenTelemetry SDK with OTLP exporters for traces and metrics."""
    config = OtelConfig()

    if not config.OTEL_ENABLED:
        return

    resource = Resource.create({"service.name": config.OTEL_SERVICE_NAME})

    # Traces
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT)
        )
    )
    trace.set_tracer_provider(trace_provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT),
        export_interval_millis=5000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()


def instrument_app(app):  # noqa: ANN001
    """Instrument a FastAPI app instance. Call after app creation."""
    config = OtelConfig()

    if not config.OTEL_ENABLED:
        return

    FastAPIInstrumentor.instrument_app(app)
