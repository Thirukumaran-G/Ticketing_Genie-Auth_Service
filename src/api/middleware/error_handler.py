from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.core.exceptions.base import AppException
from src.observability.logging.logger import get_logger

logger = get_logger(__name__)


def setup_error_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        log_fn = logger.error if exc.status_code >= 500 else logger.warning
        log_fn(
            "app_exception",
            error_code=exc.error_code,
            message=exc.message,
            status_code=exc.status_code,
            path=str(request.url),
            method=request.method,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Pydantic v2 request body / query param validation errors."""
        errors = []
        for err in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in err["loc"] if loc != "body"),
                "message": err["msg"],
                "type": err["type"],
            })
        logger.warning(
            "request_validation_error",
            path=str(request.url),
            method=request.method,
            errors=errors,
        )
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": errors,
            },
        )

    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        """Pydantic ValidationError raised manually inside service layer."""
        logger.warning(
            "pydantic_validation_error",
            path=str(request.url),
            errors=exc.errors(),
        )
        return JSONResponse(
            status_code=422,
            content={
                "error_code": "VALIDATION_ERROR",
                "message": "Validation failed.",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=str(request.url),
            method=request.method,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred. Please try again later.",
                "details": None,
            },
        )