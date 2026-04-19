from typing import Annotated

from pydantic import Field

from src.config.base import BaseConfig


class ProfilingConfig(BaseConfig):
    PYROSCOPE_ENABLED: Annotated[
        bool,
        Field(default=False, description="Enable Pyroscope continuous profiling"),
    ]
    PYROSCOPE_SERVER_ADDRESS: Annotated[
        str,
        Field(
            default="http://pyroscope:4040",
            description="Pyroscope ingestion endpoint",
        ),
    ]
    PYROSCOPE_SAMPLE_RATE: Annotated[
        int,
        Field(
            default=100,
            gt=0,
            description="Profile samples per second (Hz)",
        ),
    ]
