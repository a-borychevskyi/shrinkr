from src.models.errors.entity import ErrorModel
from src.utils.exceptions.base import (
    BadRequest,
    BaseApplicationException,
    ExceptionWithErrorsGroup,
    ExternalServiceError,
    NotFound,
    UnprocessableEntity,
    ValidationError,
)


class TestExceptionHierarchy:
    def test_not_found_status_code(self):
        exc = NotFound(message="not found")
        assert exc.status_code == 404
        assert exc.literal == "NOT_FOUND"

    def test_bad_request_status_code(self):
        exc = BadRequest(message="bad request")
        assert exc.status_code == 400

    def test_unprocessable_entity_status_code(self):
        exc = UnprocessableEntity(message="unprocessable")
        assert exc.status_code == 422

    def test_validation_error_status_code(self):
        exc = ValidationError(message="invalid")
        assert exc.status_code == 400
        assert exc.report_to_sentry is False

    def test_external_service_error(self):
        exc = ExternalServiceError(
            message="upstream failed", upstream_url="https://api.example.com"
        )
        assert exc.status_code == 502
        assert exc.upstream_url == "https://api.example.com"

    def test_base_exception_defaults(self):
        exc = BaseApplicationException(message="oops")
        assert exc.status_code == 500
        assert exc.report_to_sentry is True

    def test_to_error_response(self):
        exc = NotFound(message="Url not found")
        resp = exc.to_error_response()
        assert len(resp.errors) == 1
        assert resp.errors[0].type == "NOT_FOUND"
        assert resp.errors[0].error_message == "Url not found"

    def test_str_repr(self):
        exc = NotFound(message="gone")
        assert str(exc) == "gone"
        assert "NotFound" in repr(exc)

    def test_base_exception_with_key(self):
        exc = BaseApplicationException(message="err", key="some_key")
        assert exc.key == "some_key"
        resp = exc.to_error_response()
        assert resp.errors[0].key == "some_key"

    def test_base_exception_with_details(self):
        exc = BaseApplicationException(message="err", details={"foo": "bar"})
        assert exc.details == {"foo": "bar"}


class TestExceptionWithErrorsGroup:
    def test_add_error_and_to_response(self):
        exc = ExceptionWithErrorsGroup(message="group error")
        error = ErrorModel(
            errorClass="test.Error", type="TEST_ERROR", errorMessage="detail"
        )
        exc.add_error(error)

        assert len(exc.errors) == 1
        resp = exc.to_error_response()
        assert len(resp.errors) == 1
        assert resp.errors[0].type == "TEST_ERROR"

    def test_to_response_fallback_when_no_errors(self):
        exc = ExceptionWithErrorsGroup(message="fallback msg")

        resp = exc.to_error_response()
        assert len(resp.errors) == 1
        assert resp.errors[0].type == "INTERNAL_SERVER_ERROR"
        assert resp.errors[0].error_message == "fallback msg"

    def test_process_results(self):
        exc = ExceptionWithErrorsGroup(message="batch")
        results = [
            ValueError("bad value"),
            TypeError("bad type"),
        ]
        returned = exc.process_results(results)

        assert returned is exc
        assert len(exc.errors) == 2

    def test_process_results_skips_non_exceptions(self):
        exc = ExceptionWithErrorsGroup(message="batch")
        exc.process_results([ValueError("err")])
        assert len(exc.errors) == 1


class TestValidationErrorException:
    def test_add_error(self):
        exc = ValidationError(message="invalid input")
        error = ErrorModel(
            errorClass="test.Validation",
            type="VALIDATION_ERROR",
            errorMessage="field required",
        )
        exc.add_error(error)

        assert len(exc.errors) == 1
        assert exc.errors[0].type == "VALIDATION_ERROR"

    def test_empty_errors_list(self):
        exc = ValidationError(message="no errors added")
        assert exc.errors == []
