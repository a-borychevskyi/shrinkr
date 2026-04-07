from unittest.mock import MagicMock

from src.di.services.url import get_url_service
from src.di.services.url_stats import get_url_stats_service
from src.services.database.url import UrlService
from src.services.database.url_stats import UrlStatsService


class TestUrlServiceFactory:
    def test_returns_url_service(self):
        uow = MagicMock()
        service = get_url_service(uow)
        assert isinstance(service, UrlService)


class TestUrlStatsServiceFactory:
    def test_returns_url_stats_service(self):
        uow = MagicMock()
        service = get_url_stats_service(uow)
        assert isinstance(service, UrlStatsService)
