from fastapi import APIRouter
from ..config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "version": settings.release_version, "service": settings.service_name}


@router.get("/ready")
async def ready():
    # catalog 연결 가능 여부 확인
    import httpx
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.catalog_url}/health")
            resp.raise_for_status()
        return {"status": "ready", "version": settings.release_version, "service": settings.service_name}
    except Exception:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="catalog unreachable")


@router.get("/version")
async def version():
    return {"version": settings.release_version, "service": settings.service_name}
