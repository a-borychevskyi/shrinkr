from typing import Any, Callable

from sqlalchemy import Select

from src.models.base import BaseEntityModel


class BaseFilterModel(BaseEntityModel):
    """Base class for filter models"""

    def generate_filtered_query(self, expression: Select) -> Select:
        """
        Generates filter query based on expression and set model values.

        Example:
        >>> model = BaseFilterModel(name='User', min_age=18)
        >>> model.generate_filtered_query()
        >>> [{name: 'User', age: 19}, {name: 'User', age: 20}]
        """
        for field_set in self.model_fields_set:
            query: Query = self.model_fields[field_set].metadata[0]
            expression = query(expression=expression, value=getattr(self, field_set))

        return expression


class Query:
    modify_by: Callable[[Select, Any], Select] | None = None
    filter_by: Callable[[Any], Select] | None = None

    def __init__(
        self,
        modify_by: Callable[[Select, Any], Select] | None = None,
        filter_by: Callable[[Any], Select] | None = None,
    ):
        self.modify_by = modify_by
        self.filter_by = filter_by

    def __call__(self, expression: Select, value: Any) -> Select:
        if self.modify_by:
            expression = self.modify_by(expression, value)

        if self.filter_by:
            expression = expression.filter(self.filter_by(value))  # type: ignore[arg-type]

        return expression
