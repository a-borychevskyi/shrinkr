from collections.abc import AsyncIterator

import pytest
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from src.orm.models.base import Base
from src.repositories.uow import UnitOfWork


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer(
        image="postgres:16-alpine",
        username="test",
        password="test",
        dbname="test_shrinkr",
        driver="asyncpg",
    ) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer(image="redis:7-alpine") as redis:
        yield redis


@pytest.fixture(scope="session")
def async_engine(postgres_container):
    url = postgres_container.get_connection_url()
    return create_async_engine(url, echo=False)


@pytest.fixture(scope="session", autouse=True)
async def create_tables(async_engine):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def async_session(async_engine) -> AsyncIterator[AsyncSession]:
    session_factory = async_sessionmaker(
        async_engine, expire_on_commit=False, autoflush=False
    )
    async with session_factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


@pytest.fixture
def session_factory(async_engine):
    return async_sessionmaker(async_engine, expire_on_commit=False, autoflush=False)


@pytest.fixture
def uow(session_factory) -> UnitOfWork:
    return UnitOfWork(session_factory=session_factory)


@pytest.fixture
async def redis_client(redis_container) -> AsyncIterator[Redis]:
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(6379)
    client = Redis(host=host, port=int(port), db=0, decode_responses=True)
    yield client
    await client.flushdb()
    await client.aclose()
