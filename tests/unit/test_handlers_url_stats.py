from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.handlers.orm.url_stats import (
    CreateListUrlStatsHandler,
    CreateUrlStatsHandler,
    DeleteUrlStatsHandler,
    GetAllUrlStatsHandler,
    GetListUrlStatsHandler,
    GetOneUrlStatsHandler,
    UpdateListUrlStatsHandler,
    UpdateUrlStatsHandler,
)
from src.models.base import ManyCustomResponse
from src.models.url.entity import UrlModel
from src.models.url_stats.entity import UrlStatsModel
from src.orm.filters.url import UrlFilter
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.utils.exceptions.base import NotFound


SAMPLE_URL = UrlModel(
    id=1,
    target_url="https://example.com",
    short_code="abc123",
    created_at=datetime(2026, 1, 1, tzinfo=UTC),
    updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    deleted_at=None,
)

SAMPLE_STATS = UrlStatsModel(
    id=1,
    url_id=1,
    user_agent="Mozilla/5.0",
    ip_address="127.0.0.1",
    access_time=datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC),
)


def _make_uow():
    uow = AsyncMock()
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=False)
    uow.session = AsyncMock()
    return uow


def _make_repo():
    return MagicMock()


class TestGetOneUrlStatsHandler:
    async def test_returns_stats_when_found(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=SAMPLE_URL)
        stats_repo = _make_repo()
        stats_repo.get_one = AsyncMock(return_value=SAMPLE_STATS)
        uow = _make_uow()

        handler = GetOneUrlStatsHandler(
            url_stats_repository=stats_repo,
            url_repository=url_repo,
            uow=uow,
        )
        result = await handler.handle(UrlFilter(short_code="abc123"))

        assert result == SAMPLE_STATS

    async def test_raises_not_found_when_url_missing(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=None)
        stats_repo = _make_repo()
        uow = _make_uow()

        handler = GetOneUrlStatsHandler(
            url_stats_repository=stats_repo,
            url_repository=url_repo,
            uow=uow,
        )

        with pytest.raises(NotFound, match="Url not found"):
            await handler.handle(UrlFilter(short_code="nonexistent"))


class TestGetListUrlStatsHandler:
    async def test_returns_stats_list(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=SAMPLE_URL)
        stats_repo = _make_repo()
        expected = ManyCustomResponse(total_count=1, data=[SAMPLE_STATS])
        stats_repo.get_list = AsyncMock(return_value=expected)
        uow = _make_uow()

        handler = GetListUrlStatsHandler(
            url_stats_repository=stats_repo,
            url_repository=url_repo,
            uow=uow,
        )
        result = await handler.handle(
            UrlFilter(short_code="abc123"),
            sorters=UrlStatsSortModel(access_time="ASC"),
        )

        assert result.count == 1
        assert len(result.data) == 1

    async def test_raises_not_found_when_url_missing(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=None)
        stats_repo = _make_repo()
        uow = _make_uow()

        handler = GetListUrlStatsHandler(
            url_stats_repository=stats_repo,
            url_repository=url_repo,
            uow=uow,
        )

        with pytest.raises(NotFound, match="Url not found"):
            await handler.handle(
                UrlFilter(short_code="nonexistent"),
                sorters=UrlStatsSortModel(),
            )


class TestCreateUrlStatsHandler:
    async def test_creates_stats_record(self):
        stats_repo = _make_repo()
        stats_repo.create = AsyncMock(return_value=SAMPLE_STATS)
        uow = _make_uow()

        handler = CreateUrlStatsHandler(url_stats_repository=stats_repo, uow=uow)
        result = await handler.handle(
            url_id=1,
            user_agent="Mozilla/5.0",
            ip_address="127.0.0.1",
        )

        assert result == SAMPLE_STATS
        stats_repo.create.assert_awaited_once()


class TestGetAllUrlStatsHandler:
    async def test_returns_all_stats(self):
        stats_repo = _make_repo()
        stats_repo.get_all = AsyncMock(return_value=[SAMPLE_STATS])
        uow = _make_uow()

        handler = GetAllUrlStatsHandler(url_stats_repository=stats_repo, uow=uow)
        result = await handler.handle(sorters=UrlStatsSortModel())

        assert len(result) == 1
        assert result[0] == SAMPLE_STATS

    async def test_returns_empty_list(self):
        stats_repo = _make_repo()
        stats_repo.get_all = AsyncMock(return_value=[])
        uow = _make_uow()

        handler = GetAllUrlStatsHandler(url_stats_repository=stats_repo, uow=uow)
        result = await handler.handle(sorters=None)

        assert result == []


class TestCreateListUrlStatsHandler:
    async def test_creates_multiple_stats(self):
        stats_repo = _make_repo()
        stats_repo.create_list = AsyncMock(return_value=2)
        uow = _make_uow()

        models = [SAMPLE_STATS, SAMPLE_STATS]
        handler = CreateListUrlStatsHandler(url_stats_repository=stats_repo, uow=uow)
        result = await handler.handle(models)

        assert result == 2
        stats_repo.create_list.assert_awaited_once()


class TestUpdateUrlStatsHandler:
    async def test_updates_stats(self):
        stats_repo = _make_repo()
        stats_repo.update_one = AsyncMock(return_value=SAMPLE_STATS)
        uow = _make_uow()

        handler = UpdateUrlStatsHandler(url_stats_repository=stats_repo, uow=uow)
        result = await handler.handle(SAMPLE_STATS)

        assert result == SAMPLE_STATS
        stats_repo.update_one.assert_awaited_once()


class TestUpdateListUrlStatsHandler:
    async def test_updates_multiple_stats(self):
        stats_repo = _make_repo()
        stats_repo.update_list = AsyncMock(return_value=2)
        uow = _make_uow()

        handler = UpdateListUrlStatsHandler(url_stats_repository=stats_repo, uow=uow)
        result = await handler.handle([SAMPLE_STATS, SAMPLE_STATS])

        assert result == 2


class TestDeleteUrlStatsHandler:
    async def test_deletes_stats(self):
        stats_repo = _make_repo()
        stats_repo.delete_one = AsyncMock(return_value=1)
        uow = _make_uow()

        handler = DeleteUrlStatsHandler(url_stats_repository=stats_repo, uow=uow)
        result = await handler.handle(SAMPLE_STATS)

        assert result == 1
        stats_repo.delete_one.assert_awaited_once()
