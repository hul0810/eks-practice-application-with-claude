import uuid
import structlog
from fastapi import APIRouter, HTTPException
from ..models import Product, ProductCreate, VersionedResponse
from ..store import product_store
from ..config import settings

router = APIRouter()
logger = structlog.get_logger()


def _serialize(product: Product) -> dict:
    data = product.model_dump()
    if settings.app_version == "v2":
        data["discount_rate"] = 0.1
    return data


@router.get("", response_model=VersionedResponse)
async def list_products():
    products = product_store.list_all()
    logger.info("list_products", count=len(products))
    return VersionedResponse(
        version=settings.app_version,
        service=settings.service_name,
        data=[_serialize(p) for p in products],
    )


@router.get("/{product_id}", response_model=VersionedResponse)
async def get_product(product_id: str):
    product = product_store.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")
    logger.info("get_product", product_id=product_id)
    return VersionedResponse(
        version=settings.app_version,
        service=settings.service_name,
        data=_serialize(product),
    )


@router.post("", response_model=VersionedResponse, status_code=201)
async def create_product(body: ProductCreate):
    product = Product(id=str(uuid.uuid4()), **body.model_dump())
    created = product_store.create(product)
    logger.info("create_product", product_id=created.id, name=created.name)
    return VersionedResponse(
        version=settings.app_version,
        service=settings.service_name,
        data=_serialize(created),
    )
