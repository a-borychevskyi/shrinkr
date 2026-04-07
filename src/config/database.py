from pydantic import Field, SecretStr

from src.config.base import BaseConfig


class DatabaseConfig(BaseConfig):
    DB_HOST: str = Field(..., description="The database host")
    DB_PORT: int = Field(..., description="The database port")
    DB_NAME: str = Field(..., description="The database name")
    DB_USER: str = Field(..., description="The database user")
    DB_PASSWORD: SecretStr = Field(..., description="The database password")

    @property
    def DB_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD.get_secret_value()}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
