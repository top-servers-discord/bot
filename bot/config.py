from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    discord_token: str = Field(default="")
    shard_count: int | None = None
    shard_ids: list[int] | None = None

    clickhouse_url: str = Field(default="http://localhost:8123")
    valkey_url: str = Field(default="redis://localhost:6379/0")

    backend_url: str = Field(default="http://localhost:8000")
    backend_hmac_secret: str = Field(default="change-me")

    environment: str = Field(default="dev")


@lru_cache
def get_settings() -> BotSettings:
    return BotSettings()
