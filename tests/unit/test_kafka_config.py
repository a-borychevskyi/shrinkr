from src.config.kafka import KafkaConfig


class TestKafkaConfig:
    def test_required_fields_loaded_from_kwargs(self):
        config = KafkaConfig(
            KAFKA_BOOTSTRAP_SERVERS="broker:9092",
        )
        assert config.KAFKA_BOOTSTRAP_SERVERS == "broker:9092"
        assert config.KAFKA_CLICKS_TOPIC == "clicks"
        assert config.KAFKA_CONSUMER_GROUP == "click-ingester-group"
        assert config.KAFKA_PRODUCER_BUFFER_MAX_MESSAGES == 100_000
        assert config.KAFKA_PRODUCER_LINGER_MS == 10
        assert config.KAFKA_CONSUMER_BATCH_SIZE == 100
        assert config.KAFKA_CONSUMER_FLUSH_INTERVAL_MS == 100
        assert config.KAFKA_CONSUMER_POLL_TIMEOUT_MS == 500
        assert config.WORKER_HTTP_PORT == 8001

    def test_overrides_apply(self):
        config = KafkaConfig(
            KAFKA_BOOTSTRAP_SERVERS="broker:9092",
            KAFKA_CLICKS_TOPIC="other",
            KAFKA_CONSUMER_BATCH_SIZE=500,
        )
        assert config.KAFKA_CLICKS_TOPIC == "other"
        assert config.KAFKA_CONSUMER_BATCH_SIZE == 500
