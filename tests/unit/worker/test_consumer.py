import asyncio
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
    async def test_flush_inserts_via_repository(self):
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
        # commit is now done by _submit_flush on the poll thread, not here.
        consumer.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_submit_flush_commits_after_successful_insert(self):
        consumer = MagicMock()
        repo = MagicMock()
        repo.insert_many = AsyncMock()
        click_consumer = ClickConsumer(
            consumer=consumer,
            repository=repo,
            batch_size=2,
            flush_interval_seconds=10.0,
            flush_timeout_seconds=5.0,
        )

        loop = asyncio.get_running_loop()
        events = [_make_event(1)]

        # _submit_flush is sync but bridges to the async loop via run_coroutine_threadsafe.
        # Call it from a thread so the asyncio loop can process the bridged coroutine.
        await asyncio.to_thread(click_consumer._submit_flush, loop, events)

        repo.insert_many.assert_awaited_once_with(events)
        consumer.commit.assert_called_once_with(asynchronous=False)

    @pytest.mark.asyncio
    async def test_submit_flush_does_not_commit_on_insert_failure(self):
        consumer = MagicMock()
        repo = MagicMock()
        repo.insert_many = AsyncMock(side_effect=RuntimeError("db down"))
        click_consumer = ClickConsumer(
            consumer=consumer,
            repository=repo,
            batch_size=2,
            flush_interval_seconds=10.0,
            flush_timeout_seconds=5.0,
        )

        loop = asyncio.get_running_loop()
        events = [_make_event(1)]

        # _submit_flush catches and logs internally; should not raise.
        await asyncio.to_thread(click_consumer._submit_flush, loop, events)

        repo.insert_many.assert_awaited_once_with(events)
        consumer.commit.assert_not_called()

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


class TestLagGaugeGating:
    """Lag gauge refreshes involve blocking broker RPCs (committed/
    get_watermark_offsets) per partition. Under load these add up — they
    fired on every flush previously. We rate-limit them to avoid burning
    consumer throughput on metric upkeep.
    """

    def _build(self, interval: float):
        consumer = MagicMock()
        consumer.assignment.return_value = []  # no partitions → cheap no-op body
        repo = MagicMock()
        c = ClickConsumer(
            consumer=consumer,
            repository=repo,
            batch_size=2,
            flush_interval_seconds=10.0,
            lag_gauge_min_interval_seconds=interval,
        )
        return c, consumer

    def test_first_call_always_updates(self):
        c, consumer = self._build(interval=5.0)
        c._update_lag_gauge()
        consumer.assignment.assert_called_once()

    def test_second_call_within_interval_is_skipped(self):
        c, consumer = self._build(interval=5.0)
        c._update_lag_gauge()
        c._update_lag_gauge()
        # Still just the one call from the first update.
        assert consumer.assignment.call_count == 1

    def test_call_after_interval_elapses_updates_again(self):
        c, consumer = self._build(interval=5.0)
        c._update_lag_gauge()
        # Simulate 6 s passing by pushing the last-update timestamp back.
        c._last_lag_update_ts -= 6.0
        c._update_lag_gauge()
        assert consumer.assignment.call_count == 2

    def test_force_bypasses_gate(self):
        c, consumer = self._build(interval=60.0)
        c._update_lag_gauge()
        c._update_lag_gauge(force=True)
        assert consumer.assignment.call_count == 2
