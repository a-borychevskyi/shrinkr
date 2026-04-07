from src.models.errors.entity import ServiceErrorModel, ErrorModel


class BaseApplicationException(Exception):
    literal: str = "INTERNAL_SERVER_ERROR"
    key: str | None = None
    status_code: int = 500
    report_to_sentry: bool = True

    def __init__(
        self, message: str, details: dict | None = None, key: str | None = None
    ):
        self.message: str = message
        self.details = details
        self.key = key

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(message={self.message}, details={self.details})"
        )

    def __str__(self):
        return self.message

    def to_error_response(self) -> ServiceErrorModel:
        """Default error response format."""
        return ServiceErrorModel(
            errors=[
                ErrorModel(
                    error_class=f"{self.__class__.__module__}.{self.__class__.__name__}",
                    type=self.literal,
                    error_message=str(self.message),
                    key=self.key,
                )
            ],
        )


class ExceptionWithErrorsGroup(BaseApplicationException):
    literal: str = "INTERNAL_SERVER_ERROR"
    status_code: int = 500
    report_to_sentry: bool = True

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, details)
        self.__errors: list["ErrorModel"] = []

    @property
    def errors(self) -> list["ErrorModel"]:
        return self.__errors

    def add_error(self, error: "ErrorModel"):
        self.__errors.append(error)

    def process_results(self, results: list[BaseException]):
        for result in results:
            if isinstance(result, Exception):
                self.add_error(
                    ErrorModel(
                        errorMessage=str(result),  # type: ignore[call-arg]
                        errorClass=f"{result.__class__.__module__}.{result.__class__.__name__}",
                        # type: ignore[call-arg]
                        type=self.literal,
                    )
                )

        return self

    def to_error_response(self) -> ServiceErrorModel:
        return ServiceErrorModel(
            errors=self.errors
            or [
                ErrorModel(
                    error_class=f"{self.__class__.__module__}.{self.__class__.__name__}",
                    type=self.literal,
                    error_message=str(self.message),
                )
            ]
        )


class ValidationError(BaseApplicationException):
    literal = "VALIDATION_ERROR"
    status_code: int = 400
    report_to_sentry: bool = False

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message, details)
        self.__errors: list["ErrorModel"] = []

    @property
    def errors(self) -> list["ErrorModel"]:
        return self.__errors

    def add_error(self, error: "ErrorModel"):
        self.__errors.append(error)


class UnprocessableEntity(BaseApplicationException):
    literal = "UNPROCESSABLE_ENTITY"
    status_code: int = 422
    report_to_sentry: bool = False

    def to_error_response(self) -> ServiceErrorModel:
        return super().to_error_response()


class NotFound(BaseApplicationException):
    literal = "NOT_FOUND"
    status_code: int = 404
    report_to_sentry: bool = False

    def to_error_response(self) -> ServiceErrorModel:
        return super().to_error_response()


class BadRequest(BaseApplicationException):
    literal = "BAD_REQUEST"
    status_code: int = 400
    report_to_sentry: bool = False

    def to_error_response(self) -> ServiceErrorModel:
        return super().to_error_response()


class ExternalServiceError(BaseApplicationException):
    literal = "EXTERNAL_SERVICE_ERROR"
    status_code: int = 502
    report_to_sentry: bool = True

    def __init__(
        self,
        message: str,
        details: dict | None = None,
        upstream_url: str | None = None,
    ):
        super().__init__(message, details)
        self.upstream_url = upstream_url

    def to_error_response(self) -> ServiceErrorModel:
        return super().to_error_response()
