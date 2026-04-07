from datetime import datetime
from typing import Annotated

from pydantic import Field

from src.models.base import PydanticOrmModel


class UrlStatsModel(PydanticOrmModel):
    id: Annotated[int | None, Field()] = None
    url_id: Annotated[int, Field()]
    user_agent: Annotated[str, Field()]
    ip_address: Annotated[str, Field()]
    access_time: Annotated[datetime | None, Field()] = None

    def to_orm(self):
        return self.model_dump(exclude_unset=True)
