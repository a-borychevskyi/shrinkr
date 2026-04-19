import orjson
import pytest
from datetime import datetime, timezone

from src.kafka.schema import ClickEvent, decode_click_event, encode_click_event


class TestClickEventEncoding:
    def test_encode_round_trip(self):
        ts = datetime(2026, 4, 13, 10, 15, 30, 123_000, tzinfo=timezone.utc)
        event = ClickEvent(
            url_id=42,
            user_agent="Mozilla/5.0",
            ip_address="1.2.3.4",
            occurred_at=ts,
        )
        raw = encode_click_event(event)
        assert isinstance(raw, bytes)
        decoded = decode_click_event(raw)
        assert decoded == event

    def test_wire_format_uses_epoch_ms_int(self):
        """occurred_at_ms on the wire is a plain integer (epoch ms).

        ISO-8601 strings forced Python-level datetime.fromisoformat on the
        consumer and showed up at ~10% of worker CPU. An int skips
        parsing entirely.
        """
        ts = datetime(2026, 4, 13, 10, 15, 30, 123_000, tzinfo=timezone.utc)
        event = ClickEvent(url_id=1, user_agent="ua", ip_address="ip", occurred_at=ts)
        raw = encode_click_event(event)
        payload = orjson.loads(raw)
        assert "occurred_at_ms" in payload
        assert isinstance(payload["occurred_at_ms"], int)
        # 2026-04-13T10:15:30.123Z == 1_776_334_530_123 ms since epoch
        assert payload["occurred_at_ms"] == int(ts.timestamp() * 1000)
        # Legacy field must be gone — otherwise decode ambiguity between
        # old and new consumers.
        assert "occurred_at" not in payload

    def test_encode_is_stable(self):
        ts = datetime(2026, 4, 13, 10, 15, 30, 123_000, tzinfo=timezone.utc)
        event = ClickEvent(url_id=1, user_agent="ua", ip_address="ip", occurred_at=ts)
        raw = encode_click_event(event)
        again = encode_click_event(decode_click_event(raw))
        assert raw == again

    def test_decode_rejects_missing_fields(self):
        with pytest.raises(ValueError):
            decode_click_event(b'{"url_id": 1}')

    def test_decode_rejects_invalid_json(self):
        with pytest.raises(ValueError):
            decode_click_event(b"not json")

    def test_decode_rejects_non_int_timestamp(self):
        with pytest.raises(ValueError):
            decode_click_event(
                b'{"url_id": 1, "user_agent": "ua", "ip_address": "ip", "occurred_at_ms": "not-a-number"}'
            )

    def test_decode_preserves_utc(self):
        raw = (
            b'{"url_id": 1, "user_agent": "ua", "ip_address": "ip",'
            b' "occurred_at_ms": 1776075330123}'
        )
        event = decode_click_event(raw)
        assert event.occurred_at.tzinfo == timezone.utc
        assert event.occurred_at == datetime(
            2026, 4, 13, 10, 15, 30, 123_000, tzinfo=timezone.utc
        )

    def test_click_event_rejects_naive_datetime(self):
        from datetime import datetime as _dt

        with pytest.raises(ValueError, match="timezone-aware"):
            ClickEvent(
                url_id=1,
                user_agent="ua",
                ip_address="ip",
                occurred_at=_dt(2026, 4, 13, 10, 0, 0),  # naive
            )
