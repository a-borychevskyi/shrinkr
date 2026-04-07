from src.repositories.uow import UnitOfWork
from src.repositories.url_stats import UrlStatsRepository
from src.utils.types.type_variables import FilterModelT


class GetOneUrlHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, filters: FilterModelT):
        async with self.uow as uow:
            session = uow.session
            if not session:
                raise Exception("Session is not opened")

            return await self.url_stats_repository.get_one(
                filters=filters, async_session=session
            )


class GetListUrlHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, filters: FilterModelT):
        async with self.uow as uow:
            session = uow.session
            if not session:
                raise Exception("Session is not opened")

            return await self.url_stats_repository.get_list(
                filters=filters, async_session=session
            )


class GetAllUrlHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self):
        async with self.uow as uow:
            session = uow.session
            if not session:
                raise Exception("Session is not opened")

            return await self.url_stats_repository.get_all(async_session=session)


class CreateUrlHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, model):
        async with self.uow as uow:
            session = uow.session
            if not session:
                raise Exception("Session is not opened")

            return await self.url_stats_repository.create(
                model=model, async_session=session
            )


class CreateListUrlHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, models):
        async with self.uow as uow:
            session = uow.session
            if not session:
                raise Exception("Session is not opened")

            return await self.url_stats_repository.create_list(
                models=models, async_session=session
            )


class UpdateUrlHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, model):
        async with self.uow as uow:
            session = uow.session
            if not session:
                raise Exception("Session is not opened")

            return await self.url_stats_repository.update_one(
                model=model, async_session=session
            )


class UpdateListUrlHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, models):
        async with self.uow as uow:
            session = uow.session
            if not session:
                raise Exception("Session is not opened")

            return await self.url_stats_repository.update_list(
                models=models, async_session=session
            )


class DeleteUrlHandler:
    def __init__(self, url_stats_repository: UrlStatsRepository, uow: UnitOfWork):
        self.url_stats_repository = url_stats_repository
        self.uow = uow

    async def handle(self, model):
        async with self.uow as uow:
            session = uow.session
            if not session:
                raise Exception("Session is not opened")

            return await self.url_stats_repository.delete_one(
                model=model, async_session=session
            )
