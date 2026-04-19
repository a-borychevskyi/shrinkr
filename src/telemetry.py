import os
import socket

import structlog
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
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

from src.config.app import AppConfig
from src.config.otel import OtelConfig
from src.config.profiling import ProfilingConfig

try:
    import pyroscope
except ImportError:  # pragma: no cover - win32 has no pyroscope-io wheels
    pyroscope = None  # type: ignore[assignment]

logger = structlog.get_logger(__name__)


def setup_telemetry() -> None:
    """Configure OpenTelemetry SDK with OTLP exporters for traces and metrics."""
    config = OtelConfig()

    if not config.OTEL_ENABLED:
        setup_profiling()
        return

    # Every gunicorn worker is a separate process with its own cumulative
    # counters. Without a distinct service.instance.id the collector
    # collapses them into one time series, which appears to reset each
    # time a different worker exports — making rate() useless. Hostname
    # + PID gives one series per worker that Prometheus can sum().
    resource = Resource.create(
        {
            "service.name": config.OTEL_SERVICE_NAME,
            "service.instance.id": f"{socket.gethostname()}:{os.getpid()}",
        }
    )

    # Traces — head-based sampling. ParentBased means once a trace is
    # sampled (or not) at the entry point, child spans inherit the
    # decision, so partial traces are never exported.
    sampler = ParentBased(root=TraceIdRatioBased(config.OTEL_TRACES_SAMPLER_RATIO))
    trace_provider = TracerProvider(resource=resource, sampler=sampler)
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

    setup_profiling()


def instrument_app(app):  # noqa: ANN001
    """Instrument a FastAPI app instance. Call after app creation."""
    config = OtelConfig()

    if not config.OTEL_ENABLED:
        return

    FastAPIInstrumentor.instrument_app(app)


def _detect_role(service_name: str) -> str:
    if service_name.endswith("-worker"):
        return "worker"
    if service_name:
        return "api"
    return "unknown"


def setup_profiling() -> None:
    """Start Pyroscope continuous profiling. No-op when disabled or unavailable."""
    profiling_config = ProfilingConfig()
    if not profiling_config.PYROSCOPE_ENABLED:
        return
    if pyroscope is None:
        logger.warning("pyroscope_module_unavailable")
        return

    otel_config = OtelConfig()
    app_config = AppConfig()
    tags = {
        "env": app_config.APP_ENVIRONMENT,
        "instance": socket.gethostname(),
        "role": _detect_role(otel_config.OTEL_SERVICE_NAME),
    }

    try:
        pyroscope.configure(
            application_name=otel_config.OTEL_SERVICE_NAME,
            server_address=profiling_config.PYROSCOPE_SERVER_ADDRESS,
            sample_rate=profiling_config.PYROSCOPE_SAMPLE_RATE,
            tags=tags,
        )
        logger.info(
            "pyroscope_configured",
            application=otel_config.OTEL_SERVICE_NAME,
            server=profiling_config.PYROSCOPE_SERVER_ADDRESS,
        )
    except Exception:
        logger.warning("pyroscope_setup_failed", exc_info=True)
