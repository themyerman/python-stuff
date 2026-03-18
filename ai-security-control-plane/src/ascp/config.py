"""Application settings (ASCP_* env vars)."""

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./ascp.db"
    artifact_root: str = "./ascp_artifacts"
    log_level: str = "INFO"
    # If set, all routes except /health require Authorization: Bearer <key> or X-ASCP-API-Key
    api_key: Optional[str] = None
