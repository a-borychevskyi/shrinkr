from typing import Annotated

from fastapi import Depends

from src.di.orm.database import get_uow
from src.di.repositories.url import get_url_repository
from src.di.repositories.url_stats import get_url_stats_repository
from src.repositories.uow import UnitOfWork
from src.services.database.url_stats import UrlStatsService


def get_url_stats_service(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
) -> UrlStatsService:
    return UrlStatsService(
        url_stats_repository=get_url_stats_repository(),
        url_repository=get_url_repository(),
        uow=uow,
    )
