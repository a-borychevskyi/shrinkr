from asyncio import current_task

from sqlalchemy.ext.asyncio import (
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)

from src.config.database import DatabaseConfig


class Database:
    def __init__(self, config: DatabaseConfig):
        self.async_engine = create_async_engine(
            url=config.DB_URL, pool_pre_ping=True, pool_size=30, max_overflow=0
        )
        self.session_factory = async_scoped_session(
            async_sessionmaker(
                self.async_engine,
                expire_on_commit=False,
                autoflush=False,
            ),
            scopefunc=current_task,
        )

    def stop(self):
        self.async_engine.dispose()
