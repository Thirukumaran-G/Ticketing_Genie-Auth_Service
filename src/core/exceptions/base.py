from typing import Any


class AppException(Exception):
    """Root exception for all application errors."""
    status_code: int = 500
    error_code:  str = "INTERNAL_ERROR"
    message:     str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, details: Any = None) -> None:
        self.message = message or self.__class__.message
        self.details = details
        super().__init__(self.message)


class ValidationException(AppException):
    status_code = 422
    error_code  = "VALIDATION_ERROR"
    message     = "Validation failed."


class AuthenticationException(AppException):
    status_code = 401
    error_code  = "AUTHENTICATION_ERROR"
    message     = "Invalid email or password."


class AuthorizationException(AppException):
    status_code = 403
    error_code  = "AUTHORIZATION_ERROR"
    message     = "You do not have permission to perform this action."


class NotFoundException(AppException):
    status_code = 404
    error_code  = "NOT_FOUND"
    message     = "Resource not found."


class ConflictException(AppException):
    status_code = 409
    error_code  = "CONFLICT"
    message     = "Resource conflict."


class TokenExpiredException(AuthenticationException):
    error_code = "TOKEN_EXPIRED"
    message    = "Your session has expired. Please sign in again."


class TokenRevokedException(AuthenticationException):
    error_code = "TOKEN_REVOKED"
    message    = "Your session was ended. Please sign in again."

class DomainRequiredException(ValidationException):
    error_code = "DOMAIN_REQUIRED"
    message    = "Domain is required to create a company."


class InvalidDomainException(ValidationException):
    error_code = "INVALID_DOMAIN"
    message    = "Enter a valid domain (e.g. acme.com)."

class DescriptionRequiredException(ValidationException):
    error_code = "DESCRIPTION_REQUIRED"
    message    = "Description is required to create a product."
