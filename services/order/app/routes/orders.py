import uuid
import structlog
import httpx
from fastapi import APIRouter, HTTPException
from structlog.contextvars import get_contextvars
from ..models import Order, OrderCreate, VersionedResponse
from ..store import order_store
from ..config import settings

router = APIRouter()
logger = structlog.get_logger()


async def _verify_product(product_id: str, quantity: int) -> dict:
    ctx = get_contextvars()
    # correlation_id 전파 + HTTPXClientInstrumentor가 traceparent 자동 주입
    headers = {"X-Request-ID": ctx.get("correlation_id", "")}

    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(
            f"{settings.catalog_url}/api/v1/products/{product_id}",
            headers=headers,
        )

    if response.status_code == 404:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    response.raise_for_status()

    product = response.json()["data"]
    if product["stock"] < quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock: available {product['stock']}, requested {quantity}",
        )
    return product


def _serialize(order: Order) -> dict:
    data = order.model_dump()
    if settings.app_version != "v2":
        data.pop("priority", None)
    return data


@router.get("", response_model=VersionedResponse)
async def list_orders():
    orders = order_store.list_all()
    return VersionedResponse(
        version=settings.app_version,
        service=settings.service_name,
        data=[_serialize(o) for o in orders],
    )


@router.get("/{order_id}", response_model=VersionedResponse)
async def get_order(order_id: str):
    order = order_store.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return VersionedResponse(
        version=settings.app_version,
        service=settings.service_name,
        data=_serialize(order),
    )


@router.post("", response_model=VersionedResponse, status_code=201)
async def create_order(body: OrderCreate):
    await _verify_product(body.product_id, body.quantity)

    order = Order(
        id=str(uuid.uuid4()),
        product_id=body.product_id,
        quantity=body.quantity,
        priority=body.priority if settings.app_version == "v2" else "normal",
    )
    created = order_store.create(order)
    logger.info("create_order", order_id=created.id, product_id=body.product_id)
    return VersionedResponse(
        version=settings.app_version,
        service=settings.service_name,
        data=_serialize(created),
    )
