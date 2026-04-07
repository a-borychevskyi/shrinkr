from datetime import datetime
from typing import Annotated

from pydantic import Field

from src.models.base import PydanticOrmModel
from src.orm.models.url_stats import UrlStats


class UrlStatsModel(PydanticOrmModel):
    id: Annotated[int, Field()]
    url_id: Annotated[int, Field()]
    user_agent: Annotated[str, Field()]
    ip_address: Annotated[str, Field()]
    redirect_elapsed_ms: Annotated[int, Field()]
    access_time: Annotated[datetime, Field()]

    def to_orm(self):
        return self.model_dump()
