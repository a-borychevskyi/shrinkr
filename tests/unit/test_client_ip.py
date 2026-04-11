from unittest.mock import MagicMock

from src.utils.client_ip import get_client_ip


def _make_request(
    headers: dict[str, str] | None = None,
    client_host: str | None = "127.0.0.1",
) -> MagicMock:
    request = MagicMock()
    request.headers = headers or {}
    if client_host:
        request.client.host = client_host
    else:
        request.client = None
    return request


class TestGetClientIp:
    def test_x_forwarded_for_single(self):
        request = _make_request(headers={"x-forwarded-for": "203.0.113.1"})
        assert get_client_ip(request) == "203.0.113.1"

    def test_x_forwarded_for_multiple_takes_first(self):
        request = _make_request(
            headers={"x-forwarded-for": "203.0.113.1, 10.0.0.1, 10.0.0.2"}
        )
        assert get_client_ip(request) == "203.0.113.1"

    def test_x_forwarded_for_with_whitespace(self):
        request = _make_request(headers={"x-forwarded-for": "  203.0.113.1  "})
        assert get_client_ip(request) == "203.0.113.1"

    def test_x_real_ip_when_no_forwarded_for(self):
        request = _make_request(headers={"x-real-ip": "203.0.113.2"})
        assert get_client_ip(request) == "203.0.113.2"

    def test_x_forwarded_for_takes_priority_over_x_real_ip(self):
        request = _make_request(
            headers={
                "x-forwarded-for": "203.0.113.1",
                "x-real-ip": "203.0.113.2",
            }
        )
        assert get_client_ip(request) == "203.0.113.1"

    def test_falls_back_to_client_host(self):
        request = _make_request(headers={}, client_host="192.168.1.1")
        assert get_client_ip(request) == "192.168.1.1"

    def test_no_client_returns_unknown(self):
        request = _make_request(headers={}, client_host=None)
        assert get_client_ip(request) == "unknown"

    def test_empty_x_forwarded_for_falls_back(self):
        request = _make_request(
            headers={"x-forwarded-for": ""},
            client_host="192.168.1.1",
        )
        assert get_client_ip(request) == "192.168.1.1"
