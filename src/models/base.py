from abc import ABC, abstractmethod
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class BaseEntityModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class ManyCustomResponse[T](BaseEntityModel):
    count: Annotated[int | None, Field(default=0, alias="total_count")]
    data: Annotated[list[T], Field(default_factory=list)]


class PydanticOrmModel(BaseEntityModel, ABC):
    model_config = ConfigDict(from_attributes=True)

    @abstractmethod
    def to_orm(self):
        raise NotImplementedError
