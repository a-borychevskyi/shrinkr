from src.utils.exceptions.base import BaseApplicationException


class RateLimitExceeded(BaseApplicationException):
    literal = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    report_to_sentry = False

    def __init__(
        self,
        retry_after: int,
        message: str = "Rate limit exceeded",
        headers: dict[str, str] | None = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.headers = headers or {}
        self.headers["Retry-After"] = str(retry_after)
