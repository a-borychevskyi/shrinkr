from typing import Annotated

from fastapi import Depends

from di.repositories.url_stats import get_url_stats_repository
from handlers.orm.url_stats import (
    CreateListUrlStatsHandler,
    CreateUrlStatsHandler,
    DeleteUrlStatsHandler,
    GetAllUrlStatsHandler,
    GetListUrlStatsHandler,
    GetOneUrlStatsHandler,
    UpdateListUrlStatsHandler,
    UpdateUrlStatsHandler,
)
from src.di.orm.database import get_uow
from src.di.repositories.url import get_url_repository
from src.repositories.uow import UnitOfWork
from src.repositories.url import UrlRepository


def get_one_url_stats_handler(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    url_repository: Annotated[UrlRepository, Depends(get_url_repository)],
):
    url_stats_repository = get_url_stats_repository()
    return GetOneUrlStatsHandler(
        url_stats_repository=url_stats_repository,
        url_repository=url_repository,
        uow=uow,
    )


def get_list_url_stats_handler(
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    url_repository: Annotated[UrlRepository, Depends(get_url_repository)],
):
    url_stats_repository = get_url_stats_repository()
    return GetListUrlStatsHandler(
        url_stats_repository=url_stats_repository,
        url_repository=url_repository,
        uow=uow,
    )


def get_all_url_stats_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_stats_repository = get_url_stats_repository()
    return GetAllUrlStatsHandler(url_stats_repository=url_stats_repository, uow=uow)


def create_url_stats_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_stats_repository = get_url_stats_repository()
    return CreateUrlStatsHandler(url_stats_repository=url_stats_repository, uow=uow)


def create_list_url_stats_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_stats_repository = get_url_stats_repository()
    return CreateListUrlStatsHandler(url_stats_repository=url_stats_repository, uow=uow)


def update_url_stats_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_stats_repository = get_url_stats_repository()
    return UpdateUrlStatsHandler(url_stats_repository=url_stats_repository, uow=uow)


def update_list_url_stats_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_stats_repository = get_url_stats_repository()
    return UpdateListUrlStatsHandler(url_stats_repository=url_stats_repository, uow=uow)


def delete_url_stats_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_stats_repository = get_url_stats_repository()
    return DeleteUrlStatsHandler(url_stats_repository=url_stats_repository, uow=uow)
