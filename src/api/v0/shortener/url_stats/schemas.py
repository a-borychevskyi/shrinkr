from datetime import datetime

from pydantic import ConfigDict, Field

from src.api.base import BaseRequest, BaseResponse


class GetShortUrlStatsRequest(BaseRequest):
    short_code: str = Field(..., description="The short code to get stats for")


class GetShortUrlStatsResponse(BaseResponse):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="The id of the short URL to get stats for")
    url_id: int = Field(..., description="The id of the URL to get stats for")
    user_agent: str = Field(..., description="The user agent of the request")
    ip_address: str = Field(..., description="The IP address of the request")
    access_time: datetime = Field(..., description="The access time of the request")


class CreateUrlStatsRequest(BaseRequest):
    url_id: int = Field(..., description="The id of the URL to create stats for")
    user_agent: str = Field(..., description="The user agent of the request")
    ip_address: str = Field(..., description="The IP address of the request")
