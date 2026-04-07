from pydantic import Field

from src.api.base import BaseResponse


class HealthResponse(BaseResponse):
    status: str = Field(..., description="The health status of the system")
