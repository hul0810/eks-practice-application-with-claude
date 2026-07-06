from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_VERSION_FILE = Path(__file__).parent / "VERSION"


def _read_release_version() -> str:
    return _VERSION_FILE.read_text().strip()


class Settings(BaseSettings):
    service_name: str = "order"
    release_version: str = Field(default_factory=_read_release_version)
    app_port: int = 8002
    otlp_endpoint: str = "http://localhost:4317"
    catalog_url: str = "http://localhost:8001"
    aws_region: str = "ap-northeast-2"
    sqs_queue_url: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
