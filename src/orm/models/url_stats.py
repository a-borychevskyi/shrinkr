from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column

from src.orm.models.base import Base


class UrlStats(Base):
    __tablename__ = "url_stats"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    url_id: Mapped[int] = mapped_column(
        ForeignKey("urls.id", ondelete="CASCADE"), index=True
    )
    user_agent: Mapped[str] = mapped_column()
    ip_address: Mapped[str] = mapped_column()
    access_time: Mapped[datetime] = mapped_column(server_default=func.now())
