from __future__ import annotations

import time

import structlog

from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.orm.models import Url
from src.orm.sorters.url import UrlSortModel
from src.repositories.base import BaseDatabaseRepository, StringAbstractRepository
from src.repositories.metrics import (
    cache_operation_duration_seconds,
    cache_operations_total,
)

logger = structlog.get_logger(__name__)


class UrlRepository(BaseDatabaseRepository[Url, UrlFilter, UrlSortModel, UrlModel]):
    __model__ = Url


# Pre-built attribute dicts for the counter so we don't reallocate on
# every cache op. The OTel SDK keys view lookups on the attribute set;
# reusing the same dict lets it hit its internal aggregation cache.
_GET_HIT_ATTRS = {"operation": "get", "result": "hit"}
_GET_MISS_ATTRS = {"operation": "get", "result": "miss"}
_SET_OK_ATTRS = {"operation": "set", "result": "ok"}
_DELETE_OK_ATTRS = {"operation": "delete", "result": "ok"}
_DELETE_MISS_ATTRS = {"operation": "delete", "result": "miss"}
_GET_DURATION_ATTRS = {"operation": "get"}
_SET_DURATION_ATTRS = {"operation": "set"}
_DELETE_DURATION_ATTRS = {"operation": "delete"}


class UrlCacheRepository(StringAbstractRepository[UrlModel]):
    __model__ = UrlModel

    async def get_by_short_code(self, short_code: str) -> UrlModel | None:
        # RedisInstrumentor() emits a span for the underlying GET/SET/DEL
        # already, so we don't wrap our own span here — it was pure
        # overhead on the redirect hot path (~6k spans/s at 1700 rps).
        start = time.perf_counter()
        retrieved = await super()._get(short_code)
        elapsed = time.perf_counter() - start
        cache_operation_duration_seconds.record(elapsed, attributes=_GET_DURATION_ATTRS)

        if not retrieved:
            cache_operations_total.add(1, attributes=_GET_MISS_ATTRS)
            return None

        cache_operations_total.add(1, attributes=_GET_HIT_ATTRS)
        return self._convert_to_entity_model(retrieved)

    async def set_short_code(
        self, short_code: str, url: UrlModel, ttl: int = 60 * 60 * 6
    ) -> bool | None:
        start = time.perf_counter()
        # model_dump_json() skips the intermediate dict that
        # orjson.dumps(url.model_dump()) builds.
        result = await super()._set_value(short_code, url.model_dump_json(), ex=ttl)
        elapsed = time.perf_counter() - start
        cache_operation_duration_seconds.record(elapsed, attributes=_SET_DURATION_ATTRS)
        cache_operations_total.add(1, attributes=_SET_OK_ATTRS)
        return result

    async def delete_short_code(self, short_code: str) -> int:
        start = time.perf_counter()
        result = await super()._delete_by_key(short_code)
        elapsed = time.perf_counter() - start
        cache_operation_duration_seconds.record(
            elapsed, attributes=_DELETE_DURATION_ATTRS
        )
        attrs = _DELETE_OK_ATTRS if result > 0 else _DELETE_MISS_ATTRS
        cache_operations_total.add(1, attributes=attrs)
        return result
