from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime

from app.config import APP_NAME, APP_VERSION

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    app: str
    version: str
    message: str
    timestamp: datetime


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check():
    """Quick check to confirm DataSnoop is up and running."""
    return HealthResponse(
        status="healthy",
        app=APP_NAME,
        version=APP_VERSION,
        message="Everything looks good!",
        timestamp=datetime.now(),
    )
