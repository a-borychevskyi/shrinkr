from loguru import logger

from orm.filters.url import UrlFilter
from repositories.url import UrlRepository
from src.models.base import ManyCustomResponse
from src.models.url_stats.entity import UrlStatsModel
from src.orm.filters.url_stats import UrlStatsFilter
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.repositories.uow import UnitOfWork
from src.repositories.url_stats import UrlStatsRepository
from src.utils.exceptions.base import NotFound


class GetOneUrlStatsHandler:
    def __init__(
        self,
        url_stats_repository: UrlStatsRepository,
        url_repository: UrlRepository,
        uow: UnitOfWork,
    ):
        self.url_stats_repository = url_stats_repository
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, filters: UrlFilter) -> UrlStatsModel | None:
        async with self.uow as uow:
            session = uow.session

            url_response = await self.url_repository.get_one(
                filters=filters, async_session=session
            )
            if not url_response:
                logger.warning(f"Url not found for filters: {filters}")
                raise NotFound(message="Url not found")

            url_stats_response = await self.url_stats_repository.get_one(
                filters=UrlStatsFilter(url_id=url_response.id), async_session=session
            )

            return url_stats_response


class GetListUrlStatsHandler:
    def __init__(
        self,
        url_stats_repository: UrlStatsRepository,
        url_repository: UrlRepository,
        uow: UnitOfWork,
    ):
        self.url_stats_repository = url_stats_repository
        self.url_repository = url_repository
        self.uow = uow

    async def handle(
        self, filters: UrlFilter, sorters: UrlStatsSortModel
    ) -> ManyCustomResponse[UrlStatsModel]:
        async with self.uow as uow:
            session = uow.session

            url_response = await self.url_repository.get_one(
                filters=filters, async_session=session
            )
            if not url_response:
                logger.warning(f"Url not found for filters: {filters}")
                raise NotFound(message="Url not found")

            return await self.url_stats_repository.get_list(
                filters=UrlStatsFilter(url_id=url_response.id),
                async_session=session,
                sorters=sorters or UrlStatsSortModel(),
            )


class GetAllUrlStatsHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, sorters: UrlStatsSortModel) -> list[UrlStatsModel]:
        async with self.uow as uow:
            session = uow.session

            return await self.url_stats_repository.get_all(
                async_session=session,
                filters=UrlStatsFilter(),
                sorters=sorters or UrlStatsSortModel(),
            )


class CreateUrlStatsHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(
        self, url_id: int, user_agent: str, ip_address: str
    ) -> UrlStatsModel:
        async with self.uow as uow:
            session = uow.session

            model_to_create = UrlStatsModel(
                id=None,
                url_id=url_id,
                user_agent=user_agent,
                ip_address=ip_address,
                access_time=None,
            )

            return await self.url_stats_repository.create(
                model=model_to_create, async_session=session
            )


class CreateListUrlStatsHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, models: ...) -> int:
        async with self.uow as uow:
            session = uow.session

            models_to_create = [
                UrlStatsModel(
                    id=None,
                    url_id=model.url_id,
                    user_agent=model.user_agent,
                    ip_address=model.ip_address,
                    access_time=None,
                )
                for model in models
            ]

            return await self.url_stats_repository.create_list(
                models=models_to_create, async_session=session
            )


class UpdateUrlStatsHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, model: UrlStatsModel) -> UrlStatsModel:
        async with self.uow as uow:
            session = uow.session

            return await self.url_stats_repository.update_one(
                model=model, async_session=session
            )


class UpdateListUrlStatsHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, models: list[UrlStatsModel]) -> int:
        async with self.uow as uow:
            session = uow.session

            return await self.url_stats_repository.update_list(
                models=models, async_session=session
            )


class DeleteUrlStatsHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, model: UrlStatsModel) -> int:
        async with self.uow as uow:
            session = uow.session

            return await self.url_stats_repository.delete_one(
                model=model, async_session=session
            )
