from __future__ import annotations

from secrets import token_urlsafe

from src.orm.filters.url import UrlFilter
from src.orm.models import Url
from src.orm.sorters.url import UrlSortModel
from src.models.url.entity import UrlModel
from src.repositories.base import DatabaseRepository


class UrlRepository(DatabaseRepository[Url, UrlFilter, UrlSortModel, UrlModel]):
    __model__ = Url

    @staticmethod
    def get_short_code() -> str:
        return token_urlsafe(12)
