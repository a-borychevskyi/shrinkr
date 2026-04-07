from fastapi import APIRouter

from src.api.base import BasePayloadResponse
from src.api.v0.system.schemas import HealthResponse

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/health", response_model=BasePayloadResponse[HealthResponse])
async def health() -> BasePayloadResponse[HealthResponse]:
    return BasePayloadResponse[HealthResponse](payload=HealthResponse(status="ok"))
