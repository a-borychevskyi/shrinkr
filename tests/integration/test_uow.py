import pytest

from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.repositories.uow import UnitOfWork
from src.repositories.url import UrlRepository
from src.utils.exceptions.database import DatabaseError


@pytest.fixture
def url_repo() -> UrlRepository:
    return UrlRepository()


async def test_uow_commits_on_success(
    uow: UnitOfWork, url_repo: UrlRepository, session_factory
):
    async with uow:
        model = UrlModel(target_url="https://commit-test.com", short_code="uow1")
        await url_repo.create(async_session=uow.session, model=model)

    verify_uow = UnitOfWork(session_factory=session_factory)
    async with verify_uow:
        result = await url_repo.get_one(
            async_session=verify_uow.session,
            filters=UrlFilter(short_code="uow1"),
        )
        assert result is not None
        assert result.target_url == "https://commit-test.com"

    # Cleanup
    async with UnitOfWork(session_factory=session_factory) as cleanup_uow:
        from src.orm.models import Url

        await url_repo.delete(
            Url.short_code == "uow1", async_session=cleanup_uow.session
        )


async def test_uow_rolls_back_on_exception(session_factory, url_repo: UrlRepository):
    with pytest.raises(ValueError, match="intentional"):
        async with UnitOfWork(session_factory=session_factory) as uow:
            model = UrlModel(target_url="https://rollback-test.com", short_code="uow2")
            await url_repo.create(async_session=uow.session, model=model)
            raise ValueError("intentional")

    verify_uow = UnitOfWork(session_factory=session_factory)
    async with verify_uow:
        result = await url_repo.get_one(
            async_session=verify_uow.session,
            filters=UrlFilter(short_code="uow2"),
        )
        assert result is None


async def test_uow_session_not_opened_raises():
    from unittest.mock import MagicMock

    from sqlalchemy.ext.asyncio import async_sessionmaker

    uow = UnitOfWork(session_factory=MagicMock(spec=async_sessionmaker))
    with pytest.raises(DatabaseError, match="Session is not opened"):
        await uow.commit()
