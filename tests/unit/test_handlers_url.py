from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.handlers.orm.url import (
    CreateListUrlHandler,
    CreateUrlHandler,
    DeleteUrlHandler,
    GetAllUrlHandler,
    GetListUrlHandler,
    GetOneUrlHandler,
    MarkAsActiveUrlHandler,
    MarkAsDeletedUrlHandler,
    UpdateListUrlHandler,
    UpdateUrlHandler,
)
from src.models.base import ManyCustomResponse
from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.orm.sorters.url import UrlSortModel
from src.utils.exceptions.base import NotFound


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
    session = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.session = session
    return uow


def _make_repo():
    return MagicMock()


class TestGetOneUrlHandler:
    async def test_returns_url_when_found(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=SAMPLE_URL)
        uow = _make_uow()

        handler = GetOneUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle(UrlFilter(short_code="abc123"))

        assert result == SAMPLE_URL
        repo.get_one.assert_awaited_once()

    async def test_raises_not_found_when_missing(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=None)
        uow = _make_uow()

        handler = GetOneUrlHandler(url_repository=repo, uow=uow)

        with pytest.raises(NotFound, match="Url not found"):
            await handler.handle(UrlFilter(short_code="missing"))


class TestCreateUrlHandler:
    async def test_creates_url_with_unique_code(self):
        repo = _make_repo()
        repo.get_short_code = MagicMock(return_value="newcode1")
        repo.get_one = AsyncMock(return_value=None)
        repo.create = AsyncMock(return_value=SAMPLE_URL)
        uow = _make_uow()

        handler = CreateUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle("https://example.com")

        assert result == SAMPLE_URL
        repo.create.assert_awaited_once()

    async def test_retries_on_duplicate_code(self):
        repo = _make_repo()
        # 3 calls in loop + 1 call when building the model
        repo.get_short_code = MagicMock(side_effect=["dup", "dup", "unique", "final"])
        repo.get_one = AsyncMock(side_effect=[SAMPLE_URL, SAMPLE_URL, None])
        repo.create = AsyncMock(return_value=SAMPLE_URL)
        uow = _make_uow()

        handler = CreateUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle("https://example.com")

        assert result == SAMPLE_URL
        assert repo.get_one.await_count == 3


class TestMarkAsDeletedUrlHandler:
    async def test_marks_url_as_deleted(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=SAMPLE_URL.model_copy())
        repo.update_one = AsyncMock(return_value=SAMPLE_URL)
        uow = _make_uow()

        handler = MarkAsDeletedUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle("abc123")

        assert result is not None
        repo.update_one.assert_awaited_once()
        updated_model = repo.update_one.call_args.kwargs["model"]
        assert updated_model.deleted_at is not None

    async def test_returns_none_when_not_found(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=None)
        uow = _make_uow()

        handler = MarkAsDeletedUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle("nonexistent")

        assert result is None


class TestMarkAsActiveUrlHandler:
    async def test_marks_url_as_active(self):
        deactivated_url = SAMPLE_URL.model_copy(
            update={"deleted_at": datetime(2026, 1, 2, tzinfo=UTC)}
        )
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=deactivated_url)
        repo.update_one = AsyncMock(return_value=SAMPLE_URL)
        uow = _make_uow()

        handler = MarkAsActiveUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle("abc123")

        assert result is not None
        repo.update_one.assert_awaited_once()
        updated_model = repo.update_one.call_args.kwargs["model"]
        assert updated_model.deleted_at is None

    async def test_returns_none_when_not_found(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=None)
        uow = _make_uow()

        handler = MarkAsActiveUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle("nonexistent")

        assert result is None


class TestDeleteUrlHandler:
    async def test_deletes_url(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=SAMPLE_URL)
        repo.delete_one = AsyncMock(return_value=1)
        uow = _make_uow()

        handler = DeleteUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle("abc123")

        assert result == 1
        repo.delete_one.assert_awaited_once()

    async def test_raises_not_found_when_missing(self):
        repo = _make_repo()
        repo.get_one = AsyncMock(return_value=None)
        uow = _make_uow()

        handler = DeleteUrlHandler(url_repository=repo, uow=uow)

        with pytest.raises(NotFound, match="Url not found"):
            await handler.handle("nonexistent")


class TestGetListUrlHandler:
    async def test_returns_paginated_list(self):
        repo = _make_repo()
        expected = ManyCustomResponse(total_count=1, data=[SAMPLE_URL])
        repo.get_list = AsyncMock(return_value=expected)
        uow = _make_uow()

        handler = GetListUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle(
            filters=UrlFilter(short_code="abc123"),
            sorters=UrlSortModel(),
        )

        assert result.count == 1
        assert len(result.data) == 1
        repo.get_list.assert_awaited_once()

    async def test_uses_default_sorter_when_none(self):
        repo = _make_repo()
        expected = ManyCustomResponse(total_count=0, data=[])
        repo.get_list = AsyncMock(return_value=expected)
        uow = _make_uow()

        handler = GetListUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle(filters=UrlFilter(), sorters=None)

        assert result.count == 0


class TestGetAllUrlHandler:
    async def test_returns_all_urls(self):
        repo = _make_repo()
        repo.get_all = AsyncMock(return_value=[SAMPLE_URL])
        uow = _make_uow()

        handler = GetAllUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle(sorters=UrlSortModel())

        assert len(result) == 1
        assert result[0] == SAMPLE_URL
        repo.get_all.assert_awaited_once()

    async def test_returns_empty_list(self):
        repo = _make_repo()
        repo.get_all = AsyncMock(return_value=[])
        uow = _make_uow()

        handler = GetAllUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle(sorters=None)

        assert result == []


class TestCreateListUrlHandler:
    async def test_creates_multiple_urls(self):
        repo = _make_repo()
        repo.get_short_code = MagicMock(side_effect=["code1", "code2"])
        repo.create_list = AsyncMock(return_value=2)
        uow = _make_uow()

        handler = CreateListUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle(["https://example.com", "https://example.org"])

        assert result == 2
        repo.create_list.assert_awaited_once()


class TestUpdateUrlHandler:
    async def test_updates_url(self):
        repo = _make_repo()
        updated = SAMPLE_URL.model_copy(update={"target_url": "https://new.com"})
        repo.update_one = AsyncMock(return_value=updated)
        uow = _make_uow()

        handler = UpdateUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle(updated)

        assert result.target_url == "https://new.com"
        repo.update_one.assert_awaited_once()


class TestUpdateListUrlHandler:
    async def test_updates_multiple_urls(self):
        repo = _make_repo()
        repo.update_list = AsyncMock(return_value=2)
        uow = _make_uow()

        handler = UpdateListUrlHandler(url_repository=repo, uow=uow)
        result = await handler.handle([SAMPLE_URL, SAMPLE_URL])

        assert result == 2
        repo.update_list.assert_awaited_once()
