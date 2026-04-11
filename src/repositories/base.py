from __future__ import annotations

from abc import ABC
from typing import Any, Generic, Sequence, Type, TypeVar, cast

import orjson
import structlog
from redis.asyncio import Redis
from sqlalchemy import ColumnExpressionArgument, delete, func, insert, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.redis import RedisConfig
from src.models.base import BaseEntityModel
from src.models.base import PydanticOrmModel
from src.orm.filters.base import BaseFilterModel
from src.orm.models.base import Base
from src.orm.sorters.base import BaseSortModel
from src.utils.exceptions.base import BaseApplicationException

logger = structlog.get_logger(__name__)

ModelT = TypeVar("ModelT", bound=Base)
FilterT = TypeVar("FilterT", bound=BaseFilterModel)
SortT = TypeVar("SortT", bound=BaseSortModel)
SchemaT = TypeVar("SchemaT", bound=PydanticOrmModel)


class BaseDatabaseRepository(Generic[ModelT, FilterT, SortT, SchemaT]):
    __model__: Type[ModelT]

    async def get_one(
        self,
        async_session: AsyncSession,
        filters: FilterT,
    ) -> Any:
        sql = filters.generate_filtered_query(expression=select(self.__model__))
        result = await async_session.execute(statement=sql)
        if not (orm_model := result.scalar_one_or_none()):
            message = f"Unable to get: does not have any records for sql: {sql} by provided filters: {filters}"
            logger.warning("record_not_found", detail=message)
            return None
        return orm_model

    async def get_list(
        self,
        async_session: AsyncSession,
        filters: FilterT,
        sorters: SortT,
        page: int = 1,
        per_page: int = 10,
    ) -> Any:
        sql = filters.generate_filtered_query(expression=select(self.__model__))
        result = await async_session.execute(
            sql.order_by(*sorters.generate_params())
            .limit(limit=per_page)
            .offset(offset=(page - 1) * per_page)
        )
        data = list(result.scalars().all())
        count_result = await async_session.execute(
            statement=select(func.count()).select_from(sql.subquery())
        )
        count = count_result.scalar() or 0

        return count, data

    async def get_all(
        self,
        async_session: AsyncSession,
        filters: FilterT,
        sorters: SortT,
    ) -> Any:
        sql = filters.generate_filtered_query(expression=select(self.__model__))
        result = await async_session.execute(
            statement=sql.order_by(*sorters.generate_params())
        )
        return result.scalars().all()

    async def create(
        self,
        async_session: AsyncSession,
        model: SchemaT,
    ) -> Any | None:
        sql = insert(self.__model__).values(model.to_orm()).returning(self.__model__)
        return (await async_session.execute(statement=sql)).scalar()

    async def create_many(
        self,
        async_session: AsyncSession,
        models: Sequence[SchemaT],
    ) -> int:
        sql = insert(self.__model__).values([model.to_orm() for model in models])
        return cast(
            CursorResult[Any], await async_session.execute(statement=sql)
        ).rowcount

    async def update(
        self,
        *clauses: ColumnExpressionArgument,
        async_session: AsyncSession,
        model: SchemaT,
    ):
        sql = (
            update(self.__model__)
            .where(*clauses)
            .values(model.to_orm())
            .returning(self.__model__)
        )
        return (await async_session.execute(statement=sql)).scalar()

    async def update_many(
        self,
        *clauses: ColumnExpressionArgument,
        async_session: AsyncSession,
        models: Sequence[SchemaT],
    ):
        merged: dict[str, Any] = {}
        for model in models:
            merged.update(model.to_orm())
        sql = update(self.__model__).where(*clauses).values(**merged)
        return cast(
            CursorResult[Any], await async_session.execute(statement=sql)
        ).rowcount

    async def delete(
        self,
        *clauses: ColumnExpressionArgument,
        async_session: AsyncSession,
    ):
        sql = delete(self.__model__).where(*clauses)
        return cast(
            CursorResult[Any], await async_session.execute(statement=sql)
        ).rowcount


type _StrType = str | bytes


class BaseAbstractCacheRepository[AbstractModel: BaseEntityModel](ABC):
    """Base class for else repositories which work with cache"""

    __model__: AbstractModel

    def __init__(self, redis_client: Redis, config: RedisConfig) -> None:
        self.redis_client = redis_client
        self.application_prefix = config.APP_PREFIX

    def _get_key(self, key: str) -> str:
        return f"{self.application_prefix}:{key}"

    def _convert_to_entity_model(self, retrieved: Any) -> AbstractModel:
        if not retrieved:
            raise BaseApplicationException(
                message="Unable to convert to entity model: retrieved value is empty"
            )

        return self.__model__.model_validate(orjson.loads(retrieved))

    async def _delete_by_key(self, key: str) -> int:
        return await self.redis_client.delete(self._get_key(key))

    async def base_set(self, key: str, value: _StrType, **kwargs) -> bool | None:
        return await self.redis_client.set(self._get_key(key), value, **kwargs)

    async def base_get(self, key: str) -> _StrType | None:
        return await self.redis_client.get(self._get_key(key))

    async def set_expire(self, key: str, expire: int) -> bool:
        return await self.redis_client.expire(self._get_key(key), expire)

    async def _delete_by_keys(self, keys: list[str]) -> int:
        return await self.redis_client.delete(*keys)


class StringAbstractRepository[AbstractModel: BaseEntityModel](
    BaseAbstractCacheRepository[AbstractModel]
):
    """Base class for work with string data types"""

    __model__: Type = AbstractModel  # type: ignore[misc, assignment]

    async def _set_value(
        self, key: str, value: str, ex: int | None = None, **kwargs
    ) -> bool | None:
        return await self.redis_client.set(self._get_key(key), value, ex=ex, **kwargs)

    async def _get_keys(self, pattern: str) -> list[str]:
        return await self.redis_client.keys(self._get_key(pattern))

    async def _get_content_by_keys(self, keys: list[str]) -> list:
        prefix_keys = [self._get_key(key) for key in keys]
        return await self.redis_client.mget(keys=prefix_keys)

    async def _get(self, key: str) -> str | None:
        return await self.redis_client.get(self._get_key(key))

    async def _append(self, key: str, value: str) -> int:
        return await self.redis_client.append(self._get_key(key), value)
