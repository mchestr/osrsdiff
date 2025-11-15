"""Tests for exception classes."""

import pytest

from app.exceptions import (
    APIUnavailableError,
    BadGatewayError,
    BadRequestError,
    BaseAPIException,
    ConflictError,
    ForbiddenError,
    HistoryServiceError,
    InsufficientDataError,
    InternalServerError,
    InvalidUsernameError,
    NotFoundError,
    OSRSAPIError,
    OSRSPlayerNotFoundError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
    PlayerServiceError,
    RateLimitError,
    ServiceError,
    ServiceUnavailableError,
    StatisticsServiceError,
    UnauthorizedError,
    UnprocessableEntityError,
)


class TestBaseAPIException:
    """Test cases for BaseAPIException."""

    def test_base_exception_with_message(self):
        """Test BaseAPIException with just a message."""
        exc = BaseAPIException("Test error")

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.detail == "Test error"
        assert exc.status_code == 500

    def test_base_exception_with_detail(self):
        """Test BaseAPIException with message and detail."""
        exc = BaseAPIException("Test error", detail="Detailed error")

        assert exc.message == "Test error"
        assert exc.detail == "Detailed error"
        assert exc.status_code == 500

    def test_base_exception_with_custom_status_code(self):
        """Test BaseAPIException with custom status code."""
        exc = BaseAPIException("Test error", status_code=418)

        assert exc.status_code == 418


class TestHTTP4xxExceptions:
    """Test cases for 4xx HTTP exceptions."""

    def test_bad_request_error(self):
        """Test BadRequestError."""
        exc = BadRequestError("Bad request")

        assert exc.status_code == 400
        assert exc.message == "Bad request"

    def test_unauthorized_error_default_message(self):
        """Test UnauthorizedError with default message."""
        exc = UnauthorizedError()

        assert exc.status_code == 401
        assert exc.message == "Authentication required"

    def test_unauthorized_error_custom_message(self):
        """Test UnauthorizedError with custom message."""
        exc = UnauthorizedError("Custom auth error")

        assert exc.status_code == 401
        assert exc.message == "Custom auth error"

    def test_forbidden_error_default_message(self):
        """Test ForbiddenError with default message."""
        exc = ForbiddenError()

        assert exc.status_code == 403
        assert exc.message == "Access forbidden"

    def test_forbidden_error_custom_message(self):
        """Test ForbiddenError with custom message."""
        exc = ForbiddenError("Custom forbidden error")

        assert exc.status_code == 403
        assert exc.message == "Custom forbidden error"

    def test_not_found_error(self):
        """Test NotFoundError."""
        exc = NotFoundError("Resource not found")

        assert exc.status_code == 404
        assert exc.message == "Resource not found"

    def test_conflict_error(self):
        """Test ConflictError."""
        exc = ConflictError("Resource conflict")

        assert exc.status_code == 409
        assert exc.message == "Resource conflict"

    def test_unprocessable_entity_error(self):
        """Test UnprocessableEntityError."""
        exc = UnprocessableEntityError("Cannot process")

        assert exc.status_code == 422
        assert exc.message == "Cannot process"


class TestHTTP5xxExceptions:
    """Test cases for 5xx HTTP exceptions."""

    def test_internal_server_error_default_message(self):
        """Test InternalServerError with default message."""
        exc = InternalServerError()

        assert exc.status_code == 500
        assert exc.message == "Internal server error"

    def test_internal_server_error_custom_message(self):
        """Test InternalServerError with custom message."""
        exc = InternalServerError("Custom server error")

        assert exc.status_code == 500
        assert exc.message == "Custom server error"

    def test_bad_gateway_error(self):
        """Test BadGatewayError."""
        exc = BadGatewayError("Gateway error")

        assert exc.status_code == 502
        assert exc.message == "Gateway error"

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError."""
        exc = ServiceUnavailableError("Service unavailable")

        assert exc.status_code == 503
        assert exc.message == "Service unavailable"


class TestDomainSpecificExceptions:
    """Test cases for domain-specific exceptions."""

    def test_player_not_found_error(self):
        """Test PlayerNotFoundError."""
        exc = PlayerNotFoundError("testplayer")

        assert exc.status_code == 404
        assert "testplayer" in exc.message
        assert "not found in tracking system" in exc.message

    def test_player_already_exists_error(self):
        """Test PlayerAlreadyExistsError."""
        exc = PlayerAlreadyExistsError("testplayer")

        assert exc.status_code == 409
        assert "testplayer" in exc.message
        assert "already exists" in exc.message

    def test_invalid_username_error(self):
        """Test InvalidUsernameError."""
        exc = InvalidUsernameError("Invalid username format")

        assert exc.status_code == 400
        assert exc.message == "Invalid username format"

    def test_osrs_api_error_default_message(self):
        """Test OSRSAPIError with default message."""
        exc = OSRSAPIError()

        assert exc.status_code == 502
        assert "OSRS API unavailable" in exc.message

    def test_osrs_api_error_custom_message(self):
        """Test OSRSAPIError with custom message."""
        exc = OSRSAPIError("Connection timeout")

        assert exc.status_code == 502
        assert "OSRS API unavailable" in exc.message
        assert "Connection timeout" in exc.message

    def test_osrs_player_not_found_error(self):
        """Test OSRSPlayerNotFoundError."""
        exc = OSRSPlayerNotFoundError("testplayer")

        assert exc.status_code == 404
        assert "testplayer" in exc.message
        assert "not found in OSRS hiscores" in exc.message

    def test_rate_limit_error_default_message(self):
        """Test RateLimitError with default message."""
        exc = RateLimitError()

        assert exc.status_code == 503
        assert exc.message == "Rate limit exceeded"

    def test_rate_limit_error_custom_message(self):
        """Test RateLimitError with custom message."""
        exc = RateLimitError("Too many requests")

        assert exc.status_code == 503
        assert exc.message == "Too many requests"

    def test_api_unavailable_error_default_message(self):
        """Test APIUnavailableError with default message."""
        exc = APIUnavailableError()

        assert exc.status_code == 503
        assert exc.message == "OSRS API is currently unavailable"

    def test_api_unavailable_error_custom_message(self):
        """Test APIUnavailableError with custom message."""
        exc = APIUnavailableError("Maintenance mode")

        assert exc.status_code == 503
        assert exc.message == "Maintenance mode"

    def test_insufficient_data_error(self):
        """Test InsufficientDataError."""
        exc = InsufficientDataError("Not enough data points")

        assert exc.status_code == 422
        assert exc.message == "Not enough data points"


class TestServiceExceptions:
    """Test cases for service-level exceptions."""

    def test_service_error(self):
        """Test ServiceError."""
        exc = ServiceError("PlayerService", "Operation failed")

        assert exc.status_code == 500
        assert "PlayerService error" in exc.message
        assert "Operation failed" in exc.message

    def test_player_service_error(self):
        """Test PlayerServiceError."""
        exc = PlayerServiceError("Failed to fetch player")

        assert exc.status_code == 500
        assert "Player service" in exc.message
        assert "Failed to fetch player" in exc.message

    def test_history_service_error(self):
        """Test HistoryServiceError."""
        exc = HistoryServiceError("Failed to get history")

        assert exc.status_code == 500
        assert "History service" in exc.message
        assert "Failed to get history" in exc.message

    def test_statistics_service_error(self):
        """Test StatisticsServiceError."""
        exc = StatisticsServiceError("Failed to calculate stats")

        assert exc.status_code == 500
        assert "Statistics service" in exc.message
        assert "Failed to calculate stats" in exc.message
