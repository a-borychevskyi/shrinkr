from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.kafka.schema import ClickEvent, encode_click_event
from src.worker.consumer import ClickConsumer


def _make_kafka_msg(event: ClickEvent | None, error=None, partition: int = 0):
    msg = MagicMock()
    msg.error.return_value = error
    msg.value.return_value = encode_click_event(event) if event else b"{}"
    msg.partition.return_value = partition
    return msg


def _make_event(url_id: int) -> ClickEvent:
    return ClickEvent(
        url_id=url_id,
        user_agent="ua",
        ip_address="1.2.3.4",
        occurred_at=datetime(2026, 4, 13, tzinfo=timezone.utc),
    )


class TestClickConsumer:
    @pytest.mark.asyncio
    async def test_flush_inserts_then_commits(self):
        consumer = MagicMock()
        repo = MagicMock()
        repo.insert_many = AsyncMock()
        click_consumer = ClickConsumer(
            consumer=consumer,
            repository=repo,
            batch_size=2,
            flush_interval_seconds=10.0,
        )

        events = [_make_event(1), _make_event(2)]
        await click_consumer._flush_batch(events)

        repo.insert_many.assert_awaited_once_with(events)
        consumer.commit.assert_called_once_with(asynchronous=False)

    @pytest.mark.asyncio
    async def test_insert_failure_does_not_commit(self):
        consumer = MagicMock()
        repo = MagicMock()
        repo.insert_many = AsyncMock(side_effect=RuntimeError("db down"))
        click_consumer = ClickConsumer(
            consumer=consumer,
            repository=repo,
            batch_size=2,
            flush_interval_seconds=10.0,
        )

        with pytest.raises(RuntimeError):
            await click_consumer._flush_batch([_make_event(1)])

        consumer.commit.assert_not_called()

    def test_decode_skips_poison_message(self):
        consumer = MagicMock()
        repo = MagicMock()
        click_consumer = ClickConsumer(
            consumer=consumer,
            repository=repo,
            batch_size=2,
            flush_interval_seconds=10.0,
        )
        bad_msg = MagicMock()
        bad_msg.error.return_value = None
        bad_msg.value.return_value = b"not json"
        bad_msg.partition.return_value = 0

        result = click_consumer._decode_or_skip(bad_msg)
        assert result is None
        consumer.commit.assert_called_once_with(message=bad_msg, asynchronous=False)
