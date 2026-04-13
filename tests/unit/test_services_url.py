from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.orm.sorters.url import UrlSortModel
from src.services.database.url import UrlService
from src.utils.exceptions.base import NotFound, ServiceUnavailable


SAMPLE_ORM = MagicMock()
SAMPLE_ORM.id = 1
SAMPLE_ORM.target_url = "https://example.com"
SAMPLE_ORM.short_code = "abc123"
SAMPLE_ORM.created_at = datetime(2026, 1, 1, tzinfo=UTC)
SAMPLE_ORM.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
SAMPLE_ORM.deleted_at = None

SAMPLE_URL = UrlModel(
    id=1,
    target_url="https://example.com",
    short_code="abc123",
    created_at=datetime(2026, 1, 1, tzinfo=UTC),
    updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    deleted_at=None,
)


def _make_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    session = MagicMock()
    savepoint_cm = AsyncMock()
    savepoint_cm.__aenter__ = AsyncMock(return_value=savepoint_cm)
    savepoint_cm.__aexit__ = AsyncMock(return_value=False)
    session.begin_nested = MagicMock(return_value=savepoint_cm)
    uow.session = session
    return uow


def _make_repo():
    return MagicMock()


def _make_service(repo=None, uow=None):
    return UrlService(
        url_repository=repo or _make_repo(),
        uow=uow or _make_uow(),
    )


class TestGetOne:
    async def test_returns_model_when_found(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=SAMPLE_ORM)

        svc = _make_service(repo=repo)
        result = await svc.get_one(UrlFilter(short_code="abc123"))

        assert result.short_code == "abc123"
        assert result.target_url == "https://example.com"
        repo.get_one.assert_awaited_once()

    async def test_raises_not_found_when_missing(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=None)

        svc = _make_service(repo=repo)

        with pytest.raises(NotFound, match="Url not found"):
            await svc.get_one(UrlFilter(short_code="missing"))


class TestGetList:
    async def test_returns_paginated_list(self):
        repo = _make_repo()
        repo.get_list = AsyncMock(return_value=(1, [SAMPLE_ORM]))

        svc = _make_service(repo=repo)
        result = await svc.get_list(
            filters=UrlFilter(short_code="abc123"),
            sorters=UrlSortModel(),
        )

        assert result.count == 1
        assert len(result.data) == 1
        assert result.data[0].short_code == "abc123"

    async def test_uses_default_sorter_when_none(self):
        repo = _make_repo()
        repo.get_list = AsyncMock(return_value=(0, []))

        svc = _make_service(repo=repo)
        result = await svc.get_list(filters=UrlFilter(), sorters=None)

        assert result.count == 0


class TestGetAll:
    async def test_returns_all_urls(self):
        repo = _make_repo()
        repo.get_all = AsyncMock(return_value=[SAMPLE_ORM])

        svc = _make_service(repo=repo)
        result = await svc.get_all(sorters=UrlSortModel())

        assert len(result) == 1
        assert result[0].short_code == "abc123"

    async def test_returns_empty_list(self):
        repo = _make_repo()
        repo.get_all = AsyncMock(return_value=[])

        svc = _make_service(repo=repo)
        result = await svc.get_all(sorters=None)

        assert result == []


def _integrity_error() -> IntegrityError:
    return IntegrityError(
        statement="INSERT INTO urls ...",
        params={},
        orig=Exception("duplicate key value violates unique constraint"),
    )


class TestCreate:
    async def test_creates_url_when_code_is_unique(self):
        repo = _make_repo()
        repo.create = AsyncMock(return_value=SAMPLE_ORM)

        svc = _make_service(repo=repo)
        result = await svc.create("https://example.com")

        assert result.short_code == "abc123"
        repo.create.assert_awaited_once()

    async def test_retries_on_integrity_error_then_succeeds(self):
        """A unique-constraint collision on short_code should trigger a retry
        with a fresh code rather than propagating the error."""
        repo = _make_repo()
        repo.create = AsyncMock(
            side_effect=[_integrity_error(), _integrity_error(), SAMPLE_ORM]
        )

        svc = _make_service(repo=repo)
        result = await svc.create("https://example.com")

        assert result.short_code == "abc123"
        assert repo.create.await_count == 3

    async def test_raises_service_unavailable_on_exhaustion(self):
        """After the retry budget is exhausted the service must fail explicitly
        instead of looping forever."""
        repo = _make_repo()
        repo.create = AsyncMock(side_effect=_integrity_error())

        svc = _make_service(repo=repo)

        with pytest.raises(ServiceUnavailable):
            await svc.create("https://example.com")


class TestCreateMany:
    async def test_creates_multiple_urls(self):
        repo = _make_repo()
        repo.create_many = AsyncMock(return_value=2)

        svc = _make_service(repo=repo)
        result = await svc.create_many(["https://example.com", "https://example.org"])

        assert result == 2
        repo.create_many.assert_awaited_once()
        submitted_models = repo.create_many.await_args.kwargs["models"]
        codes = [m.short_code for m in submitted_models]
        assert len(codes) == len(set(codes))

    async def test_batch_retries_on_integrity_error(self):
        repo = _make_repo()
        repo.create_many = AsyncMock(side_effect=[_integrity_error(), 2])

        svc = _make_service(repo=repo)
        result = await svc.create_many(["https://a.com", "https://b.com"])

        assert result == 2
        assert repo.create_many.await_count == 2

    async def test_batch_raises_service_unavailable_on_exhaustion(self):
        repo = _make_repo()
        repo.create_many = AsyncMock(side_effect=_integrity_error())

        svc = _make_service(repo=repo)

        with pytest.raises(ServiceUnavailable):
            await svc.create_many(["https://a.com", "https://b.com"])


class TestUpdate:
    async def test_updates_url(self):
        repo = _make_repo()
        updated_orm = MagicMock()
        updated_orm.id = 1
        updated_orm.target_url = "https://new.com"
        updated_orm.short_code = "abc123"
        updated_orm.created_at = datetime(2026, 1, 1, tzinfo=UTC)
        updated_orm.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
        updated_orm.deleted_at = None
        repo.update = AsyncMock(return_value=updated_orm)

        svc = _make_service(repo=repo)
        model = SAMPLE_URL.model_copy(update={"target_url": "https://new.com"})
        result = await svc.update(model)

        assert result.target_url == "https://new.com"
        repo.update.assert_awaited_once()


class TestUpdateMany:
    async def test_updates_multiple_urls(self):
        repo = _make_repo()
        repo.update_many = AsyncMock(return_value=2)

        svc = _make_service(repo=repo)
        result = await svc.update_many([SAMPLE_URL, SAMPLE_URL])

        assert result == 2
        repo.update_many.assert_awaited_once()


class TestMarkAsDeleted:
    async def test_marks_url_as_deleted(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=SAMPLE_ORM)
        repo.update = AsyncMock(return_value=SAMPLE_ORM)

        svc = _make_service(repo=repo)
        result = await svc.mark_as_deleted("abc123")

        assert result is not None
        repo.update.assert_awaited_once()

    async def test_returns_none_when_not_found(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=None)

        svc = _make_service(repo=repo)
        result = await svc.mark_as_deleted("nonexistent")

        assert result is None


class TestMarkAsActive:
    async def test_marks_url_as_active(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=SAMPLE_ORM)
        repo.update = AsyncMock(return_value=SAMPLE_ORM)

        svc = _make_service(repo=repo)
        result = await svc.mark_as_active("abc123")

        assert result is not None
        repo.update.assert_awaited_once()

    async def test_returns_none_when_not_found(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=None)

        svc = _make_service(repo=repo)
        result = await svc.mark_as_active("nonexistent")

        assert result is None


class TestDelete:
    async def test_deletes_url(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=SAMPLE_ORM)
        repo.delete = AsyncMock(return_value=1)

        svc = _make_service(repo=repo)
        result = await svc.delete("abc123")

        assert result == 1
        repo.delete.assert_awaited_once()

    async def test_raises_not_found_when_missing(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=None)

        svc = _make_service(repo=repo)

        with pytest.raises(NotFound, match="Url not found"):
            await svc.delete("nonexistent")
