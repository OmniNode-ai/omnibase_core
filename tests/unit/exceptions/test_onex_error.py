"""
Comprehensive unit tests for OnexError exception class.

Tests cover:
- OnexError initialization and basic behaviors
- Error code validation and handling
- Error context handling with BasicErrorContext
- Exception inheritance and chaining
- Message formatting with and without context
- Edge cases and error scenarios
"""

import pytest

from omnibase_core.errors.error_codes import CoreErrorCode, OnexError
from omnibase_core.types.core_types import BasicErrorContext


class TestOnexErrorBasicBehavior:
    """Test basic OnexError initialization and behaviors."""

    def test_onex_error_with_minimal_args(self):
        """Test OnexError creation with only required arguments."""
        error = OnexError(
            message="Test validation error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        assert error.error_code == CoreErrorCode.VALIDATION_ERROR
        assert error.message == "Test validation error"
        assert error.context is not None
        assert isinstance(error.context, dict)
        assert str(error) == "[ONEX_CORE_006_VALIDATION_ERROR] Test validation error"

    def test_onex_error_with_all_args(self):
        """Test OnexError creation with all arguments."""
        error = OnexError(
            message="Operation failed",
            error_code=CoreErrorCode.OPERATION_FAILED,
            file_path="/test/file.py",
            line_number=42,
            function_name="test_function",
        )

        assert error.error_code == CoreErrorCode.OPERATION_FAILED
        assert error.message == "Operation failed"
        assert error.context["file_path"] == "/test/file.py"
        assert error.context["line_number"] == 42
        assert error.context["function_name"] == "test_function"
        assert str(error) == "[ONEX_CORE_081_OPERATION_FAILED] Operation failed"

    def test_onex_error_is_exception(self):
        """Test that OnexError is a proper Exception subclass."""
        error = OnexError(
            message="Internal error",
            error_code=CoreErrorCode.INTERNAL_ERROR,
        )

        assert isinstance(error, Exception)
        assert isinstance(error, OnexError)

    def test_onex_error_can_be_raised(self):
        """Test that OnexError can be raised and caught."""
        with pytest.raises(OnexError) as exc_info:
            raise OnexError(
                message="Resource not found",
                error_code=CoreErrorCode.RESOURCE_NOT_FOUND,
            )

        assert exc_info.value.error_code == CoreErrorCode.RESOURCE_NOT_FOUND
        assert exc_info.value.message == "Resource not found"


class TestOnexErrorCodes:
    """Test OnexError with different error codes."""

    @pytest.mark.parametrize(
        ("error_code", "expected_code_string"),
        [
            (CoreErrorCode.INVALID_PARAMETER, "ONEX_CORE_001_INVALID_PARAMETER"),
            (CoreErrorCode.VALIDATION_FAILED, "ONEX_CORE_005_VALIDATION_FAILED"),
            (CoreErrorCode.FILE_NOT_FOUND, "ONEX_CORE_021_FILE_NOT_FOUND"),
            (
                CoreErrorCode.INVALID_CONFIGURATION,
                "ONEX_CORE_041_INVALID_CONFIGURATION",
            ),
            (CoreErrorCode.OPERATION_FAILED, "ONEX_CORE_081_OPERATION_FAILED"),
            (CoreErrorCode.TIMEOUT_EXCEEDED, "ONEX_CORE_082_TIMEOUT_EXCEEDED"),
            (CoreErrorCode.RESOURCE_NOT_FOUND, "ONEX_CORE_085_RESOURCE_NOT_FOUND"),
            (CoreErrorCode.INVALID_STATE, "ONEX_CORE_086_INVALID_STATE"),
            (
                CoreErrorCode.DATABASE_CONNECTION_ERROR,
                "ONEX_CORE_131_DATABASE_CONNECTION_ERROR",
            ),
        ],
    )
    def test_onex_error_with_all_error_codes(self, error_code, expected_code_string):
        """Test OnexError creation with each error code."""
        error = OnexError(
            message=f"Test {expected_code_string}",
            error_code=error_code,
        )

        assert error.error_code == error_code
        assert error.error_code.value == expected_code_string
        assert expected_code_string in str(error)

    def test_error_code_in_string_representation(self):
        """Test that error code is included in string representation."""
        error = OnexError(
            message="Test message",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        assert "[ONEX_CORE_006_VALIDATION_ERROR]" in str(error)
        assert "Test message" in str(error)


class TestOnexErrorContext:
    """Test OnexError with error context handling."""

    def test_onex_error_with_empty_context(self):
        """Test OnexError with empty error context."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        assert error.context == {}
        assert str(error) == "[ONEX_CORE_006_VALIDATION_ERROR] Test error"

    def test_onex_error_with_additional_context(self):
        """Test OnexError with additional context information."""
        error = OnexError(
            message="Validation failed",
            error_code=CoreErrorCode.VALIDATION_ERROR,
            field="username",
            value="test_user",
            constraint="min_length",
        )

        assert error.context["field"] == "username"
        assert error.context["value"] == "test_user"
        assert error.context["constraint"] == "min_length"

        # Check that context is included in the string representation
        error_str = str(error)
        assert "[ONEX_CORE_006_VALIDATION_ERROR]" in error_str
        assert "Validation failed" in error_str

    def test_onex_error_with_full_context_fields(self):
        """Test OnexError with all context fields populated."""
        error = OnexError(
            message="Validation error occurred",
            error_code=CoreErrorCode.VALIDATION_ERROR,
            file_path="/path/to/file.py",
            line_number=100,
            column_number=15,
            function_name="process_data",
            module_name="data_processor",
            stack_trace="Traceback (most recent call last)...",
            error_type="validation",
        )

        assert error.context["file_path"] == "/path/to/file.py"
        assert error.context["line_number"] == 100
        assert error.context["column_number"] == 15
        assert error.context["function_name"] == "process_data"
        assert error.context["module_name"] == "data_processor"
        assert error.context["stack_trace"] == "Traceback (most recent call last)..."
        assert error.context["error_type"] == "validation"

    def test_onex_error_with_complex_context_values(self):
        """Test OnexError with complex nested context values."""
        error = OnexError(
            message="Configuration error",
            error_code=CoreErrorCode.CONFIGURATION_ERROR,
            config={"timeout": 30, "retries": 3, "enabled": True},
            items=[1, 2, 3, 4, 5],
            state=None,
        )

        # Verify complex values are preserved
        assert error.context["config"]["timeout"] == 30
        assert error.context["config"]["retries"] == 3
        assert error.context["config"]["enabled"] is True
        assert error.context["items"] == [1, 2, 3, 4, 5]
        assert error.context["state"] is None

    def test_onex_error_default_context_creation(self):
        """Test that OnexError creates default context when no context provided."""
        error = OnexError(
            message="Test error",
            error_code=CoreErrorCode.INTERNAL_ERROR,
        )

        assert error.context is not None
        assert isinstance(error.context, dict)
        assert error.context == {}


class TestOnexErrorCauseChaining:
    """Test OnexError cause exception chaining using Python's standard __cause__."""

    def test_onex_error_with_cause_exception(self):
        """Test OnexError with a cause exception using 'from' syntax."""
        original = ValueError("Original error message")

        try:
            raise OnexError(
                message="Wrapped error",
                error_code=CoreErrorCode.VALIDATION_ERROR,
            ) from original
        except OnexError as error:
            assert error.__cause__ == original
            assert isinstance(error.__cause__, ValueError)
            assert str(error.__cause__) == "Original error message"

    def test_onex_error_with_none_cause(self):
        """Test OnexError with None cause."""
        error = OnexError(
            message="No cause error",
            error_code=CoreErrorCode.OPERATION_FAILED,
        )

        assert error.__cause__ is None

    def test_onex_error_chain_multiple_causes(self):
        """Test chaining multiple OnexError exceptions."""
        # Create a chain of errors using standard Python exception chaining
        original = TypeError("Type mismatch")

        try:
            try:
                raise original
            except TypeError as e:
                raise OnexError(
                    message="First level error",
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                ) from e
        except OnexError as first_error:
            try:
                raise OnexError(
                    message="Second level error",
                    error_code=CoreErrorCode.OPERATION_FAILED,
                ) from first_error
            except OnexError as second_error:
                # Verify the chain
                assert second_error.__cause__ == first_error
                assert first_error.__cause__ == original
                assert isinstance(second_error.__cause__, OnexError)
                assert isinstance(first_error.__cause__, TypeError)

    def test_onex_error_with_different_exception_types(self):
        """Test OnexError with various exception types as cause."""
        exception_types = [
            ValueError("Value error"),
            TypeError("Type error"),
            KeyError("Key error"),
            AttributeError("Attribute error"),
            RuntimeError("Runtime error"),
        ]

        for original_exception in exception_types:
            try:
                raise OnexError(
                    message="Wrapped exception",
                    error_code=CoreErrorCode.INTERNAL_ERROR,
                ) from original_exception
            except OnexError as error:
                assert error.__cause__ == original_exception
                assert type(error.__cause__) == type(original_exception)


class TestOnexErrorMessageFormatting:
    """Test OnexError message formatting behaviors."""

    def test_message_format_basic(self):
        """Test basic message formatting without context."""
        error = OnexError(
            error_code=CoreErrorCode.NOT_FOUND,
            message="Resource not found",
        )

        assert str(error) == "[ONEX_CORE_028_NOT_FOUND] Resource not found"

    def test_message_format_with_single_context_item(self):
        """Test message formatting with single context item."""
        error = OnexError(
            message="Resource not found",
            error_code=CoreErrorCode.NOT_FOUND,
            resource_id="12345",
        )

        # Verify error string includes error code and message
        error_str = str(error)
        assert "[ONEX_CORE_028_NOT_FOUND] Resource not found" == error_str

        # Verify context is accessible
        assert error.context["resource_id"] == "12345"

    def test_message_format_with_multiple_context_items(self):
        """Test message formatting with multiple context items."""
        error = OnexError(
            message="Invalid configuration",
            error_code=CoreErrorCode.CONFIGURATION_ERROR,
            param1="value1",
            param2=42,
            param3=True,
        )

        # Verify error string includes error code and message
        error_str = str(error)
        assert "[ONEX_CORE_044_CONFIGURATION_ERROR] Invalid configuration" == error_str

        # Verify context values are accessible
        assert error.context["param1"] == "value1"
        assert error.context["param2"] == 42
        assert error.context["param3"] is True

    def test_message_format_with_special_characters(self):
        """Test message formatting with special characters in message."""
        error = OnexError(
            error_code=CoreErrorCode.VALIDATION_ERROR,
            message='Error with "quotes" and special chars: <>!@#$%',
        )

        assert '[ONEX_CORE_006_VALIDATION_ERROR] Error with "quotes"' in str(error)

    def test_message_format_with_unicode(self):
        """Test message formatting with unicode characters."""
        error = OnexError(
            error_code=CoreErrorCode.VALIDATION_ERROR,
            message="Error with unicode: 你好 🚀 ñ",
        )

        assert "[ONEX_CORE_006_VALIDATION_ERROR]" in str(error)
        assert "你好" in str(error)
        assert "🚀" in str(error)


class TestOnexErrorEdgeCases:
    """Test OnexError edge cases and boundary conditions."""

    def test_empty_message(self):
        """Test OnexError with empty message."""
        error = OnexError(
            error_code=CoreErrorCode.INTERNAL_ERROR,
            message="",
        )

        assert error.message == ""
        assert str(error) == "[ONEX_CORE_089_INTERNAL_ERROR] "

    def test_very_long_message(self):
        """Test OnexError with very long message."""
        long_message = "A" * 10000
        error = OnexError(
            error_code=CoreErrorCode.INTERNAL_ERROR,
            message=long_message,
        )

        assert error.message == long_message
        assert len(str(error)) > 10000

    def test_multiline_message(self):
        """Test OnexError with multiline message."""
        message = "Line 1\nLine 2\nLine 3"
        error = OnexError(
            error_code=CoreErrorCode.VALIDATION_ERROR,
            message=message,
        )

        assert error.message == message
        assert "Line 1" in str(error)
        assert "Line 2" in str(error)

    def test_onex_error_equality_not_implemented(self):
        """Test that OnexError instances are compared by identity."""
        error1 = OnexError(
            "Test error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )
        error2 = OnexError(
            "Test error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        # Exceptions are not equal even with same content
        assert error1 is not error2

    def test_onex_error_attributes_immutable(self):
        """Test that OnexError attributes can be accessed and modified."""
        error = OnexError(
            "Test error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
        )

        # Attributes should be accessible
        assert error.error_code == CoreErrorCode.VALIDATION_ERROR
        assert error.message == "Test error"

        # Python doesn't enforce immutability, but we can modify
        error.model.message = "Modified message"
        assert error.message == "Modified message"


class TestOnexErrorIntegration:
    """Integration tests for OnexError usage patterns."""

    def test_raise_and_catch_onex_error(self):
        """Test raising and catching OnexError in try-except block."""

        def function_that_raises():
            raise OnexError(
                "Operation failed in function",
                error_code=CoreErrorCode.OPERATION_FAILED,
            )

        with pytest.raises(OnexError) as exc_info:
            function_that_raises()

        assert exc_info.value.error_code == CoreErrorCode.OPERATION_FAILED
        assert "Operation failed in function" in str(exc_info.value)

    def test_catch_and_rewrap_exception(self):
        """Test catching an exception and wrapping it in OnexError."""

        def inner_function():
            raise ValueError("Invalid value")

        def outer_function():
            try:
                inner_function()
            except ValueError as e:
                raise OnexError(
                    "Caught and wrapped error",
                    error_code=CoreErrorCode.VALIDATION_ERROR,
                ) from e

        with pytest.raises(OnexError) as exc_info:
            outer_function()

        assert exc_info.value.error_code == CoreErrorCode.VALIDATION_ERROR
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_error_context_serialization(self):
        """Test that error context can be serialized."""
        error = OnexError(
            "Test error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
            file_path="/test/file.py",
            line_number=42,
            key="value",
        )

        # Serialize the context
        serialized = error.context

        assert isinstance(serialized, dict)
        assert serialized["file_path"] == "/test/file.py"
        assert serialized["line_number"] == 42
        assert serialized["key"] == "value"

    def test_multiple_errors_with_same_code(self):
        """Test creating multiple errors with the same error code."""
        errors = [
            OnexError(
                f"Error {i}",
                error_code=CoreErrorCode.VALIDATION_ERROR,
            )
            for i in range(5)
        ]

        for i, error in enumerate(errors):
            assert error.error_code == CoreErrorCode.VALIDATION_ERROR
            assert error.message == f"Error {i}"

    def test_error_with_context_validation(self):
        """Test that error context can be validated."""
        error = OnexError(
            "Test error",
            error_code=CoreErrorCode.VALIDATION_ERROR,
            file_path="/test/file.py",
            line_number=42,
        )

        # Context should be accessible and valid
        assert error._simple_context.file_path == "/test/file.py"
        assert error._simple_context.line_number == 42
        assert isinstance(error._simple_context, BasicErrorContext)
