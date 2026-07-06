from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_VERSION_FILE = Path(__file__).parent / "VERSION"


def _read_release_version() -> str:
    return _VERSION_FILE.read_text().strip()


class Settings(BaseSettings):
    service_name: str = "catalog"
    release_version: str = Field(default_factory=_read_release_version)
    app_port: int = 8001
    otlp_endpoint: str = "http://localhost:4317"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
