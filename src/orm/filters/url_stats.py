from datetime import datetime
from typing import Annotated

from pydantic import Field

from src.orm.filters.base import BaseFilterModel, Query
from src.orm.models import UrlStats


class UrlStatsFilter(BaseFilterModel):
    id: Annotated[int | None, Query(filter_by=lambda value: UrlStats.id == value)] = (
        Field(default=None)
    )
    id__in: Annotated[
        list[int] | None, Query(filter_by=lambda value: UrlStats.id.in_(value))
    ] = Field(default=None)
    id__notin: Annotated[
        list[int] | None, Query(filter_by=lambda value: UrlStats.id.notin_(value))
    ] = Field(default=None)

    url_id: Annotated[
        int | None, Query(filter_by=lambda value: UrlStats.url_id == value)
    ] = Field(default=None)
    url_id__in: Annotated[
        list[int] | None, Query(filter_by=lambda value: UrlStats.url_id.in_(value))
    ] = Field(default=None)
    url_id__notin: Annotated[
        list[int] | None, Query(filter_by=lambda value: UrlStats.url_id.notin_(value))
    ] = Field(default=None)

    user_agent: Annotated[
        str | None, Query(filter_by=lambda value: UrlStats.user_agent == value)
    ] = Field(default=None)
    user_agent__contains: Annotated[
        str | None, Query(filter_by=lambda value: UrlStats.user_agent.contains(value))
    ] = Field(default=None)

    ip_address: Annotated[
        str | None, Query(filter_by=lambda value: UrlStats.ip_address == value)
    ] = Field(default=None)
    ip_address__contains: Annotated[
        str | None, Query(filter_by=lambda value: UrlStats.ip_address.contains(value))
    ] = Field(default=None)

    access_time: Annotated[
        datetime | None, Query(filter_by=lambda value: UrlStats.access_time == value)
    ] = Field(default=None)
    access_time__gt: Annotated[
        datetime | None, Query(filter_by=lambda value: UrlStats.access_time > value)
    ] = Field(default=None)
    access_time__lt: Annotated[
        datetime | None, Query(filter_by=lambda value: UrlStats.access_time < value)
    ] = Field(default=None)
    access_time__between: Annotated[
        tuple[datetime, datetime] | None,
        Query(filter_by=lambda value: UrlStats.access_time.between(*value)),
    ] = Field(default=None)
