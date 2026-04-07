from __future__ import annotations

from typing import Any, Generic, Sequence, Type, TypeVar, cast

from loguru import logger
from sqlalchemy import ColumnExpressionArgument, delete, func, insert, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import PydanticOrmModel
from src.orm.filters.base import BaseFilterModel
from src.orm.models.base import Base
from src.orm.sorters.base import BaseSortModel

ModelT = TypeVar("ModelT", bound=Base)
FilterT = TypeVar("FilterT", bound=BaseFilterModel)
SortT = TypeVar("SortT", bound=BaseSortModel)
SchemaT = TypeVar("SchemaT", bound=PydanticOrmModel)


class DatabaseRepository(Generic[ModelT, FilterT, SortT, SchemaT]):
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
            logger.warning(message)
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
        sql = (
            update(self.__model__)
            .where(*clauses)
            .values([model.to_orm() for model in models])
        )
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
