from unittest.mock import patch

import pytest

from src.telemetry import setup_profiling


@pytest.fixture
def enabled_config(monkeypatch):
    monkeypatch.setenv("PYROSCOPE_ENABLED", "true")
    monkeypatch.setenv("PYROSCOPE_SERVER_ADDRESS", "http://pyroscope:4040")
    monkeypatch.setenv("PYROSCOPE_SAMPLE_RATE", "100")
    monkeypatch.setenv("OTEL_SERVICE_NAME", "shrinkr-test")
    monkeypatch.setenv("APP_ENVIRONMENT", "test")


def test_noop_when_disabled(monkeypatch):
    monkeypatch.setenv("PYROSCOPE_ENABLED", "false")
    with patch("src.telemetry.pyroscope") as mock_pyroscope:
        setup_profiling()
    mock_pyroscope.configure.assert_not_called()


def test_configures_sdk_when_enabled(enabled_config):
    with patch("src.telemetry.pyroscope") as mock_pyroscope:
        setup_profiling()
    mock_pyroscope.configure.assert_called_once()
    kwargs = mock_pyroscope.configure.call_args.kwargs
    assert kwargs["application_name"] == "shrinkr-test"
    assert kwargs["server_address"] == "http://pyroscope:4040"
    assert kwargs["sample_rate"] == 100
    assert kwargs["tags"]["role"] == "api"
    assert kwargs["tags"]["env"] == "test"
    assert "instance" in kwargs["tags"]


def test_does_not_raise_on_configure_failure(enabled_config):
    with patch("src.telemetry.pyroscope") as mock_pyroscope:
        mock_pyroscope.configure.side_effect = RuntimeError("boom")
        setup_profiling()  # must not raise
