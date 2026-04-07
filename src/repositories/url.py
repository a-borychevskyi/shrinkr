from __future__ import annotations

from secrets import token_urlsafe

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.base import ManyCustomResponse
from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.orm.models import Url
from src.orm.sorters.url import UrlSortModel
from src.repositories.base import DatabaseRepository


class UrlRepository(DatabaseRepository[Url, UrlFilter, UrlSortModel, UrlModel]):
    __model__ = Url

    @staticmethod
    def get_short_code() -> str:
        return token_urlsafe(12)

    async def get_one(
        self,
        async_session: AsyncSession,
        filters: UrlFilter,
    ) -> UrlModel | None:
        result = await super().get_one(async_session, filters)
        if not result:
            return None
        return UrlModel.model_validate(result)

    async def get_list(
        self,
        async_session: AsyncSession,
        filters: UrlFilter,
        sorters: UrlSortModel,
        page: int = 1,
        per_page: int = 10,
    ) -> ManyCustomResponse[UrlModel]:
        count, data = await super().get_list(
            async_session, filters, sorters, page, per_page
        )
        return ManyCustomResponse[UrlModel](
            count=count,
            data=[UrlModel.model_validate(result) for result in data],
        )

    async def get_all(
        self,
        async_session: AsyncSession,
        filters: UrlFilter,
        sorters: UrlSortModel,
    ) -> list[UrlModel]:
        results = await super().get_all(async_session, filters, sorters)
        return [UrlModel.model_validate(url) for url in results]

    async def create(
        self,
        async_session: AsyncSession,
        model: UrlModel,
    ) -> UrlModel:
        result = await super().create(async_session, model)
        return UrlModel.model_validate(result)

    async def create_list(
        self,
        async_session: AsyncSession,
        models: list[UrlModel],
    ) -> int:
        return await super().create_many(async_session, models)

    async def update_one(
        self,
        async_session: AsyncSession,
        model: UrlModel,
    ):
        result = await super().update(
            Url.id == model.id, async_session=async_session, model=model
        )
        return UrlModel.model_validate(result)

    async def update_list(self, async_session: AsyncSession, models: list[UrlModel]):
        return await super().update_many(
            Url.id.in_([model.id for model in models]),
            async_session=async_session,
            models=models,
        )

    async def delete_one(
        self,
        async_session: AsyncSession,
        model: UrlModel,
    ):
        return await super().delete(Url.id == model.id, async_session=async_session)
