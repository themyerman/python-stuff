"""Settings from env (ASCP_ prefix) and optional config file."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASCP_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    database_url: str = "sqlite:///ascp.db"
    artifact_root: str = "ascp_artifacts"
    log_level: str = "INFO"


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
