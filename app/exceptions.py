"""Centralized exception definitions for the application.

This module provides a consistent exception hierarchy that maps to HTTP status codes
and provides reusable error messages across all APIs.
"""

from typing import Optional


class BaseAPIException(Exception):
    """Base exception for all API-related errors.

    All API exceptions should inherit from this class to ensure consistent
    error handling and HTTP status code mapping.
    """

    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        status_code: int = 500,
    ):
        """Initialize the exception.

        Args:
            message: Human-readable error message
            detail: Optional detailed error information
            status_code: HTTP status code for this exception
        """
        self.message = message
        self.detail = detail or message
        self.status_code = status_code
        super().__init__(self.message)


# HTTP Status Code Exceptions (4xx)
class BadRequestError(BaseAPIException):
    """Raised when the request is malformed or invalid (400)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=400)


class UnauthorizedError(BaseAPIException):
    """Raised when authentication is required or invalid (401)."""

    def __init__(
        self,
        message: str = "Authentication required",
        detail: Optional[str] = None,
    ):
        super().__init__(message, detail, status_code=401)


class ForbiddenError(BaseAPIException):
    """Raised when access is forbidden (403)."""

    def __init__(
        self, message: str = "Access forbidden", detail: Optional[str] = None
    ):
        super().__init__(message, detail, status_code=403)


class NotFoundError(BaseAPIException):
    """Raised when a requested resource is not found (404)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=404)


class ConflictError(BaseAPIException):
    """Raised when a resource conflict occurs (409)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=409)


class UnprocessableEntityError(BaseAPIException):
    """Raised when the request is valid but cannot be processed (422)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=422)


# HTTP Status Code Exceptions (5xx)
class InternalServerError(BaseAPIException):
    """Raised when an internal server error occurs (500)."""

    def __init__(
        self,
        message: str = "Internal server error",
        detail: Optional[str] = None,
    ):
        super().__init__(message, detail, status_code=500)


class BadGatewayError(BaseAPIException):
    """Raised when an upstream service is unavailable (502)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=502)


class ServiceUnavailableError(BaseAPIException):
    """Raised when a service is temporarily unavailable (503)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=503)


# Domain-Specific Exceptions


# Player-related exceptions
class PlayerNotFoundError(NotFoundError):
    """Raised when a requested player is not found."""

    def __init__(self, username: str, detail: Optional[str] = None):
        message = f"Player '{username}' not found in tracking system"
        super().__init__(message, detail)


class PlayerAlreadyExistsError(ConflictError):
    """Raised when trying to add a player that already exists."""

    def __init__(self, username: str, detail: Optional[str] = None):
        message = f"Player '{username}' already exists in tracking system"
        super().__init__(message, detail)


class InvalidUsernameError(BadRequestError):
    """Raised when a username is invalid."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail)


# OSRS API exceptions
class OSRSAPIError(BadGatewayError):
    """Base exception for OSRS API errors."""

    def __init__(
        self, message: str = "OSRS API error", detail: Optional[str] = None
    ):
        full_message = f"OSRS API unavailable: {message}"
        super().__init__(full_message, detail)


class OSRSPlayerNotFoundError(NotFoundError):
    """Raised when a player is not found in OSRS hiscores."""

    def __init__(self, username: str, detail: Optional[str] = None):
        message = f"Player '{username}' not found in OSRS hiscores"
        super().__init__(message, detail)


class RateLimitError(ServiceUnavailableError):
    """Raised when OSRS API rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        detail: Optional[str] = None,
    ):
        super().__init__(message, detail)


class APIUnavailableError(ServiceUnavailableError):
    """Raised when OSRS API is unavailable."""

    def __init__(
        self,
        message: str = "OSRS API is currently unavailable",
        detail: Optional[str] = None,
    ):
        super().__init__(message, detail)


# History/Statistics exceptions
class InsufficientDataError(UnprocessableEntityError):
    """Raised when there is insufficient data for an operation."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail)


# Service-level exceptions (these wrap other errors)
class ServiceError(InternalServerError):
    """Base exception for service-level errors."""

    def __init__(
        self, service_name: str, message: str, detail: Optional[str] = None
    ):
        full_message = f"{service_name} error: {message}"
        super().__init__(full_message, detail)


class PlayerServiceError(ServiceError):
    """Raised when a player service operation fails."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__("Player service", message, detail)


class HistoryServiceError(ServiceError):
    """Raised when a history service operation fails."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__("History service", message, detail)


class StatisticsServiceError(ServiceError):
    """Raised when a statistics service operation fails."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__("Statistics service", message, detail)
