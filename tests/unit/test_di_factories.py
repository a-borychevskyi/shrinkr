from unittest.mock import MagicMock

from src.di.handlers.url import (
    create_list_url_handler,
    get_all_url_handler,
    get_list_url_handler,
    mark_as_active_url_handler,
    mark_as_deleted_url_handler,
    update_list_url_handler,
    update_url_handler,
    delete_url_handler,
)
from src.di.handlers.url_stats import (
    get_one_url_stats_handler,
    get_all_url_stats_handler,
    create_url_stats_handler,
    create_list_url_stats_handler,
    update_url_stats_handler,
    update_list_url_stats_handler,
    delete_url_stats_handler,
)
from src.handlers.orm.url import (
    CreateListUrlHandler,
    DeleteUrlHandler,
    GetAllUrlHandler,
    GetListUrlHandler,
    MarkAsActiveUrlHandler,
    MarkAsDeletedUrlHandler,
    UpdateListUrlHandler,
    UpdateUrlHandler,
)
from src.handlers.orm.url_stats import (
    CreateListUrlStatsHandler,
    CreateUrlStatsHandler,
    DeleteUrlStatsHandler,
    GetAllUrlStatsHandler,
    GetOneUrlStatsHandler,
    UpdateListUrlStatsHandler,
    UpdateUrlStatsHandler,
)
from src.repositories.url import UrlRepository


class TestUrlDiFactories:
    def test_get_list_url_handler(self):
        uow = MagicMock()
        handler = get_list_url_handler(uow)
        assert isinstance(handler, GetListUrlHandler)

    def test_get_all_url_handler(self):
        uow = MagicMock()
        handler = get_all_url_handler(uow)
        assert isinstance(handler, GetAllUrlHandler)

    def test_create_list_url_handler(self):
        uow = MagicMock()
        handler = create_list_url_handler(uow)
        assert isinstance(handler, CreateListUrlHandler)

    def test_update_url_handler(self):
        uow = MagicMock()
        handler = update_url_handler(uow)
        assert isinstance(handler, UpdateUrlHandler)

    def test_update_list_url_handler(self):
        uow = MagicMock()
        handler = update_list_url_handler(uow)
        assert isinstance(handler, UpdateListUrlHandler)

    def test_mark_as_active_url_handler(self):
        uow = MagicMock()
        handler = mark_as_active_url_handler(uow)
        assert isinstance(handler, MarkAsActiveUrlHandler)

    def test_mark_as_deleted_url_handler(self):
        uow = MagicMock()
        handler = mark_as_deleted_url_handler(uow)
        assert isinstance(handler, MarkAsDeletedUrlHandler)

    def test_delete_url_handler(self):
        uow = MagicMock()
        handler = delete_url_handler(uow)
        assert isinstance(handler, DeleteUrlHandler)


class TestUrlStatsDiFactories:
    def test_get_one_url_stats_handler(self):
        uow = MagicMock()
        url_repo = UrlRepository()
        handler = get_one_url_stats_handler(uow, url_repo)
        assert isinstance(handler, GetOneUrlStatsHandler)

    def test_get_all_url_stats_handler(self):
        uow = MagicMock()
        handler = get_all_url_stats_handler(uow)
        assert isinstance(handler, GetAllUrlStatsHandler)

    def test_create_url_stats_handler(self):
        uow = MagicMock()
        handler = create_url_stats_handler(uow)
        assert isinstance(handler, CreateUrlStatsHandler)

    def test_create_list_url_stats_handler(self):
        uow = MagicMock()
        handler = create_list_url_stats_handler(uow)
        assert isinstance(handler, CreateListUrlStatsHandler)

    def test_update_url_stats_handler(self):
        uow = MagicMock()
        handler = update_url_stats_handler(uow)
        assert isinstance(handler, UpdateUrlStatsHandler)

    def test_update_list_url_stats_handler(self):
        uow = MagicMock()
        handler = update_list_url_stats_handler(uow)
        assert isinstance(handler, UpdateListUrlStatsHandler)

    def test_delete_url_stats_handler(self):
        uow = MagicMock()
        handler = delete_url_stats_handler(uow)
        assert isinstance(handler, DeleteUrlStatsHandler)
