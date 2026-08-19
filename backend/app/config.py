"""Application configuration loaded from environment."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg2://scoop:scoop@db:5432/scoop",
        alias="DATABASE_URL",
    )
    default_postcode: str = Field(default="4000", alias="DEFAULT_POSTCODE")
    scrape_cache_ttl_seconds: int = Field(default=1800, alias="SCRAPE_CACHE_TTL_SECONDS")
    scrape_timeout_seconds: float = Field(default=15.0, alias="SCRAPE_TIMEOUT_SECONDS")

    enable_danmurphys: bool = Field(default=True, alias="ENABLE_DANMURPHYS")
    enable_bws: bool = Field(default=True, alias="ENABLE_BWS")
    enable_liquorland: bool = Field(default=True, alias="ENABLE_LIQUORLAND")

    cors_origins: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        alias="CORS_ORIGINS",
    )
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()