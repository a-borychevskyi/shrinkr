from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.params import Depends
from opentelemetry import trace

from src.api.base import BasePayloadResponse
from src.api.v0.shortener.url_stats.schemas import (
    GetShortUrlStatsRequest,
    GetShortUrlStatsResponse,
)
from src.di.services.url_stats import get_url_stats_service
from src.orm.filters.url import UrlFilter
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.services.database.url_stats import UrlStatsService
from src.utils.enums.sort import SortOption

router = APIRouter(prefix="/shortner", tags=["Stats"])


@router.get(
    "/stats", response_model=BasePayloadResponse[list[GetShortUrlStatsResponse]]
)
async def get_short_url_stats(
    query_params: Annotated[GetShortUrlStatsRequest, Query()],
    url_stats_service: Annotated[UrlStatsService, Depends(get_url_stats_service)],
) -> BasePayloadResponse[list[GetShortUrlStatsResponse]]:
    span = trace.get_current_span()
    span.set_attribute("url.short_code", query_params.short_code)

    filters = UrlFilter(short_code=query_params.short_code)
    response = await url_stats_service.get_list(
        filters,
        sorters=UrlStatsSortModel(access_time=SortOption.ASC),
    )

    span.set_attribute("url_stats.result_count", response.count or 0)
    return BasePayloadResponse[list[GetShortUrlStatsResponse]](
        payload=[
            GetShortUrlStatsResponse.model_validate(model) for model in response.data
        ],
    )
