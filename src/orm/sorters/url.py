from enum import StrEnum
from typing import Annotated

from pydantic import Field

from src.orm.sorters.base import BaseSortModel
from src.utils.enums.sort import SortOption


class UrlSortValues(StrEnum):
    id_asc = "id"
    id_desc = "-id"

    target_url_asc = "target_url"
    target_url_desc = "-target_url"

    short_code_asc = "short_code"
    short_code_desc = "-short_code"

    created_at_asc = "created_at"
    created_at_desc = "-created_at"

    updated_at_asc = "updated_at"
    updated_at_desc = "-updated_at"

    deleted_at_asc = "deleted_at"
    deleted_at_desc = "-deleted_at"


class UrlSortModel(BaseSortModel):
    id: Annotated[SortOption | None, Field()] = None
    target_url: Annotated[SortOption | None, Field()] = None
    short_code: Annotated[SortOption | None, Field()] = None
    created_at: Annotated[SortOption | None, Field()] = None
    updated_at: Annotated[SortOption | None, Field()] = None
    deleted_at: Annotated[SortOption | None, Field()] = None
