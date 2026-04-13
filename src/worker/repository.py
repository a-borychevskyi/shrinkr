"""Bulk-insert helper used by the worker's flush loop.

Why not reuse a request-scoped repository? The worker has no requests
— just a poll loop on a thread bridging into asyncio. Reusing
UnitOfWork would require fabricating a session per flush and pulling
in the FastAPI request shape. A thin helper that takes the engine and
runs one multi-row INSERT is the smallest thing that works.
"""

from __future__ import annotations

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncEngine

from src.kafka.schema import ClickEvent
from src.orm.models import UrlStats


class UrlStatsBulkRepository:
    def __init__(self, engine: AsyncEngine) -> None:
        self._engine = engine

    async def insert_many(self, events: list[ClickEvent]) -> None:
        if not events:
            return
        rows = [
            {
                "url_id": event.url_id,
                "user_agent": event.user_agent,
                "ip_address": event.ip_address,
                # access_time uses server_default=now() on the column, so we
                # don't pass occurred_at — the schema's existing semantics
                # (server-side click time) are preserved.
            }
            for event in events
        ]
        async with self._engine.begin() as conn:
            await conn.execute(insert(UrlStats), rows)
