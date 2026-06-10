from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "catalog"
    app_version: str = "v1"
    app_port: int = 8001
    otlp_endpoint: str = "http://localhost:4317"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
