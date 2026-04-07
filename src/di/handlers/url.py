from typing import Annotated

from fastapi import Depends

from src.di.orm.database import get_uow
from src.di.repositories.url import get_url_repository
from src.handlers.orm.url import (
    CreateListUrlHandler,
    CreateUrlHandler,
    DeleteUrlHandler,
    GetAllUrlHandler,
    GetListUrlHandler,
    GetOneUrlHandler,
    MarkAsDeletedUrlHandler,
    UpdateListUrlHandler,
    UpdateUrlHandler,
)
from src.repositories.uow import UnitOfWork


def get_one_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return GetOneUrlHandler(url_repository=url_repository, uow=uow)


def get_list_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return GetListUrlHandler(url_repository=url_repository, uow=uow)


def get_all_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return GetAllUrlHandler(url_repository=url_repository, uow=uow)


def create_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return CreateUrlHandler(url_repository=url_repository, uow=uow)


def create_list_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return CreateListUrlHandler(url_repository=url_repository, uow=uow)


def update_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return UpdateUrlHandler(url_repository=url_repository, uow=uow)


def update_list_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return UpdateListUrlHandler(url_repository=url_repository, uow=uow)


def mark_as_deleted_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return MarkAsDeletedUrlHandler(url_repository=url_repository, uow=uow)


def delete_url_handler(uow: Annotated[UnitOfWork, Depends(get_uow)]):
    url_repository = get_url_repository()
    return DeleteUrlHandler(url_repository=url_repository, uow=uow)
