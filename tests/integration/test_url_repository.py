import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.url.entity import UrlModel
from src.orm.filters.url import UrlFilter
from src.orm.models import Url
from src.orm.sorters.url import UrlSortModel
from src.repositories.url import UrlRepository


async def test_create_and_get_one(async_session: AsyncSession, url_repo: UrlRepository):
    model = UrlModel(target_url="https://example.com", short_code="abc123")
    created = await url_repo.create(async_session=async_session, model=model)

    assert created is not None
    assert created.target_url == "https://example.com"
    assert created.short_code == "abc123"
    assert created.id is not None

    fetched = await url_repo.get_one(
        async_session=async_session,
        filters=UrlFilter(short_code="abc123"),
    )
    assert fetched is not None
    assert fetched.id == created.id


async def test_get_one_not_found(async_session: AsyncSession, url_repo: UrlRepository):
    result = await url_repo.get_one(
        async_session=async_session,
        filters=UrlFilter(short_code="nonexistent"),
    )
    assert result is None


async def test_get_list_with_pagination(
    async_session: AsyncSession, url_repo: UrlRepository
):
    for i in range(5):
        model = UrlModel(target_url=f"https://example.com/{i}", short_code=f"list{i}")
        await url_repo.create(async_session=async_session, model=model)

    count, data = await url_repo.get_list(
        async_session=async_session,
        filters=UrlFilter(),
        sorters=UrlSortModel(),
        page=1,
        per_page=3,
    )
    assert count >= 5
    assert len(data) == 3


async def test_get_list_with_filter(
    async_session: AsyncSession, url_repo: UrlRepository
):
    model = UrlModel(target_url="https://filtered.com", short_code="filtered1")
    await url_repo.create(async_session=async_session, model=model)

    count, data = await url_repo.get_list(
        async_session=async_session,
        filters=UrlFilter(target_url="https://filtered.com"),
        sorters=UrlSortModel(),
    )
    assert count >= 1
    assert all(row.target_url == "https://filtered.com" for row in data)


async def test_update(async_session: AsyncSession, url_repo: UrlRepository):
    model = UrlModel(target_url="https://original.com", short_code="upd1")
    created = await url_repo.create(async_session=async_session, model=model)

    updated_model = UrlModel.model_validate(created)
    updated_model.target_url = "https://updated.com"

    result = await url_repo.update(
        Url.id == created.id, async_session=async_session, model=updated_model
    )
    assert result is not None
    assert result.target_url == "https://updated.com"


async def test_delete(async_session: AsyncSession, url_repo: UrlRepository):
    model = UrlModel(target_url="https://delete-me.com", short_code="del1")
    created = await url_repo.create(async_session=async_session, model=model)

    deleted_count = await url_repo.delete(
        Url.id == created.id, async_session=async_session
    )
    assert deleted_count == 1

    fetched = await url_repo.get_one(
        async_session=async_session,
        filters=UrlFilter(short_code="del1"),
    )
    assert fetched is None


async def test_create_duplicate_short_code_raises(
    async_session: AsyncSession, url_repo: UrlRepository
):
    model1 = UrlModel(target_url="https://first.com", short_code="dup1")
    await url_repo.create(async_session=async_session, model=model1)
    await async_session.flush()

    model2 = UrlModel(target_url="https://second.com", short_code="dup1")
    with pytest.raises(IntegrityError):
        await url_repo.create(async_session=async_session, model=model2)


async def test_get_short_code_generates_unique_codes(url_repo: UrlRepository):
    codes = {url_repo.get_short_code() for _ in range(100)}
    assert len(codes) == 100
