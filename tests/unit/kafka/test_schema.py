from datetime import datetime, timezone

import pytest

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

    def test_occurred_at_iso_format_with_z(self):
        ts = datetime(2026, 4, 13, 10, 15, 30, 123_000, tzinfo=timezone.utc)
        event = ClickEvent(url_id=1, user_agent="ua", ip_address="ip", occurred_at=ts)
        raw = encode_click_event(event)
        # Must be parseable both ways and stable.
        again = encode_click_event(decode_click_event(raw))
        assert raw == again

    def test_decode_rejects_missing_fields(self):
        with pytest.raises(ValueError):
            decode_click_event(b'{"url_id": 1}')

    def test_decode_rejects_invalid_json(self):
        with pytest.raises(ValueError):
            decode_click_event(b"not json")

    def test_decode_rejects_invalid_timestamp(self):
        with pytest.raises(ValueError):
            decode_click_event(
                b'{"url_id": 1, "user_agent": "ua", "ip_address": "ip", "occurred_at": "not-a-date"}'
            )

    def test_decode_naive_timestamp_defaults_to_utc(self):
        raw = b'{"url_id": 1, "user_agent": "ua", "ip_address": "ip", "occurred_at": "2026-04-13T10:15:30"}'
        event = decode_click_event(raw)
        assert event.occurred_at.tzinfo == timezone.utc
