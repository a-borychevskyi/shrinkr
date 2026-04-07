from datetime import UTC, datetime
from secrets import token_urlsafe

from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.repositories.uow import UnitOfWork
from src.repositories.url import UrlRepository
from src.utils.types.type_variables import FilterModelT


class GetOneUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, filters: FilterModelT):
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.get_one(
                filters=filters, async_session=session
            )


class GetListUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, filters: FilterModelT):
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.get_list(
                filters=filters, async_session=session
            )


class GetAllUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self):
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.get_all(async_session=session)


class CreateUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, model):
        async with self.uow as uow:
            session = uow.session

            model_to_create = UrlModel(
                id=None,
                target_url=model.target_url,
                short_code=self.url_repository.get_short_code(model=model),
                created_at=None,
                updated_at=None,
                deleted_at=None,
            )

            return await self.url_repository.create(
                model=model_to_create, async_session=session
            )


class CreateListUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, models):
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.create_list(
                models=models, async_session=session
            )


class UpdateUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, model):
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.update_one(
                model=model, async_session=session
            )


class UpdateListUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, models):
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.update_list(
                models=models, async_session=session
            )


class MarkAsDeletedUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, short_code: str):
        async with self.uow as uow:
            session = uow.session

            filters = UrlFilter(short_code=short_code)
            model = await self.url_repository.get_one(
                filters=filters, async_session=session
            )
            if not model or model.deleted_at:
                return None

            model.deleted_at = datetime.now(UTC).replace(tzinfo=None)
            return await self.url_repository.update_one(
                model=model, async_session=session
            )


class DeleteUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, model):
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.delete_one(
                model=model, async_session=session
            )
