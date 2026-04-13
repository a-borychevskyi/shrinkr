"""Wire schema for click events on the Kafka topic.

JSON over Kafka is sufficient for v1 — see the design spec for the
"future improvements" bullet on Avro/Schema Registry. We use orjson
because it's already a project dependency and is faster than the
stdlib json module.
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
            "occurred_at": event.occurred_at.isoformat(),
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
        return ClickEvent(
            url_id=int(payload["url_id"]),
            user_agent=str(payload["user_agent"]),
            ip_address=str(payload["ip_address"]),
            occurred_at=_parse_iso(payload["occurred_at"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"missing or invalid field: {exc}") from exc


def _parse_iso(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
