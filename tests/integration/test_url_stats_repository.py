from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.url.entity import UrlModel
from src.models.url_stats.entity import UrlStatsModel
from src.orm.filters.url_stats import UrlStatsFilter
from src.orm.models import Url
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.repositories.url import UrlRepository
from src.repositories.url_stats import UrlStatsRepository


async def _create_url(
    async_session: AsyncSession, url_repo: UrlRepository, short_code: str
) -> Any:
    model = UrlModel(target_url="https://example.com", short_code=short_code)
    return await url_repo.create(async_session=async_session, model=model)


async def test_create_and_get_stats(
    async_session: AsyncSession,
    url_repo: UrlRepository,
    stats_repo: UrlStatsRepository,
):
    url = await _create_url(async_session, url_repo, "stats1")

    stat = UrlStatsModel(
        url_id=url.id,
        user_agent="Mozilla/5.0",
        ip_address="192.168.1.1",
    )
    created = await stats_repo.create(async_session=async_session, model=stat)

    assert created is not None
    assert created.url_id == url.id
    assert created.user_agent == "Mozilla/5.0"
    assert created.ip_address == "192.168.1.1"
    assert created.access_time is not None


async def test_get_stats_list_by_url_id(
    async_session: AsyncSession,
    url_repo: UrlRepository,
    stats_repo: UrlStatsRepository,
):
    url = await _create_url(async_session, url_repo, "stats2")

    for i in range(3):
        stat = UrlStatsModel(
            url_id=url.id,
            user_agent=f"Agent-{i}",
            ip_address=f"10.0.0.{i}",
        )
        await stats_repo.create(async_session=async_session, model=stat)

    count, data = await stats_repo.get_list(
        async_session=async_session,
        filters=UrlStatsFilter(url_id=url.id),
        sorters=UrlStatsSortModel(),
    )
    assert count == 3
    assert len(data) == 3


async def test_cascade_delete_removes_stats(
    async_session: AsyncSession,
    url_repo: UrlRepository,
    stats_repo: UrlStatsRepository,
):
    url = await _create_url(async_session, url_repo, "cascade1")

    stat = UrlStatsModel(url_id=url.id, user_agent="Bot", ip_address="1.2.3.4")
    await stats_repo.create(async_session=async_session, model=stat)

    await url_repo.delete(Url.id == url.id, async_session=async_session)
    await async_session.flush()

    count, data = await stats_repo.get_list(
        async_session=async_session,
        filters=UrlStatsFilter(url_id=url.id),
        sorters=UrlStatsSortModel(),
    )
    assert count == 0


async def test_stats_filter_by_ip(
    async_session: AsyncSession,
    url_repo: UrlRepository,
    stats_repo: UrlStatsRepository,
):
    url = await _create_url(async_session, url_repo, "statsip1")

    for ip in ["10.0.0.1", "10.0.0.2", "10.0.0.1"]:
        stat = UrlStatsModel(url_id=url.id, user_agent="Agent", ip_address=ip)
        await stats_repo.create(async_session=async_session, model=stat)

    count, data = await stats_repo.get_list(
        async_session=async_session,
        filters=UrlStatsFilter(ip_address="10.0.0.1"),
        sorters=UrlStatsSortModel(),
    )
    assert count == 2
