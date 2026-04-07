from enum import StrEnum
from typing import Annotated

from pydantic import Field

from src.orm.sorters.base import BaseSortModel
from src.utils.enums.sort import SortOption


class UrlStatsSortValues(StrEnum):
    id_asc = "id"
    id_desc = "-id"

    url_id_asc = "url_id"
    url_id_desc = "-url_id"

    user_agent_asc = "user_agent"
    user_agent_desc = "-user_agent"

    ip_address_asc = "ip_address"
    ip_address_desc = "-ip_address"

    redirect_elapsed_ms_asc = "redirect_elapsed_ms"
    redirect_elapsed_ms_desc = "-redirect_elapsed_ms"

    access_time_asc = "access_time"
    access_time_desc = "-access_time"


class UrlStatsSortModel(BaseSortModel):
    id: Annotated[SortOption | None, Field()] = None
    url_id: Annotated[SortOption | None, Field()] = None
    user_agent: Annotated[SortOption | None, Field()] = None
    ip_address: Annotated[SortOption | None, Field()] = None
    redirect_elapsed_ms: Annotated[SortOption | None, Field()] = None
    access_time: Annotated[SortOption | None, Field()] = None
