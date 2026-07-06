# dev CI 워크플로우 테스트용 재빌드 마커 (2026-07-07)
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from .config import settings
from .telemetry import init_telemetry
from .logging_config import configure_logging
from .middleware import CorrelationIdMiddleware, AccessLogMiddleware
from .routes import health, products

configure_logging(settings.service_name, settings.release_version)

app = FastAPI(
    title=settings.service_name,
    version=settings.release_version,
    docs_url="/docs",
)

init_telemetry(app, settings.service_name, settings.release_version, settings.otlp_endpoint)

# 등록 순서: 나중에 add_middleware할수록 외부(먼저 실행)
app.add_middleware(AccessLogMiddleware)
app.add_middleware(CorrelationIdMiddleware)

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/health", "/ready", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics")

app.include_router(health.router, tags=["probe"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
