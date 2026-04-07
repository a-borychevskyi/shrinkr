from datetime import datetime
from typing import Annotated

from pydantic import Field

from src.models.base import PydanticOrmModel


class UrlModel(PydanticOrmModel):
    id: Annotated[int | None, Field()] = None
    target_url: Annotated[str, Field()]
    short_code: Annotated[str, Field()]
    created_at: Annotated[datetime | None, Field()] = None
    updated_at: Annotated[datetime | None, Field()] = None
    deleted_at: Annotated[datetime | None, Field()] = None

    def to_orm(self):
        return self.model_dump(exclude_unset=True)
