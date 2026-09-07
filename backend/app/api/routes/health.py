from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness/readiness probe -- wired into Container Apps health probes."""
    settings = get_settings()
    return HealthResponse(status="ok", app_env=settings.app_env, demo_mode=settings.demo_mode)
