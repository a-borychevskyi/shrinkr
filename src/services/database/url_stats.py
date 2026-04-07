from loguru import logger

from src.models.base import ManyCustomResponse
from src.models.url_stats.entity import UrlStatsModel
from src.orm.filters.url import UrlFilter
from src.orm.filters.url_stats import UrlStatsFilter
from src.orm.models import UrlStats
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.repositories.uow import UnitOfWork
from src.repositories.url import UrlRepository
from src.repositories.url_stats import UrlStatsRepository
from src.utils.exceptions.base import NotFound


class UrlStatsService:
    def __init__(
        self,
        url_stats_repository: UrlStatsRepository,
        url_repository: UrlRepository,
        uow: UnitOfWork,
    ):
        self.url_stats_repository = url_stats_repository
        self.url_repository = url_repository
        self.uow = uow

    async def get_one(self, filters: UrlFilter) -> UrlStatsModel:
        async with self.uow as uow:
            url = await self.url_repository.get_one(
                filters=filters, async_session=uow.session
            )
            if not url:
                logger.warning(f"Url not found for filters: {filters}")
                raise NotFound(message="Url not found")

            result = await self.url_stats_repository.get_one(
                filters=UrlStatsFilter(url_id=url.id), async_session=uow.session
            )
            if not result:
                raise NotFound(message="UrlStats not found")
            return UrlStatsModel.model_validate(result)

    async def get_list(
        self,
        filters: UrlFilter,
        sorters: UrlStatsSortModel | None = None,
    ) -> ManyCustomResponse[UrlStatsModel]:
        async with self.uow as uow:
            url = await self.url_repository.get_one(
                filters=filters, async_session=uow.session
            )
            if not url:
                logger.warning(f"Url not found for filters: {filters}")
                raise NotFound(message="Url not found")

            count, data = await self.url_stats_repository.get_list(
                filters=UrlStatsFilter(url_id=url.id),
                async_session=uow.session,
                sorters=sorters or UrlStatsSortModel(),
            )
            return ManyCustomResponse[UrlStatsModel](
                count=count,
                data=[UrlStatsModel.model_validate(row) for row in data],
            )

    async def get_all(
        self, sorters: UrlStatsSortModel | None = None
    ) -> list[UrlStatsModel]:
        async with self.uow as uow:
            results = await self.url_stats_repository.get_all(
                async_session=uow.session,
                filters=UrlStatsFilter(),
                sorters=sorters or UrlStatsSortModel(),
            )
            return [UrlStatsModel.model_validate(row) for row in results]

    async def create(
        self, url_id: int, user_agent: str, ip_address: str
    ) -> UrlStatsModel:
        async with self.uow as uow:
            model = UrlStatsModel(
                url_id=url_id, user_agent=user_agent, ip_address=ip_address
            )
            result = await self.url_stats_repository.create(
                model=model, async_session=uow.session
            )
            return UrlStatsModel.model_validate(result)

    async def create_many(self, models: list[UrlStatsModel]) -> int:
        async with self.uow as uow:
            return await self.url_stats_repository.create_many(
                models=models, async_session=uow.session
            )

    async def update(self, model: UrlStatsModel) -> UrlStatsModel:
        async with self.uow as uow:
            result = await self.url_stats_repository.update(
                UrlStats.id == model.id, async_session=uow.session, model=model
            )
            return UrlStatsModel.model_validate(result)

    async def update_many(self, models: list[UrlStatsModel]) -> int:
        async with self.uow as uow:
            return await self.url_stats_repository.update_many(
                UrlStats.id.in_([m.id for m in models]),
                async_session=uow.session,
                models=models,
            )

    async def delete(self, model: UrlStatsModel) -> int:
        async with self.uow as uow:
            return await self.url_stats_repository.delete(
                UrlStats.id == model.id, async_session=uow.session
            )
