from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.params import Depends

from src.handlers.orm.url_stats import GetListUrlStatsHandler
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.api.base import BasePayloadResponse
from src.api.v0.shortener.url_stats.schemas import (
    GetShortUrlStatsRequest,
    GetShortUrlStatsResponse,
)
from src.di.handlers.url_stats import (
    get_list_url_stats_handler,
)
from src.orm.filters.url import UrlFilter

router = APIRouter(prefix="/shortner", tags=["Stats"])


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
