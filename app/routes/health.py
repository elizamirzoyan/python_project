from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import APP_NAME, APP_VERSION

router = APIRouter()


class HealthResponse(BaseModel):
    """Response shape for the health-check endpoint."""

    status: str
    app: str
    version: str
    message: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """Confirm that the DataSnoop API is up and accepting requests."""
    return HealthResponse(
        status="healthy",
        app=APP_NAME,
        version=APP_VERSION,
        message="Everything looks good!",
        timestamp=datetime.now(),
    )
