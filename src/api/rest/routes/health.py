from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="auth-service")
