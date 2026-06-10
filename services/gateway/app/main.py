from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from .config import settings
from .telemetry import init_telemetry
from .logging_config import configure_logging
from .middleware import CorrelationIdMiddleware, AccessLogMiddleware
from .routes import health, products, orders

configure_logging(settings.service_name, settings.app_version)

app = FastAPI(
    title=settings.service_name,
    version=settings.app_version,
    docs_url="/docs",
)

init_telemetry(app, settings.service_name, settings.app_version, settings.otlp_endpoint)

app.add_middleware(AccessLogMiddleware)
app.add_middleware(CorrelationIdMiddleware)

# v2에서만 GZip 압축 활성화
if settings.app_version == "v2":
    app.add_middleware(GZipMiddleware, minimum_size=1000)

Instrumentator(
    should_group_status_codes=False,
    excluded_handlers=["/health", "/ready", "/metrics"],
).instrument(app).expose(app, endpoint="/metrics")

app.include_router(health.router, tags=["probe"])
app.include_router(products.router, prefix="/api/v1/products", tags=["products"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
