from abc import ABC, abstractmethod
from typing import Annotated

from pydantic import BaseModel, Field


class BaseEntityModel(BaseModel):
    pass


class ManyCustomResponse[T](BaseEntityModel):
    count: Annotated[int | None, Field(default=0, alias="total_count")]
    data: Annotated[list[T], Field(default_factory=list)]


class PydanticOrmModel(BaseEntityModel, ABC):
    @abstractmethod
    def to_orm(self):
        raise NotImplementedError
