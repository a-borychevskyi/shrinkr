from datetime import UTC, datetime

from loguru import logger
from opentelemetry import trace

from src.models.base import ManyCustomResponse
from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.orm.models import Url
from src.orm.sorters.url import UrlSortModel
from src.repositories.uow import UnitOfWork
from src.repositories.url import UrlRepository
from src.utils.exceptions.base import NotFound

tracer = trace.get_tracer(__name__)


class UrlService:
    def __init__(self, url_repository: UrlRepository, uow: UnitOfWork):
        self.url_repository = url_repository
        self.uow = uow

    async def get_one(self, filters: UrlFilter) -> UrlModel:
        with tracer.start_as_current_span(
            "UrlService.get_one",
            attributes={"url.short_code": filters.short_code or ""},
        ):
            async with self.uow as uow:
                result = await self.url_repository.get_one(
                    filters=filters, async_session=uow.session
                )
                if not result:
                    logger.warning(f"Url not found for filters: {filters}")
                    raise NotFound(message="Url not found")
                return UrlModel.model_validate(result)

    async def get_list(
        self, filters: UrlFilter, sorters: UrlSortModel | None = None
    ) -> ManyCustomResponse[UrlModel]:
        with tracer.start_as_current_span("UrlService.get_list"):
            async with self.uow as uow:
                count, data = await self.url_repository.get_list(
                    filters=filters,
                    async_session=uow.session,
                    sorters=sorters or UrlSortModel(),
                )
                return ManyCustomResponse[UrlModel](
                    count=count,
                    data=[UrlModel.model_validate(row) for row in data],
                )

    async def get_all(self, sorters: UrlSortModel | None = None) -> list[UrlModel]:
        with tracer.start_as_current_span("UrlService.get_all"):
            async with self.uow as uow:
                results = await self.url_repository.get_all(
                    async_session=uow.session,
                    filters=UrlFilter(),
                    sorters=sorters or UrlSortModel(),
                )
                return [UrlModel.model_validate(row) for row in results]

    async def create(self, target_url: str) -> UrlModel:
        with tracer.start_as_current_span(
            "UrlService.create",
            attributes={"url.target_url": target_url},
        ) as span:
            async with self.uow as uow:
                attempts = 0
                while True:
                    attempts += 1
                    short_code = self.url_repository.get_short_code()
                    existing = await self.url_repository.get_one(
                        filters=UrlFilter(short_code=short_code),
                        async_session=uow.session,
                    )
                    if not existing:
                        break

                span.set_attribute("url.short_code", short_code)
                span.set_attribute("url.generation_attempts", attempts)

                model = UrlModel(target_url=target_url, short_code=short_code)
                result = await self.url_repository.create(
                    model=model, async_session=uow.session
                )
                return UrlModel.model_validate(result)

    async def create_many(self, target_urls: list[str]) -> int:
        with tracer.start_as_current_span(
            "UrlService.create_many",
            attributes={"url.batch_size": len(target_urls)},
        ):
            async with self.uow as uow:
                models = [
                    UrlModel(
                        target_url=url,
                        short_code=self.url_repository.get_short_code(),
                    )
                    for url in target_urls
                ]
                return await self.url_repository.create_many(
                    models=models, async_session=uow.session
                )

    async def update(self, model: UrlModel) -> UrlModel:
        with tracer.start_as_current_span("UrlService.update"):
            async with self.uow as uow:
                result = await self.url_repository.update(
                    Url.id == model.id, async_session=uow.session, model=model
                )
                return UrlModel.model_validate(result)

    async def update_many(self, models: list[UrlModel]) -> int:
        with tracer.start_as_current_span(
            "UrlService.update_many",
            attributes={"url.batch_size": len(models)},
        ):
            async with self.uow as uow:
                return await self.url_repository.update_many(
                    Url.id.in_([m.id for m in models]),
                    async_session=uow.session,
                    models=models,
                )

    async def mark_as_deleted(self, short_code: str) -> UrlModel | None:
        with tracer.start_as_current_span(
            "UrlService.mark_as_deleted",
            attributes={"url.short_code": short_code},
        ) as span:
            async with self.uow as uow:
                filters = UrlFilter(short_code=short_code, deleted_at__is_null=True)
                result = await self.url_repository.get_one(
                    filters=filters, async_session=uow.session
                )
                if not result:
                    span.set_attribute("url.found", False)
                    return None

                span.set_attribute("url.found", True)
                model = UrlModel.model_validate(result)
                model.deleted_at = datetime.now(UTC).replace(tzinfo=None)
                updated = await self.url_repository.update(
                    Url.id == model.id, async_session=uow.session, model=model
                )
                return UrlModel.model_validate(updated)

    async def mark_as_active(self, short_code: str) -> UrlModel | None:
        with tracer.start_as_current_span(
            "UrlService.mark_as_active",
            attributes={"url.short_code": short_code},
        ) as span:
            async with self.uow as uow:
                filters = UrlFilter(short_code=short_code, deleted_at__is_not_null=True)
                result = await self.url_repository.get_one(
                    filters=filters, async_session=uow.session
                )
                if not result:
                    span.set_attribute("url.found", False)
                    return None

                span.set_attribute("url.found", True)
                model = UrlModel.model_validate(result)
                model.deleted_at = None
                updated = await self.url_repository.update(
                    Url.id == model.id, async_session=uow.session, model=model
                )
                return UrlModel.model_validate(updated)

    async def delete(self, short_code: str) -> int:
        with tracer.start_as_current_span(
            "UrlService.delete",
            attributes={"url.short_code": short_code},
        ):
            async with self.uow as uow:
                filters = UrlFilter(short_code=short_code)
                result = await self.url_repository.get_one(
                    filters=filters, async_session=uow.session
                )
                if not result:
                    raise NotFound(message="Url not found")

                return await self.url_repository.delete(
                    Url.id == result.id, async_session=uow.session
                )
