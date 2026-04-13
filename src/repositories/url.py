from __future__ import annotations

import time

import orjson
import structlog
from opentelemetry import trace

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
tracer = trace.get_tracer(__name__)


class UrlRepository(BaseDatabaseRepository[Url, UrlFilter, UrlSortModel, UrlModel]):
    __model__ = Url


class UrlCacheRepository(StringAbstractRepository[UrlModel]):
    __model__ = UrlModel

    async def get_by_short_code(self, short_code: str) -> UrlModel | None:
        with tracer.start_as_current_span(
            "cache.get",
            attributes={"cache.key": short_code},
        ) as span:
            start = time.perf_counter()
            retrieved = await super()._get(short_code)
            elapsed = time.perf_counter() - start
            cache_operation_duration_seconds.record(
                elapsed, attributes={"operation": "get"}
            )

            if not retrieved:
                logger.debug("cache_miss", short_code=short_code)
                span.set_attribute("cache.hit", False)
                cache_operations_total.add(
                    1, attributes={"operation": "get", "result": "miss"}
                )
                return None

            logger.debug("cache_hit", short_code=short_code)
            span.set_attribute("cache.hit", True)
            cache_operations_total.add(
                1, attributes={"operation": "get", "result": "hit"}
            )
            return self._convert_to_entity_model(retrieved)

    async def set_short_code(
        self, short_code: str, url: UrlModel, ttl: int = 60 * 60 * 6
    ) -> bool | None:
        with tracer.start_as_current_span(
            "cache.set",
            attributes={"cache.key": short_code, "cache.ttl_seconds": ttl},
        ):
            logger.debug("cache_set", short_code=short_code)
            start = time.perf_counter()
            result = await super()._set_value(
                short_code, orjson.dumps(url.model_dump()).decode(), ex=ttl
            )
            elapsed = time.perf_counter() - start
            cache_operation_duration_seconds.record(
                elapsed, attributes={"operation": "set"}
            )
            cache_operations_total.add(
                1, attributes={"operation": "set", "result": "ok"}
            )
            return result

    async def delete_short_code(self, short_code: str) -> int:
        with tracer.start_as_current_span(
            "cache.delete",
            attributes={"cache.key": short_code},
        ):
            logger.debug("cache_delete", short_code=short_code)
            start = time.perf_counter()
            result = await super()._delete_by_key(short_code)
            elapsed = time.perf_counter() - start
            cache_operation_duration_seconds.record(
                elapsed, attributes={"operation": "delete"}
            )
            result_label = "ok" if result > 0 else "miss"
            cache_operations_total.add(
                1, attributes={"operation": "delete", "result": result_label}
            )
            return result
