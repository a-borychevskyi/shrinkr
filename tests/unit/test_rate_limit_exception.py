from src.utils.exceptions.rate_limit import RateLimitExceeded


class TestRateLimitExceeded:
    def test_status_code(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.status_code == 429

    def test_literal(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.literal == "RATE_LIMIT_EXCEEDED"

    def test_default_message(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.message == "Rate limit exceeded"

    def test_custom_message(self):
        exc = RateLimitExceeded(retry_after=30, message="Too many requests")
        assert exc.message == "Too many requests"

    def test_retry_after(self):
        exc = RateLimitExceeded(retry_after=45)
        assert exc.retry_after == 45

    def test_headers(self):
        exc = RateLimitExceeded(
            retry_after=30,
            headers={
                "X-RateLimit-Limit": "10",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1234567890",
            },
        )
        assert exc.headers["X-RateLimit-Limit"] == "10"
        assert exc.headers["Retry-After"] == "30"

    def test_to_error_response(self):
        exc = RateLimitExceeded(retry_after=30)
        resp = exc.to_error_response()
        assert len(resp.errors) == 1
        assert resp.errors[0].type == "RATE_LIMIT_EXCEEDED"

    def test_not_reported_to_sentry(self):
        exc = RateLimitExceeded(retry_after=30)
        assert exc.report_to_sentry is False
