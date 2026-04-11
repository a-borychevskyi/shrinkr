from src.orm.filters.url_stats import UrlStatsFilter
from src.orm.models import UrlStats
from src.orm.sorters.url_stats import UrlStatsSortModel
from src.models.url_stats.entity import UrlStatsModel
from src.repositories.base import BaseDatabaseRepository


class UrlStatsRepository(
    BaseDatabaseRepository[UrlStats, UrlStatsFilter, UrlStatsSortModel, UrlStatsModel]
):
    __model__ = UrlStats
