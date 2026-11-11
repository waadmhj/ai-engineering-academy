"""Application settings, read from environment variables (and an optional .env file)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = f"sqlite:///{(REPO_ROOT / 'api' / 'academy.db').as_posix()}"
    content_dir: Path = REPO_ROOT / "content"
    roadmap_file: Path = REPO_ROOT / "content.md"
    forge_dir: Path = REPO_ROOT / "forge"

    auth_mode: Literal["local", "jwt"] = "local"
    jwt_secret: str = "dev-only-insecure-secret-change-me"
    jwt_ttl_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000"

    forge_timeout_seconds: int = 60

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
