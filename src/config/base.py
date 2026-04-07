from dotenv import find_dotenv

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=find_dotenv(),
        case_sensitive=True,
        env_ignore_empty=False,
        env_file_encoding="utf-8",
        extra="ignore",
    )
