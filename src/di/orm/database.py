from functools import lru_cache

from fastapi import Request

from src.config.database import DatabaseConfig
from src.orm.database import Database
from src.repositories.uow import UnitOfWork


@lru_cache(maxsize=1)
def get_db_config() -> DatabaseConfig:
    return DatabaseConfig()


@lru_cache(maxsize=1)
def get_db() -> Database:
    """Singleton :class:`Database` (engine + session factory).

    Cached so the engine + connection pool is created once per process.
    API lifespan calls this at startup; worker's ``_async_main`` does
    too. Without caching, two callers would create two independent
    pools.
    """
    return Database(config=get_db_config())


def get_uow(request: Request):
    db = request.app.state.db
    return UnitOfWork(session_factory=db.session_factory)
