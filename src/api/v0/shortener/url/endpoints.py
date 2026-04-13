from typing import Annotated

from fastapi import APIRouter, Query, Response
from fastapi.params import Depends
from opentelemetry import trace

from src.api.base import BasePayloadResponse
from src.api.v0.shortener.url.schemas import (
    ActivateUrlRequest,
    ActivateUrlResponse,
    CreateShortUrlRequest,
    CreateShortUrlResponse,
    DeactivateUrlRequest,
    DeactivateUrlResponse,
    DeleteUrlRequest,
    DeleteUrlResponse,
)
from src.di.repositories.url import get_url_cache_repository
from src.di.services.url import get_url_service
from src.repositories.url import UrlCacheRepository
from src.services.database.url import UrlService

router = APIRouter(prefix="/shortner", tags=["Urls"])

tracer = trace.get_tracer(__name__)


@router.post("/deactivate", response_model=BasePayloadResponse[DeactivateUrlResponse])
async def deactivate_short_url(
    body: DeactivateUrlRequest,
    url_service: Annotated[UrlService, Depends(get_url_service)],
    url_cache_repository: Annotated[
        UrlCacheRepository, Depends(get_url_cache_repository)
    ],
    response: Response,
) -> BasePayloadResponse[DeactivateUrlResponse]:
    span = trace.get_current_span()
    span.set_attribute("url.short_code", body.short_code)

    result = await url_service.mark_as_deleted(body.short_code)
    if result is not None:
        await url_cache_repository.delete_short_code(body.short_code)

    message = "Short URL deactivated"
    if result is None:
        message = "Short URL is either not found or already deactivated"
        response.status_code = 404

    return BasePayloadResponse[DeactivateUrlResponse](
        payload=DeactivateUrlResponse(message=message),
    )


@router.post("/activate", response_model=BasePayloadResponse[ActivateUrlResponse])
async def activate_short_url(
    body: ActivateUrlRequest,
    url_service: Annotated[UrlService, Depends(get_url_service)],
    url_cache_repository: Annotated[
        UrlCacheRepository, Depends(get_url_cache_repository)
    ],
    response: Response,
) -> BasePayloadResponse[ActivateUrlResponse]:
    span = trace.get_current_span()
    span.set_attribute("url.short_code", body.short_code)

    result = await url_service.mark_as_active(body.short_code)
    if result is not None:
        await url_cache_repository.set_short_code(body.short_code, result)

    message = "Short URL activated"
    if result is None:
        message = "Short URL is either not found or already activated"
        response.status_code = 404

    return BasePayloadResponse[ActivateUrlResponse](
        payload=ActivateUrlResponse(message=message),
    )


@router.post(
    "/",
    response_model=BasePayloadResponse[CreateShortUrlResponse],
    status_code=201,
)
async def create_short_url(
    body: CreateShortUrlRequest,
    url_service: Annotated[UrlService, Depends(get_url_service)],
    url_cache_repository: Annotated[
        UrlCacheRepository, Depends(get_url_cache_repository)
    ],
) -> BasePayloadResponse[CreateShortUrlResponse]:
    span = trace.get_current_span()
    span.set_attribute("url.target_url", str(body.target_url))

    result = await url_service.create(str(body.target_url))
    await url_cache_repository.set_short_code(result.short_code, result)

    span.set_attribute("url.short_code", result.short_code)
    return BasePayloadResponse[CreateShortUrlResponse](
        payload=CreateShortUrlResponse(short_code=result.short_code),
    )


@router.delete("/{short_code}", response_model=BasePayloadResponse[DeleteUrlResponse])
async def delete_short_url(
    query_params: Annotated[DeleteUrlRequest, Query()],
    url_service: Annotated[UrlService, Depends(get_url_service)],
    url_cache_repository: Annotated[
        UrlCacheRepository, Depends(get_url_cache_repository)
    ],
) -> BasePayloadResponse[DeleteUrlResponse]:
    span = trace.get_current_span()
    span.set_attribute("url.short_code", query_params.short_code)

    await url_service.delete(query_params.short_code)
    await url_cache_repository.delete_short_code(query_params.short_code)

    return BasePayloadResponse[DeleteUrlResponse](
        payload=DeleteUrlResponse(message="Short URL deleted"),
    )
