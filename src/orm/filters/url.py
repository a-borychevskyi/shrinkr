from datetime import datetime
from typing import Annotated

from pydantic import Field

from src.orm.filters.base import BaseFilterModel, Query
from src.orm.models import Url


class UrlFilter(BaseFilterModel):
    id: Annotated[int | None, Query(filter_by=lambda value: Url.id == value)] = Field(
        default=None
    )
    id__in: Annotated[
        list[int] | None, Query(filter_by=lambda value: Url.id.in_(value))
    ] = Field(default=None)
    id__notin: Annotated[
        list[int] | None, Query(filter_by=lambda value: Url.id.notin_(value))
    ] = Field(default=None)

    target_url: Annotated[
        str | None, Query(filter_by=lambda value: Url.target_url == value)
    ] = Field(default=None)
    target_url__contains: Annotated[
        str | None, Query(filter_by=lambda value: Url.target_url.contains(value))
    ] = Field(default=None)

    short_code: Annotated[
        str | None, Query(filter_by=lambda value: Url.short_code == value)
    ] = Field(default=None)
    short_code__in: Annotated[
        list[str] | None, Query(filter_by=lambda value: Url.short_code.in_(value))
    ] = Field(default=None)

    created_at: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.created_at == value)
    ] = Field(default=None)
    created_at__gt: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.created_at > value)
    ] = Field(default=None)
    created_at__lt: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.created_at < value)
    ] = Field(default=None)
    created_at__between: Annotated[
        tuple[datetime, datetime] | None,
        Query(filter_by=lambda value: Url.created_at.between(*value)),
    ] = Field(default=None)

    updated_at: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.updated_at == value)
    ] = Field(default=None)
    updated_at__gt: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.updated_at > value)
    ] = Field(default=None)
    updated_at__lt: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.updated_at < value)
    ] = Field(default=None)
    updated_at__between: Annotated[
        tuple[datetime, datetime] | None,
        Query(filter_by=lambda value: Url.updated_at.between(*value)),
    ] = Field(default=None)

    deleted_at: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.deleted_at == value)
    ] = Field(default=None)
    deleted_at__is_null: Annotated[
        bool | None, Query(filter_by=lambda value: Url.deleted_at.is_(None))
    ] = Field(default=None)
    deleted_at__is_not_null: Annotated[
        bool | None, Query(filter_by=lambda value: Url.deleted_at.is_not(None))
    ] = Field(default=None)
    deleted_at__gt: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.deleted_at > value)
    ] = Field(default=None)
    deleted_at__lt: Annotated[
        datetime | None, Query(filter_by=lambda value: Url.deleted_at < value)
    ] = Field(default=None)
    deleted_at__between: Annotated[
        tuple[datetime, datetime] | None,
        Query(filter_by=lambda value: Url.deleted_at.between(*value)),
    ] = Field(default=None)
