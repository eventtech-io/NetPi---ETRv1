"""Centralized configuration management."""
import os
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Settings(BaseModel):
    """NetPi application settings.

    Values are read from environment variables. For local development,
    create a .env file or export variables before starting the server.
    """

    api_key: str | None = Field(default=None, alias="NETPI_API_KEY")
    cors_origins: list[str] = Field(default_factory=lambda: ["*"], alias="NETPI_CORS_ORIGINS")
    data_dir: str = Field(default="/var/lib/netpi", alias="NETPI_DATA_DIR")
    log_level: str = Field(default="INFO", alias="NETPI_LOG_LEVEL")
    capture_dir: str = Field(default="/var/lib/netpi/captures", alias="NETPI_CAPTURE_DIR")
    max_capture_size_mb: int = Field(default=1024, alias="NETPI_MAX_CAPTURE_SIZE_MB")
    bpf_allowed_chars: str = (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "0123456789.: /\\-()=><!&|_"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()] or ["*"]
        return v

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, v: str) -> str:
        return v.upper()

    model_config = ConfigDict(populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    env_values = {
        field.alias: os.environ[field.alias]
        for field in Settings.model_fields.values()
        if field.alias and field.alias in os.environ
    }
    return Settings(**env_values)



