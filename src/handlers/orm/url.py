from datetime import UTC, datetime

from loguru import logger

from src.models.base import ManyCustomResponse
from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.orm.sorters.url import UrlSortModel
from src.repositories.uow import UnitOfWork
from src.repositories.url import UrlRepository
from src.utils.exceptions.base import NotFound
from src.utils.types.type_variables import FilterModelT


class GetOneUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, filters: FilterModelT) -> UrlModel | None:
        async with self.uow as uow:
            session = uow.session

            response = await self.url_repository.get_one(
                filters=filters, async_session=session
            )
            if not response:
                logger.warning(f"Url not found for filters: {filters}")
                raise NotFound(message="Url not found")

            return response


class GetListUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(
        self, filters: UrlFilter, sorters: UrlSortModel
    ) -> ManyCustomResponse[UrlModel]:
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.get_list(
                filters=filters,
                async_session=session,
                sorters=sorters or UrlSortModel(),
            )


class GetAllUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, sorters: UrlSortModel) -> list[UrlModel]:
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.get_all(
                async_session=session,
                filters=UrlFilter(),
                sorters=sorters or UrlSortModel(),
            )


class CreateUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, target_url: str) -> UrlModel:
        async with self.uow as uow:
            session = uow.session

            while True:
                short_code = self.url_repository.get_short_code()
                search_response = await self.url_repository.get_one(
                    filters=UrlFilter(short_code=short_code), async_session=session
                )

                if not search_response:
                    break

            model_to_create = UrlModel(
                target_url=target_url,
                short_code=self.url_repository.get_short_code(),
            )

            return await self.url_repository.create(
                model=model_to_create, async_session=session
            )


class CreateListUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, target_urls: list[str]) -> int:
        async with self.uow as uow:
            session = uow.session

            models_to_create = [
                UrlModel(
                    target_url=url,
                    short_code=self.url_repository.get_short_code(),
                )
                for url in target_urls
            ]

            return await self.url_repository.create_list(
                models=models_to_create, async_session=session
            )


class UpdateUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, model: UrlModel) -> UrlModel:
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.update_one(
                model=model, async_session=session
            )


class UpdateListUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, models: list[UrlModel]) -> int:
        async with self.uow as uow:
            session = uow.session

            return await self.url_repository.update_list(
                models=models, async_session=session
            )


class MarkAsDeletedUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, short_code: str) -> UrlModel | None:
        async with self.uow as uow:
            session = uow.session

            filters = UrlFilter(short_code=short_code, deleted_at__is_null=True)
            model = await self.url_repository.get_one(
                filters=filters, async_session=session
            )
            if not model:
                return None

            model.deleted_at = datetime.now(UTC).replace(tzinfo=None)
            return await self.url_repository.update_one(
                model=model, async_session=session
            )


class MarkAsActiveUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, short_code: str) -> UrlModel | None:
        async with self.uow as uow:
            session = uow.session

            filters = UrlFilter(short_code=short_code, deleted_at__is_not_null=True)
            model = await self.url_repository.get_one(
                filters=filters, async_session=session
            )
            if not model:
                return None

            model.deleted_at = None
            return await self.url_repository.update_one(
                model=model, async_session=session
            )


class DeleteUrlHandler:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def handle(self, short_code: str) -> int:
        async with self.uow as uow:
            session = uow.session

            filters = UrlFilter(short_code=short_code)
            model = await self.url_repository.get_one(
                filters=filters, async_session=session
            )
            if not model:
                raise NotFound(message="Url not found")

            return await self.url_repository.delete_one(
                model=model, async_session=session
            )
