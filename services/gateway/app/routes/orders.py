import httpx
from fastapi import APIRouter, Request, Response
from structlog.contextvars import get_contextvars
from ..config import settings

router = APIRouter()

_EXCLUDED_REQUEST_HEADERS = {"host", "content-length", "transfer-encoding"}
_EXCLUDED_RESPONSE_HEADERS = {"content-length", "transfer-encoding"}


async def _proxy(method: str, url: str, request: Request) -> Response:
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in _EXCLUDED_REQUEST_HEADERS
    }
    ctx = get_contextvars()
    headers["X-Request-ID"] = ctx.get("correlation_id", "")

    body = await request.body()

    async with httpx.AsyncClient(timeout=10.0) as client:
        upstream = await client.request(
            method=method,
            url=url,
            headers=headers,
            content=body,
            params=dict(request.query_params),
        )

    response_headers = {
        k: v for k, v in upstream.headers.items()
        if k.lower() not in _EXCLUDED_RESPONSE_HEADERS
    }
    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=response_headers,
        media_type=upstream.headers.get("content-type"),
    )


@router.get("")
async def list_orders(request: Request):
    return await _proxy("GET", f"{settings.order_url}/api/v1/orders", request)


@router.get("/{order_id}")
async def get_order(order_id: str, request: Request):
    return await _proxy("GET", f"{settings.order_url}/api/v1/orders/{order_id}", request)


@router.post("")
async def create_order(request: Request):
    return await _proxy("POST", f"{settings.order_url}/api/v1/orders", request)
