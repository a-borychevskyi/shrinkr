from typing import Annotated

from pydantic import Field

from src.config.redis import RedisConfig


class RateLimiterConfig(RedisConfig):
    RATE_LIMIT_DEFAULT_TIMES: Annotated[
        int, Field(default=60, gt=0, description="Default max requests per window")
    ]
    RATE_LIMIT_DEFAULT_WINDOW: Annotated[
        int, Field(default=60, gt=0, description="Default window size in seconds")
    ]
    RATE_LIMIT_ENABLED: Annotated[
        bool, Field(default=True, description="Global kill switch for rate limiting")
    ]
    RATE_LIMIT_KEY_PREFIX: Annotated[
        str, Field(default="rl", description="Redis key namespace for rate limiting")
    ]
