"""Configuration for API Extractor HTTP server."""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Server configuration settings."""

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    log_level: str = "info"

    # API settings
    api_title: str = "API Extractor"
    api_version: str = "0.1.0"
    api_description: str = "Extract REST API definitions from source code"

    # Security settings
    max_path_depth: int = 10
    allowed_path_prefixes: List[str] = []
    enable_s3: bool = True

    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 10

    model_config = SettingsConfigDict(
        env_prefix="API_EXTRACTOR_",
        env_file=".env",
        env_file_encoding="utf-8",
    )


def get_settings() -> Settings:
    """Get application settings."""
    return Settings()
