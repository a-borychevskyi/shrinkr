from typing import TypeVar

from src.models.base import PydanticOrmModel
from src.orm.filters.base import BaseFilterModel
from src.orm.sorters.base import BaseSortModel

CreateModelT = TypeVar("CreateModelT", bound=PydanticOrmModel)
UpdateModelT = TypeVar("UpdateModelT", bound=PydanticOrmModel)

FilterModelT = TypeVar("FilterModelT", bound=BaseFilterModel)
SortModelT = TypeVar("SortModelT", bound=BaseSortModel)
