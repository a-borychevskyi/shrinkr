from datetime import datetime, UTC
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.url_stats.entity import UrlStatsModel
from src.orm.filters.url import UrlFilter
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.services.database.url_stats import UrlStatsService
from src.utils.exceptions.base import NotFound


SAMPLE_URL_ORM = MagicMock()
SAMPLE_URL_ORM.id = 1
SAMPLE_URL_ORM.target_url = "https://example.com"
SAMPLE_URL_ORM.short_code = "abc123"

SAMPLE_STATS_ORM = MagicMock()
SAMPLE_STATS_ORM.id = 1
SAMPLE_STATS_ORM.url_id = 1
SAMPLE_STATS_ORM.user_agent = "Mozilla/5.0"
SAMPLE_STATS_ORM.ip_address = "127.0.0.1"
SAMPLE_STATS_ORM.access_time = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)

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


def _make_service(stats_repo=None, url_repo=None, uow=None):
    return UrlStatsService(
        url_stats_repository=stats_repo or _make_repo(),
        url_repository=url_repo or _make_repo(),
        uow=uow or _make_uow(),
    )


class TestGetOne:
    async def test_returns_stats_when_found(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=SAMPLE_URL_ORM)
        stats_repo = _make_repo()
        stats_repo.get_one = AsyncMock(return_value=SAMPLE_STATS_ORM)

        svc = _make_service(stats_repo=stats_repo, url_repo=url_repo)
        result = await svc.get_one(UrlFilter(short_code="abc123"))

        assert result.url_id == 1
        assert result.user_agent == "Mozilla/5.0"

    async def test_raises_not_found_when_url_missing(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=None)
        stats_repo = _make_repo()

        svc = _make_service(stats_repo=stats_repo, url_repo=url_repo)

        with pytest.raises(NotFound, match="Url not found"):
            await svc.get_one(UrlFilter(short_code="nonexistent"))

    async def test_raises_not_found_when_stats_missing(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=SAMPLE_URL_ORM)
        stats_repo = _make_repo()
        stats_repo.get_one = AsyncMock(return_value=None)

        svc = _make_service(stats_repo=stats_repo, url_repo=url_repo)

        with pytest.raises(NotFound, match="UrlStats not found"):
            await svc.get_one(UrlFilter(short_code="abc123"))


class TestGetList:
    async def test_returns_stats_list(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=SAMPLE_URL_ORM)
        stats_repo = _make_repo()
        stats_repo.get_list = AsyncMock(return_value=(1, [SAMPLE_STATS_ORM]))

        svc = _make_service(stats_repo=stats_repo, url_repo=url_repo)
        result = await svc.get_list(
            UrlFilter(short_code="abc123"),
            sorters=UrlStatsSortModel(),
        )

        assert result.count == 1
        assert len(result.data) == 1

    async def test_raises_not_found_when_url_missing(self):
        url_repo = _make_repo()
        url_repo.get_one = AsyncMock(return_value=None)
        stats_repo = _make_repo()

        svc = _make_service(stats_repo=stats_repo, url_repo=url_repo)

        with pytest.raises(NotFound, match="Url not found"):
            await svc.get_list(
                UrlFilter(short_code="nonexistent"),
                sorters=UrlStatsSortModel(),
            )


class TestGetAll:
    async def test_returns_all_stats(self):
        stats_repo = _make_repo()
        stats_repo.get_all = AsyncMock(return_value=[SAMPLE_STATS_ORM])

        svc = _make_service(stats_repo=stats_repo)
        result = await svc.get_all(sorters=UrlStatsSortModel())

        assert len(result) == 1
        assert result[0].url_id == 1

    async def test_returns_empty_list(self):
        stats_repo = _make_repo()
        stats_repo.get_all = AsyncMock(return_value=[])

        svc = _make_service(stats_repo=stats_repo)
        result = await svc.get_all(sorters=None)

        assert result == []


class TestCreateMany:
    async def test_creates_multiple_stats(self):
        stats_repo = _make_repo()
        stats_repo.create_many = AsyncMock(return_value=2)

        svc = _make_service(stats_repo=stats_repo)
        result = await svc.create_many([SAMPLE_STATS, SAMPLE_STATS])

        assert result == 2
        stats_repo.create_many.assert_awaited_once()


class TestUpdate:
    async def test_updates_stats(self):
        stats_repo = _make_repo()
        stats_repo.update = AsyncMock(return_value=SAMPLE_STATS_ORM)

        svc = _make_service(stats_repo=stats_repo)
        result = await svc.update(SAMPLE_STATS)

        assert result.url_id == 1
        stats_repo.update.assert_awaited_once()


class TestUpdateMany:
    async def test_updates_multiple_stats(self):
        stats_repo = _make_repo()
        stats_repo.update_many = AsyncMock(return_value=2)

        svc = _make_service(stats_repo=stats_repo)
        result = await svc.update_many([SAMPLE_STATS, SAMPLE_STATS])

        assert result == 2


class TestDelete:
    async def test_deletes_stats(self):
        stats_repo = _make_repo()
        stats_repo.delete = AsyncMock(return_value=1)

        svc = _make_service(stats_repo=stats_repo)
        result = await svc.delete(SAMPLE_STATS)

        assert result == 1
        stats_repo.delete.assert_awaited_once()
