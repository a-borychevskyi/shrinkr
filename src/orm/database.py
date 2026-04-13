from asyncio import current_task

from sqlalchemy.ext.asyncio import (
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from src.config.database import DatabaseConfig
from src.orm.metrics import register_query_metrics


class Database:
    def __init__(self, config: DatabaseConfig):
        self.async_engine = create_async_engine(
            url=config.DB_URL,
            pool_pre_ping=True,
            pool_size=config.DB_POOL_SIZE,
            max_overflow=config.DB_MAX_OVERFLOW,
        )
        register_query_metrics(self.async_engine.sync_engine)
        self.session_factory = async_scoped_session(
            async_sessionmaker(
                self.async_engine,
                expire_on_commit=False,
                autoflush=False,
            ),
            scopefunc=current_task,
        )

    async def stop(self):
        await self.async_engine.dispose()
