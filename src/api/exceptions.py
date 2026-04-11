import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.models.errors.entity import ErrorModel, ServiceErrorModel
from src.utils.exceptions.base import BaseApplicationException
from src.utils.exceptions.rate_limit import RateLimitExceeded

logger = structlog.get_logger(__name__)


def _error_response_to_dict(error_response: ServiceErrorModel) -> dict:
    return error_response.model_dump(
        by_alias=True, exclude_none=True, exclude_unset=True, mode="json"
    )


def _build_validation_errors(
    exc: RequestValidationError,
) -> list[ErrorModel]:
    errors = []
    error_class = f"{exc.__class__.__module__}.{exc.__class__.__name__}"

    for error in exc.errors():
        field = None
        if error.get("loc") and len(error["loc"]) > 1:
            loc = error["loc"][-1]
            if isinstance(loc, str):
                field = loc

        errors.append(
            ErrorModel(
                error_class=error_class,
                type="VALIDATION_ERROR",
                error_message=error.get("msg"),
                field=field,
            )
        )

    return errors


class ExceptionHandler:
    def __init__(self, app: FastAPI):
        self.app = app

    def register_handlers(self):
        @self.app.exception_handler(RequestValidationError)
        async def validation_exception_handler(
            request: Request, exc: RequestValidationError
        ) -> JSONResponse:
            logger.warning("validation_error", detail=str(exc))
            return JSONResponse(
                status_code=422,
                content=_error_response_to_dict(
                    ServiceErrorModel(errors=_build_validation_errors(exc))
                ),
            )

        @self.app.exception_handler(StarletteHTTPException)
        async def http_exception_handler(
            request: Request, exc: StarletteHTTPException
        ) -> JSONResponse:
            logger.warning("http_error", status_code=exc.status_code, detail=exc.detail)
            error_type = "NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
            return JSONResponse(
                status_code=exc.status_code,
                content=_error_response_to_dict(
                    ServiceErrorModel(
                        errors=[
                            ErrorModel(
                                error_class=f"{exc.__class__.__module__}.{exc.__class__.__name__}",
                                type=error_type,
                                error_message=str(exc.detail),
                            )
                        ]
                    )
                ),
            )

        @self.app.exception_handler(RateLimitExceeded)
        async def rate_limit_exception_handler(
            request: Request, exc: RateLimitExceeded
        ) -> JSONResponse:
            logger.warning("rate_limit_exceeded", detail=str(exc))
            return JSONResponse(
                status_code=exc.status_code,
                content=_error_response_to_dict(exc.to_error_response()),
                headers=exc.headers,
            )

        @self.app.exception_handler(BaseApplicationException)
        async def application_exception_handler(
            request: Request, exc: BaseApplicationException
        ) -> JSONResponse:
            logger.warning("application_error", detail=str(exc))
            return JSONResponse(
                status_code=exc.status_code,
                content=_error_response_to_dict(exc.to_error_response()),
            )

        @self.app.exception_handler(Exception)
        async def global_exception_handler(
            request: Request, exc: Exception
        ) -> JSONResponse:
            logger.error("unhandled_exception", detail=str(exc), exc_info=exc)
            fallback = BaseApplicationException(str(exc))
            return JSONResponse(
                status_code=500,
                content=_error_response_to_dict(fallback.to_error_response()),
            )
