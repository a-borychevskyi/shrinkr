import pytest
from pydantic import ValidationError

from src.config.profiling import ProfilingConfig


def test_defaults_are_safe_for_local_dev(monkeypatch):
    for var in (
        "PYROSCOPE_ENABLED",
        "PYROSCOPE_SERVER_ADDRESS",
        "PYROSCOPE_SAMPLE_RATE",
    ):
        monkeypatch.delenv(var, raising=False)
    config = ProfilingConfig(_env_file=None)
    assert config.PYROSCOPE_ENABLED is False
    assert config.PYROSCOPE_SERVER_ADDRESS == "http://pyroscope:4040"
    assert config.PYROSCOPE_SAMPLE_RATE == 100


def test_env_vars_are_parsed(monkeypatch):
    monkeypatch.setenv("PYROSCOPE_ENABLED", "true")
    monkeypatch.setenv("PYROSCOPE_SERVER_ADDRESS", "http://other:4040")
    monkeypatch.setenv("PYROSCOPE_SAMPLE_RATE", "250")
    config = ProfilingConfig(_env_file=None)
    assert config.PYROSCOPE_ENABLED is True
    assert config.PYROSCOPE_SERVER_ADDRESS == "http://other:4040"
    assert config.PYROSCOPE_SAMPLE_RATE == 250


def test_non_positive_sample_rate_is_rejected(monkeypatch):
    monkeypatch.setenv("PYROSCOPE_SAMPLE_RATE", "0")
    with pytest.raises(ValidationError):
        ProfilingConfig(_env_file=None)
