from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.utils.exceptions.database import DatabaseError


class UnitOfWork:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.__session_factory = session_factory
        self.session: AsyncSession | None = None

    def __get_session(self) -> AsyncSession:
        if isinstance(self.session, AsyncSession):
            return self.session

        raise DatabaseError("Session is not opened")

    async def commit(self):
        session = self.__get_session()

        await session.commit()

    async def rollback(self):
        session = self.__get_session()

        await session.rollback()

    async def close(self):
        session = self.__get_session()
        await session.close()

    async def __aenter__(self):
        try:
            self.session = self.__session_factory()
            await self.session.__aenter__()
            return self
        except Exception:
            if isinstance(self.session, AsyncSession) and self.session.is_active:
                await self.rollback()
                await self.close()
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            await self.commit()
        else:
            await self.rollback()

        await self.close()
