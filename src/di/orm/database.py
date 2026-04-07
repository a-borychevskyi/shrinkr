from fastapi import Request

from src.config.database import DatabaseConfig
from src.orm.database import Database
from src.repositories.uow import UnitOfWork


def get_db_config():
    return DatabaseConfig()


def get_db() -> Database:
    config = get_db_config()
    return Database(config=config)


def get_uow(request: Request):
    db = request.app.state.db
    return UnitOfWork(session_factory=db.session_factory)
