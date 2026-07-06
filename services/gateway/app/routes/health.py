from fastapi import APIRouter
from ..config import settings

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "version": settings.release_version, "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"status": "ready", "version": settings.release_version, "service": settings.service_name}


@router.get("/version")
async def version():
    return {"version": settings.release_version, "service": settings.service_name}
