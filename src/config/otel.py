from typing import Annotated

from pydantic import Field

from src.config.base import BaseConfig


class OtelConfig(BaseConfig):
    OTEL_ENABLED: Annotated[
        bool, Field(default=False, description="Enable OpenTelemetry tracing")
    ]
    OTEL_SERVICE_NAME: Annotated[
        str, Field(default="shrinkr", description="OTel service name")
    ]
    OTEL_EXPORTER_OTLP_ENDPOINT: Annotated[
        str,
        Field(
            default="http://localhost:4317",
            description="OTel collector OTLP gRPC endpoint",
        ),
    ]
    OTEL_TRACES_SAMPLER_RATIO: Annotated[
        float,
        Field(
            default=0.05,
            ge=0.0,
            le=1.0,
            description=(
                "Probability that a trace is sampled. Span encoding/export "
                "is the dominant CPU cost under load, so default to 5% "
                "head-based sampling. Set to 1.0 for dev/debug, 0.0 to "
                "disable (spans still created, just never exported)."
            ),
        ),
    ]
