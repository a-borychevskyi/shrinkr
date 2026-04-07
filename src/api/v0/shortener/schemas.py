from datetime import datetime

from pydantic import ConfigDict, Field, HttpUrl

from src.api.base import BaseRequest, BaseResponse


class RedirectToUrlRequest(BaseRequest):
    short_code: str = Field(
        ..., description="The short code to redirect to the target URL"
    )


class GetShortUrlStatsRequest(BaseRequest):
    short_code: str = Field(..., description="The short code to get stats for")


class GetShortUrlStatsResponse(BaseResponse):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="The id of the short URL to get stats for")
    url_id: int = Field(..., description="The id of the URL to get stats for")
    user_agent: str = Field(..., description="The user agent of the request")
    ip_address: str = Field(..., description="The IP address of the request")
    access_time: datetime = Field(..., description="The access time of the request")


class DeactivateUrlRequest(BaseRequest):
    short_code: str = Field(..., description="The short code to deactivate")


class DeactivateUrlResponse(BaseResponse):
    message: str = Field(..., description="The message of the response")


class ActivateUrlRequest(BaseRequest):
    short_code: str = Field(..., description="The short code to activate")


class ActivateUrlResponse(BaseResponse):
    message: str = Field(..., description="The message of the response")


class CreateShortUrlRequest(BaseRequest):
    target_url: HttpUrl = Field(..., description="The target URL to shorten")


class CreateShortUrlResponse(BaseResponse):
    short_code: str = Field(..., description="The short code of the created URL")


class DeleteUrlRequest(BaseRequest):
    short_code: str = Field(..., description="The id of the URL to delete")


class DeleteUrlResponse(BaseResponse):
    message: str = Field(..., description="The message of the response")


class CreateUrlStatsRequest(BaseRequest):
    url_id: int = Field(..., description="The id of the URL to create stats for")
    user_agent: str = Field(..., description="The user agent of the request")
    ip_address: str = Field(..., description="The IP address of the request")
