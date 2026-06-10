from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "order"
    app_version: str = "v1"
    app_port: int = 8002
    otlp_endpoint: str = "http://localhost:4317"
    catalog_url: str = "http://localhost:8001"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
