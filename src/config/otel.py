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
