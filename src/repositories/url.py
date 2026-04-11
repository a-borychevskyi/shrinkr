from __future__ import annotations

from secrets import token_urlsafe

import orjson
from loguru import logger

from src.repositories.base import StringAbstractRepository
from src.orm.filters.url import UrlFilter
from src.orm.models import Url
from src.orm.sorters.url import UrlSortModel
from src.models.url.entity import UrlModel
from src.repositories.base import BaseDatabaseRepository


class UrlRepository(BaseDatabaseRepository[Url, UrlFilter, UrlSortModel, UrlModel]):
    __model__ = Url

    @staticmethod
    def get_short_code() -> str:
        return token_urlsafe(12)


class UrlCacheRepository(StringAbstractRepository[UrlModel]):
    __model__ = UrlModel

    async def get_by_short_code(self, short_code: str) -> UrlModel | None:
        retrieved = await super()._get(short_code)
        if not retrieved:
            logger.debug(f"Cache miss for short code: {short_code}")
            return None

        logger.debug(f"Cache hit for short code: {short_code}")
        return self._convert_to_entity_model(retrieved)

    async def set_short_code(self, short_code: str, url: UrlModel, ttl: int = 60 * 60 * 6) -> bool | None:
        logger.debug(f"Cache set for short code: {short_code}")
        await super()._set_value(short_code, orjson.dumps(url.model_dump()).decode())
        return await super().set_expire(short_code, ttl)
