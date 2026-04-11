from typing import Annotated

from pydantic import Field

from src.config.base import BaseConfig


class RedisConfig(BaseConfig):
    REDIS_HOST: Annotated[str, Field(..., description="The Redis host")]
    REDIS_PORT: Annotated[int, Field(..., description="The Redis port")]

    REDIS_DB: Annotated[int, Field(..., description="The Redis database")]
    REDIS_PASSWORD: Annotated[str | None, Field(default=None, description="The Redis password")]

    APP_PREFIX: Annotated[str, Field(..., description="The Redis prefix")]
