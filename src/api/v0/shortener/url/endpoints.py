from typing import Annotated

from fastapi import APIRouter, Query, Request, Response
from fastapi.params import Depends
from fastapi.responses import RedirectResponse
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
    RedirectToUrlRequest,
)
from src.di.repositories.url import get_url_cache_repository
from src.di.services.url import get_url_service
from src.di.services.url_stats import get_url_stats_service
from src.orm.filters.url import UrlFilter
from src.repositories.url import UrlCacheRepository
from src.services.database.url import UrlService
from src.services.database.url_stats import UrlStatsService

router = APIRouter(prefix="/shortner", tags=["Urls"])

tracer = trace.get_tracer(__name__)


@router.get(
    "/",
    response_model=None,
    status_code=302,
)
async def redirect_to_url(
    request: Request,
    query_params: Annotated[RedirectToUrlRequest, Query()],
    url_service: Annotated[UrlService, Depends(get_url_service)],
    url_cache_repository: Annotated[
        UrlCacheRepository, Depends(get_url_cache_repository)
    ],
    url_stats_service: Annotated[UrlStatsService, Depends(get_url_stats_service)],
) -> RedirectResponse:
    span = trace.get_current_span()
    span.set_attribute("url.short_code", query_params.short_code)

    response = await url_cache_repository.get_by_short_code(query_params.short_code)
    cache_hit = response is not None
    if not cache_hit:
        filters = UrlFilter(short_code=query_params.short_code)
        response = await url_service.get_one(filters)
        await url_cache_repository.set_short_code(query_params.short_code, response)

    span.set_attribute("cache.hit", cache_hit)

    if response is None:
        span.set_attribute("url.found", False)
        return RedirectResponse(url="/", status_code=302)

    span.set_attribute("url.found", True)
    span.set_attribute("url.target_url", response.target_url)

    _id = response.id if response.id is not None else -1
    ip_address = request.client.host if request.client is not None else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    await url_stats_service.create(
        url_id=_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return RedirectResponse(url=response.target_url, status_code=302)


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
