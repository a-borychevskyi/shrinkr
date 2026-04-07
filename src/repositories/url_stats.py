from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import ManyCustomResponse
from src.models.url_stats.entity import UrlStatsModel
from src.orm.filters.url_stats import UrlStatsFilter
from src.orm.models import UrlStats
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.repositories.base import DatabaseRepository


class UrlStatsRepository[Model: UrlStats](DatabaseRepository):
    __model__ = Model

    async def get_one(
        self,
        async_session: AsyncSession,
        filters: UrlStatsFilter,
    ) -> UrlStatsModel | None:
        result = await super().get_one(async_session, filters)
        return UrlStatsModel.model_validate(result)

    async def get_list(
        self,
        async_session: AsyncSession,
        filters: UrlStatsFilter,
        sorters: UrlStatsSortModel,
        page: int = 1,
        per_page: int = 10,
    ) -> ManyCustomResponse[UrlStats]:
        results = await super().get_list(
            async_session, filters, sorters, page, per_page
        )
        return ManyCustomResponse[UrlStats](
            count=results.count,
            data=[UrlStatsModel.model_validate(result) for result in results.data],
        )

    async def get_all(
        self,
        async_session: AsyncSession,
        filters: UrlStatsFilter,
        sorters: UrlStatsSortModel,
    ) -> list[UrlStatsModel]:
        results = await super().get_all(async_session, filters, sorters)
        return [UrlStatsModel.model_validate(url) for url in results]

    async def create(
        self,
        async_session: AsyncSession,
        model: UrlStats,
    ) -> UrlStatsModel:
        result = await super().create(async_session, model)
        return UrlStatsModel.model_validate(result)

    async def create_list(
        self,
        async_session: AsyncSession,
        models: list[UrlStatsModel],
    ) -> int:
        return await super().create_many(async_session, models)

    async def update_one(
        self,
        async_session: AsyncSession,
        model: UrlStatsModel,
    ):
        result = await super().update(
            UrlStats.id == model.id, async_session=async_session, model=model
        )
        return UrlStatsModel.model_validate(result)

    async def update_list(
        self, async_session: AsyncSession, models: list[UrlStatsModel]
    ):
        return await super().update_many(
            UrlStats.id.in_([model.id for model in models]),
            async_session=async_session,
            models=models,
        )

    async def delete_one(
        self,
        async_session: AsyncSession,
        model: UrlStatsModel,
    ):
        return await super().delete(
            UrlStats.id == model.id, async_session=async_session
        )
