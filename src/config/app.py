from pydantic import Field

from src.config.base import BaseConfig


class AppConfig(BaseConfig):
    APP_HOST: str = Field(
        default="0.0.0.0", description="The host to bind the server to"
    )
    APP_PORT: int = Field(default=8000, description="The port to bind the server to")

    APP_LOG_LEVEL: str = Field(default="info", description="The log level to use")
    APP_ENVIRONMENT: str = Field(
        default="development", description="The environment to run the server in"
    )
    APP_WORKERS: int = Field(
        default=1, description="The number of workers to run the server with"
    )
