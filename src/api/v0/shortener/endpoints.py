from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.params import Depends
from fastapi.responses import RedirectResponse

from handlers.orm.url import UpdateUrlHandler, MarkAsActiveUrlHandler
from handlers.orm.url_stats import GetListUrlStatsHandler
from orm.sorters.url_stats import UrlStatsSortModel
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
    mark_as_active_url_handler,
    delete_url_handler,
)
from src.di.handlers.url_stats import (
    create_url_stats_handler,
    get_list_url_stats_handler,
)
from src.handlers.orm.url import (
    CreateUrlHandler,
    GetOneUrlHandler,
    MarkAsDeletedUrlHandler,
    MarkAsActiveUrlHandler,
    DeleteUrlHandler,
)
from src.handlers.orm.url_stats import CreateUrlStatsHandler
from src.orm.filters.url import UrlFilter

router = APIRouter(prefix="/shortner", tags=["shortener"])


@router.get(
    "/",
    response_model=None,
    status_code=302,
)
async def redirect_to_url(
    request: Request,
    query_params: Annotated[RedirectToUrlRequest, Query()],
    get_one_handler: Annotated[GetOneUrlHandler, Depends(get_one_url_handler)],
    create_stats_handler: Annotated[
        CreateUrlStatsHandler, Depends(create_url_stats_handler)
    ],
) -> RedirectResponse:
    filters = UrlFilter(short_code=query_params.short_code)
    response = await get_one_handler.handle(filters)
    if response is None:
        return RedirectResponse(url="/", status_code=302)

    _id = response.id if response.id is not None else -1
    ip_address = request.client.host if request.client is not None else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    await create_stats_handler.handle(
        url_id=_id,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return RedirectResponse(url=response.target_url, status_code=302)


@router.get(
    "/stats", response_model=BasePayloadResponse[list[GetShortUrlStatsResponse]]
)
async def get_short_url_stats(
    query_params: Annotated[GetShortUrlStatsRequest, Query()],
    get_list_handler: Annotated[
        GetListUrlStatsHandler, Depends(get_list_url_stats_handler)
    ],
) -> BasePayloadResponse[GetShortUrlStatsResponse]:
    filters = UrlFilter(short_code=query_params.short_code)
    response = await get_list_handler.handle(
        filters,
        sorters=UrlStatsSortModel(access_time="ASC"),
    )
    return BasePayloadResponse(
        payload=[
            GetShortUrlStatsResponse.model_validate(model) for model in response.data
        ],
        status_code=200,
    )


@router.post("/deactivate", response_model=BasePayloadResponse[DeactivateUrlResponse])
async def deactivate_short_url(
    body: DeactivateUrlRequest,
    mark_as_deleted_handler: Annotated[
        MarkAsDeletedUrlHandler, Depends(mark_as_deleted_url_handler)
    ],
) -> BasePayloadResponse[DeactivateUrlResponse]:
    response = await mark_as_deleted_handler.handle(body.short_code)

    message = "Short URL deactivated"
    status_code = 200
    if response is None:
        message = "Short URL is either not found or already deactivated"
        status_code = 404

    return BasePayloadResponse(
        payload=DeactivateUrlResponse(message=message), status_code=status_code
    )


@router.post("/activate", response_model=BasePayloadResponse[ActivateUrlResponse])
async def activate_short_url(
    body: ActivateUrlRequest,
    mark_as_active_handler: Annotated[
        MarkAsActiveUrlHandler, Depends(mark_as_active_url_handler)
    ],
) -> BasePayloadResponse[ActivateUrlResponse]:
    response = await mark_as_active_handler.handle(body.short_code)

    message = "Short URL activated"
    status_code = 200
    if response is None:
        message = "Short URL is either not found or already activated"
        status_code = 404

    return BasePayloadResponse(
        payload=ActivateUrlResponse(message=message), status_code=status_code
    )


@router.post("/", response_model=BasePayloadResponse[CreateShortUrlResponse])
async def create_short_url(
    body: CreateShortUrlRequest,
    create_handler: Annotated[CreateUrlHandler, Depends(create_url_handler)],
) -> BasePayloadResponse[CreateShortUrlResponse]:
    response = await create_handler.handle(str(body.target_url))
    return BasePayloadResponse(
        payload=CreateShortUrlResponse(short_code=response.short_code),
        status_code=201,
    )


@router.delete("/{short_code}", response_model=BasePayloadResponse[DeleteUrlResponse])
async def delete_short_url(
    query_params: Annotated[DeleteUrlRequest, Query()],
    delete_handler: Annotated[DeleteUrlHandler, Depends(delete_url_handler)],
) -> BasePayloadResponse[DeleteUrlResponse]:
    await delete_handler.handle(query_params.short_code)
    return BasePayloadResponse(
        payload=DeleteUrlResponse(message="Short URL deleted"), status_code=200
    )
