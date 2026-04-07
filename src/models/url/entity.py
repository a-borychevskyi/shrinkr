from datetime import datetime
from typing import Annotated

from pydantic import Field

from src.models.base import PydanticOrmModel


class UrlModel(PydanticOrmModel):
    id: Annotated[int | None, Field()]
    target_url: Annotated[str, Field()]
    short_code: Annotated[str, Field()]
    created_at: Annotated[datetime | None, Field()]
    updated_at: Annotated[datetime | None, Field()]
    deleted_at: Annotated[datetime | None, Field(default=None)]

    def to_orm(self):
        return self.model_dump(exclude_unset=True)
