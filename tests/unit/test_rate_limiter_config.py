import pytest
from pydantic import ValidationError

from src.config.rate_limiter import RateLimiterConfig


class TestRateLimiterConfig:
    def test_defaults(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")

        config = RateLimiterConfig()

        assert config.RATE_LIMIT_DEFAULT_TIMES == 60
        assert config.RATE_LIMIT_DEFAULT_WINDOW == 60
        assert config.RATE_LIMIT_ENABLED is True
        assert config.RATE_LIMIT_KEY_PREFIX == "rl"

    def test_override_via_env(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_TIMES", "100")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_WINDOW", "120")
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        monkeypatch.setenv("RATE_LIMIT_KEY_PREFIX", "ratelimit")

        config = RateLimiterConfig()

        assert config.RATE_LIMIT_DEFAULT_TIMES == 100
        assert config.RATE_LIMIT_DEFAULT_WINDOW == 120
        assert config.RATE_LIMIT_ENABLED is False
        assert config.RATE_LIMIT_KEY_PREFIX == "ratelimit"

    def test_rejects_zero_times(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_TIMES", "0")

        with pytest.raises(ValidationError):
            RateLimiterConfig()

    def test_rejects_negative_window(self, monkeypatch):
        monkeypatch.setenv("REDIS_HOST", "localhost")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_DB", "0")
        monkeypatch.setenv("APP_PREFIX", "shrinkr")
        monkeypatch.setenv("RATE_LIMIT_DEFAULT_WINDOW", "-1")

        with pytest.raises(ValidationError):
            RateLimiterConfig()
