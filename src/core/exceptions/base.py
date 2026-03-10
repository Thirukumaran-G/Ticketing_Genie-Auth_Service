from typing import Any


class AppException(Exception):
    """Root exception for all application errors."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        self.message = message or self.__class__.message
        self.details = details
        super().__init__(self.message)


class ValidationException(AppException):
    """Input validation failure."""
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation failed."


class AuthenticationException(AppException):
    """Authentication failure — bad credentials or missing token."""
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication failed."


class AuthorizationException(AppException):
    """Authorization failure — valid token but insufficient scope."""
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action."


class NotFoundException(AppException):
    """Resource not found."""
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found."


class ConflictException(AppException):
    """Resource already exists or state conflict."""
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource conflict."


class TokenExpiredException(AuthenticationException):
    """JWT token has expired."""
    error_code = "TOKEN_EXPIRED"
    message = "Token has expired."


class TokenRevokedException(AuthenticationException):
    """JWT token has been revoked."""
    error_code = "TOKEN_REVOKED"
    message = "Token has been revoked."


