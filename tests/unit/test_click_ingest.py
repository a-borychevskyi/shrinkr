"""Unit tests for the batched click ingester."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.click_ingest import ClickEvent, ClickIngester


def _make_engine_with_captured_batches() -> tuple[MagicMock, list[list[dict]]]:
    """Return a fake AsyncEngine and a list that captures each flushed batch."""
    captured: list[list[dict]] = []

    conn = AsyncMock()

    async def _execute(_stmt, rows):
        captured.append(list(rows))

    conn.execute.side_effect = _execute

    transaction = AsyncMock()
    transaction.__aenter__.return_value = conn
    transaction.__aexit__.return_value = None

    engine = MagicMock()
    engine.begin.return_value = transaction
    return engine, captured


class TestClickIngester:
    async def test_enqueue_and_flush_writes_rows(self):
        engine, captured = _make_engine_with_captured_batches()
        ingester = ClickIngester(engine=engine, batch_size=3, flush_interval=0.05)

        await ingester.start()
        try:
            for i in range(3):
                ingester.enqueue(
                    ClickEvent(url_id=i, user_agent="ua", ip_address="1.2.3.4")
                )
            # Give the consumer a chance to collect and flush.
            await asyncio.sleep(0.2)
        finally:
            await ingester.stop()

        assert captured, "expected at least one flush"
        flushed = [row for batch in captured for row in batch]
        assert len(flushed) == 3
        assert {row["url_id"] for row in flushed} == {0, 1, 2}

    async def test_queue_full_drops_events(self):
        engine, _ = _make_engine_with_captured_batches()
        ingester = ClickIngester(engine=engine, max_queue_size=2)

        # Do not start the consumer so the queue fills up instantly.
        ingester.enqueue(ClickEvent(url_id=1, user_agent="u", ip_address="ip"))
        ingester.enqueue(ClickEvent(url_id=2, user_agent="u", ip_address="ip"))
        # This third enqueue should be dropped without raising.
        ingester.enqueue(ClickEvent(url_id=3, user_agent="u", ip_address="ip"))

        assert ingester._queue.qsize() == 2  # noqa: SLF001

    async def test_stop_drains_remaining_events(self):
        engine, captured = _make_engine_with_captured_batches()
        ingester = ClickIngester(engine=engine, batch_size=100, flush_interval=1.0)

        await ingester.start()
        ingester.enqueue(ClickEvent(url_id=42, user_agent="u", ip_address="ip"))
        # Stop immediately — shouldn't wait for flush_interval, should drain.
        await ingester.stop()

        flushed = [row for batch in captured for row in batch]
        assert any(row["url_id"] == 42 for row in flushed)


@pytest.mark.asyncio
async def test_start_is_idempotent():
    engine = MagicMock()
    ingester = ClickIngester(engine=engine)
    await ingester.start()
    first_task = ingester._task  # noqa: SLF001
    await ingester.start()
    assert ingester._task is first_task  # noqa: SLF001
    await ingester.stop()
