"""
Test suite for error handling functionality.

Tests OnexError exception class and error handling decorators.
"""

import pytest

from omnibase_core.exceptions.base_onex_error import OnexError


class TestErrorHandling:
    """Test cases for error handling."""

    def test_onex_error_creation(self):
        """Test OnexError exception creation."""
        error = OnexError(message="Test error message", error_code="TEST_ERROR")

        assert str(error) == "Test error message"
        assert error.error_code == "TEST_ERROR"

    def test_onex_error_with_context(self):
        """Test OnexError with additional context."""
        error = OnexError(
            message="Test error with context", error_code="TEST_ERROR_CONTEXT"
        )

        assert error.message == "Test error with context"
        assert error.error_code == "TEST_ERROR_CONTEXT"
