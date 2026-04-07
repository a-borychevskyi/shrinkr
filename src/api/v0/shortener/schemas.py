from pydantic import Field

from src.api.base import BaseRequest, BaseResponse


class RedirectToUrlRequest(BaseRequest):
    short_code: str = Field(
        ..., description="The short code to redirect to the target URL"
    )


class GetShortUrlStatsRequest(BaseRequest):
    short_code: str = Field(..., description="The short code to get statistics for")


class GetShortUrlStatsResponse(BaseResponse):
    stats: dict = Field(..., description="The statistics of the short URL")


class DeactivateUrlRequest(BaseRequest):
    short_code: str = Field(..., description="The short code to deactivate")


class DeactivateUrlResponse(BaseResponse):
    message: str = Field(..., description="The message of the response")


class ActivateUrlRequest(BaseRequest):
    short_code: str = Field(..., description="The short code to activate")


class ActivateUrlResponse(BaseResponse):
    message: str = Field(..., description="The message of the response")


class CreateShortUrlRequest(BaseRequest):
    target_url: str = Field(..., description="The target URL to shorten")


class CreateShortUrlResponse(BaseResponse):
    short_code: str = Field(..., description="The short code of the created URL")


class DeleteUrlRequest(BaseRequest):
    url_id: int = Field(..., description="The id of the URL to delete")


class DeleteUrlResponse(BaseResponse):
    message: str = Field(..., description="The message of the response")
