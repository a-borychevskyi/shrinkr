from typing import Type

from loguru import logger
from sqlalchemy import TextClause, text

from src.models.base import BaseEntityModel
from src.utils.enums.sort import SortOption


class BaseSortModel(BaseEntityModel):
    """Base class for all-sorters models."""

    def validate_sort_option(self, name: str, value: str) -> bool:
        is_valid_field = name in self.model_fields
        is_valid_direction = value in SortOption.__members__.values()
        return is_valid_field and is_valid_direction

    def generate_params(self) -> list[TextClause]:
        """
        Generates SQL order clauses by set model fields.

        Example:
        >>> model = BaseSortModel(name='ASC', username='DESC')
        >>> model.generate_params()
        >>> ['name ASC', 'username DESC']
        """
        order_by = []

        for name, value in self.model_dump(exclude_unset=True).items():
            if not self.validate_sort_option(name, value):
                logger.warning(f"Invalid sort option: {name} {value}")
                continue

            order_by.append(text(f"{name} {value}"))

        return order_by


def sort_convertor[T: BaseSortModel](model: Type[T], sort_by: str) -> T:
    """
    Converts sorters field like '-name,username...' into model field format.

    Example:
    >>> sort_convertor(BaseSortModel, "-name,username")
    >>> BaseSortModel(name='DESC', username='ASC')
    """
    if not sort_by:
        return model()

    items = [item.strip() for item in sort_by.split(",")]

    sorting_fields = {}

    for field in items:
        if field.startswith("-"):
            sort_field, sort_direction = field[1:], SortOption.DESC
        else:
            sort_field, sort_direction = field, SortOption.ASC

        sorting_fields[sort_field] = sort_direction

    return model.model_validate(sorting_fields)
