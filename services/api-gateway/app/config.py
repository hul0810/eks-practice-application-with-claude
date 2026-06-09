from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "api-gateway"
    app_version: str = "v1"
    app_port: int = 8000
    otlp_endpoint: str = "http://localhost:4317"
    product_service_url: str = "http://localhost:8001"
    order_service_url: str = "http://localhost:8002"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)


settings = Settings()
