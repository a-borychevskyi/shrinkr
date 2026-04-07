from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.params import Depends
from fastapi.responses import RedirectResponse

from src.api.base import BasePayloadResponse
from src.api.v0.shortener.schemas import (
    ActivateUrlRequest,
    ActivateUrlResponse,
    CreateShortUrlRequest,
    CreateShortUrlResponse,
    DeactivateUrlRequest,
    DeactivateUrlResponse,
    DeleteUrlRequest,
    DeleteUrlResponse,
    GetShortUrlStatsRequest,
    GetShortUrlStatsResponse,
    RedirectToUrlRequest,
)
from src.di.handlers.url import (
    create_url_handler,
    get_one_url_handler,
    mark_as_deleted_url_handler,
)
from src.handlers.orm.url import (
    CreateUrlHandler,
    GetOneUrlHandler,
    MarkAsDeletedUrlHandler,
)
from src.orm.filters.url import UrlFilter

router = APIRouter(prefix="/shortner", tags=["shortener"])


@router.get("/", response_model=None, status_code=302)
async def redirect_to_url(
    query_params: Annotated[RedirectToUrlRequest, Query()],
    get_one_handler: Annotated[GetOneUrlHandler, Depends(get_one_url_handler)],
) -> RedirectResponse:
    filters = UrlFilter(short_code=query_params.short_code)
    response = await get_one_handler.handle(filters)
    return RedirectResponse(url=response.target_url, status_code=302)


@router.get("/stats", response_model=BasePayloadResponse[GetShortUrlStatsResponse])
async def get_short_url_stats(
    query_params: Annotated[GetShortUrlStatsRequest, Query()],
) -> BasePayloadResponse[GetShortUrlStatsResponse]:
    pass


@router.post("/deactivate", response_model=BasePayloadResponse[DeactivateUrlResponse])
async def deactivate_short_url(
    body: DeactivateUrlRequest,
    mark_as_deleted_handler: Annotated[
        MarkAsDeletedUrlHandler, Depends(mark_as_deleted_url_handler)
    ],
) -> BasePayloadResponse[DeactivateUrlResponse]:
    response = await mark_as_deleted_handler.handle(body.short_code)

    message = "Short URL deactivated"
    if response is None:
        message = "Short URL is either not found or already deactivated"

    return BasePayloadResponse(payload=DeactivateUrlResponse(message=message))


@router.post("/activate", response_model=BasePayloadResponse[ActivateUrlResponse])
async def activate_short_url(
    body: ActivateUrlRequest,
) -> BasePayloadResponse[ActivateUrlResponse]:
    pass


@router.post("/", response_model=BasePayloadResponse[CreateShortUrlResponse])
async def create_short_url(
    body: CreateShortUrlRequest,
    create_handler: Annotated[CreateUrlHandler, Depends(create_url_handler)],
) -> BasePayloadResponse[CreateShortUrlResponse]:
    response = await create_handler.handle(body)
    return BasePayloadResponse(
        payload=CreateShortUrlResponse(short_code=response.short_code)
    )


@router.delete("/{url_id}", response_model=BasePayloadResponse[DeleteUrlResponse])
async def delete_short_url(
    query_params: Annotated[DeleteUrlRequest, Query()],
) -> BasePayloadResponse[DeleteUrlResponse]:
    pass
