from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.config.otel import OtelConfig


def setup_telemetry() -> None:
    """Configure OpenTelemetry SDK with OTLP exporter and auto-instrumentation."""
    config = OtelConfig()

    if not config.OTEL_ENABLED:
        return

    resource = Resource.create({"service.name": config.OTEL_SERVICE_NAME})

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=config.OTEL_EXPORTER_OTLP_ENDPOINT)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    RedisInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()


def instrument_app(app):  # noqa: ANN001
    """Instrument a FastAPI app instance. Call after app creation."""
    config = OtelConfig()

    if not config.OTEL_ENABLED:
        return

    FastAPIInstrumentor.instrument_app(app)
