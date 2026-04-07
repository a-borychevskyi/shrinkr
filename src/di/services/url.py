from typing import Annotated

from fastapi import Depends

from src.di.orm.database import get_uow
from src.di.repositories.url import get_url_repository
from src.repositories.uow import UnitOfWork
from src.services.database.url import UrlService


def get_url_service(uow: Annotated[UnitOfWork, Depends(get_uow)]) -> UrlService:
    return UrlService(url_repository=get_url_repository(), uow=uow)
