from datetime import datetime, timezone


from src.kafka.producer import ClickProducer
from src.kafka.schema import ClickEvent, decode_click_event


class _StubKafkaProducer:
    """Captures produce() calls in memory; mimics confluent_kafka.Producer."""

    def __init__(self, raise_buffer_error: bool = False) -> None:
        self.calls: list[dict] = []
        self.poll_calls: list[float] = []
        self.flush_calls: list[float] = []
        self.raise_buffer_error = raise_buffer_error

    def produce(self, topic, key=None, value=None, on_delivery=None) -> None:
        if self.raise_buffer_error:
            raise BufferError("queue full")
        self.calls.append(
            {"topic": topic, "key": key, "value": value, "on_delivery": on_delivery}
        )

    def poll(self, timeout: float) -> int:
        self.poll_calls.append(timeout)
        return 0

    def flush(self, timeout: float) -> int:
        self.flush_calls.append(timeout)
        return 0


class TestClickProducer:
    def test_send_produces_to_topic_with_url_id_key(self):
        stub = _StubKafkaProducer()
        producer = ClickProducer(producer=stub, topic="clicks")
        ts = datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc)

        producer.send(
            ClickEvent(url_id=42, user_agent="ua", ip_address="ip", occurred_at=ts)
        )

        assert len(stub.calls) == 1
        call = stub.calls[0]
        assert call["topic"] == "clicks"
        assert call["key"] == b"42"
        decoded = decode_click_event(call["value"])
        assert decoded.url_id == 42
        assert decoded.user_agent == "ua"
        assert decoded.ip_address == "ip"
        assert decoded.occurred_at == ts

    def test_send_swallows_buffer_error(self):
        stub = _StubKafkaProducer(raise_buffer_error=True)
        producer = ClickProducer(producer=stub, topic="clicks")
        ts = datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc)

        # Must not raise — drop-on-full mirrors today's behaviour.
        producer.send(
            ClickEvent(url_id=1, user_agent="u", ip_address="i", occurred_at=ts)
        )

    def test_poll_drains_delivery_reports(self):
        stub = _StubKafkaProducer()
        producer = ClickProducer(producer=stub, topic="clicks")
        producer.poll()
        assert stub.poll_calls == [0]

    def test_flush_passes_timeout(self):
        stub = _StubKafkaProducer()
        producer = ClickProducer(producer=stub, topic="clicks")
        producer.flush(timeout=2.5)
        assert stub.flush_calls == [2.5]
