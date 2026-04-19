"""Wire schema for click events on the Kafka topic.

JSON over Kafka is sufficient for v1 — see the design spec for the
"future improvements" bullet on Avro/Schema Registry. We use orjson
because it's already a project dependency and is faster than the
stdlib json module.

Timestamps travel on the wire as ``occurred_at_ms`` — an integer number
of milliseconds since the Unix epoch — rather than an ISO-8601 string.
Profiling showed ``datetime.fromisoformat`` at ~10% of worker CPU;
integer parsing is ~free and orjson already serializes ints directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import orjson


@dataclass(slots=True, frozen=True)
class ClickEvent:
    url_id: int
    user_agent: str
    ip_address: str
    occurred_at: datetime

    def __post_init__(self) -> None:
        if self.occurred_at.tzinfo is None:
            raise ValueError("ClickEvent.occurred_at must be timezone-aware")


def encode_click_event(event: ClickEvent) -> bytes:
    """Serialize a ClickEvent to JSON bytes for Kafka produce()."""
    return orjson.dumps(
        {
            "url_id": event.url_id,
            "user_agent": event.user_agent,
            "ip_address": event.ip_address,
            "occurred_at_ms": int(event.occurred_at.timestamp() * 1000),
        }
    )


def decode_click_event(raw: bytes) -> ClickEvent:
    """Deserialize JSON bytes from Kafka into a ClickEvent.

    Raises ValueError on malformed JSON or missing required fields so
    the consumer can log + skip + commit (poison-message handling).
    """
    try:
        payload = orjson.loads(raw)
    except orjson.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc

    try:
        occurred_at_ms = payload["occurred_at_ms"]
        if not isinstance(occurred_at_ms, int) or isinstance(occurred_at_ms, bool):
            raise ValueError(
                f"occurred_at_ms must be int, got {type(occurred_at_ms).__name__}"
            )
        return ClickEvent(
            url_id=int(payload["url_id"]),
            user_agent=str(payload["user_agent"]),
            ip_address=str(payload["ip_address"]),
            occurred_at=datetime.fromtimestamp(occurred_at_ms / 1000, tz=timezone.utc),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"missing or invalid field: {exc}") from exc
