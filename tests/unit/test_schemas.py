import pytest
from pydantic import ValidationError

from src.api.v0.shortener.url.schemas import (
    ActivateUrlRequest,
    CreateShortUrlRequest,
    DeactivateUrlRequest,
    RedirectToUrlRequest,
)
from src.api.base import BasePayloadResponse, BaseResponse


class TestCreateShortUrlRequest:
    def test_valid_url(self):
        req = CreateShortUrlRequest(target_url="https://example.com")
        assert str(req.target_url) == "https://example.com/"

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError):
            CreateShortUrlRequest(target_url="not-a-url")

    def test_missing_url_rejected(self):
        with pytest.raises(ValidationError):
            CreateShortUrlRequest()


class TestRedirectToUrlRequest:
    def test_valid(self):
        req = RedirectToUrlRequest(short_code="abc123")
        assert req.short_code == "abc123"

    def test_missing_short_code_rejected(self):
        with pytest.raises(ValidationError):
            RedirectToUrlRequest()


class TestDeactivateUrlRequest:
    def test_valid(self):
        req = DeactivateUrlRequest(short_code="abc123")
        assert req.short_code == "abc123"


class TestActivateUrlRequest:
    def test_valid(self):
        req = ActivateUrlRequest(short_code="abc123")
        assert req.short_code == "abc123"


class TestBasePayloadResponse:
    def test_default_status_code(self):

        class TestResponse(BaseResponse):
            value: str

        resp = BasePayloadResponse[TestResponse](payload=TestResponse(value="test"))
        assert resp.status_code == 200

    def test_custom_status_code(self):

        class TestResponse(BaseResponse):
            value: str

        resp = BasePayloadResponse[TestResponse](
            payload=TestResponse(value="test"), status_code=201
        )
        assert resp.status_code == 201
