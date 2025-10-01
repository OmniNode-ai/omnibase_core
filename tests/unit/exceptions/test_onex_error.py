"""
Comprehensive unit tests for OnexError exception class.

Tests cover:
- OnexError initialization and basic behaviors
- Error code validation and handling
- Error context handling with ModelErrorContext
- Exception inheritance and chaining
- Message formatting with and without context
- Edge cases and error scenarios
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.exceptions.onex_error import OnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class TestOnexErrorBasicBehavior:
    """Test basic OnexError initialization and behaviors."""

    def test_onex_error_with_minimal_args(self):
        """Test OnexError creation with only required arguments."""
        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Test validation error",
        )

        assert error.code == EnumCoreErrorCode.VALIDATION_ERROR
        assert error.message == "Test validation error"
        assert error.details is not None
        assert isinstance(error.details, ModelErrorContext)
        assert error.cause is None
        assert str(error) == "[validation_error] Test validation error"

    def test_onex_error_with_all_args(self):
        """Test OnexError creation with all arguments."""
        context = ModelErrorContext(
            file_path="/test/file.py",
            line_number=42,
            function_name="test_function",
        )
        cause = ValueError("Original error")

        error = OnexError(
            code=EnumCoreErrorCode.OPERATION_FAILED,
            message="Operation failed",
            details=context,
            cause=cause,
        )

        assert error.code == EnumCoreErrorCode.OPERATION_FAILED
        assert error.message == "Operation failed"
        assert error.details == context
        assert error.cause == cause
        assert str(error) == "[operation_failed] Operation failed"

    def test_onex_error_is_exception(self):
        """Test that OnexError is a proper Exception subclass."""
        error = OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
            message="Internal error",
        )

        assert isinstance(error, Exception)
        assert isinstance(error, OnexError)

    def test_onex_error_can_be_raised(self):
        """Test that OnexError can be raised and caught."""
        with pytest.raises(OnexError) as exc_info:
            raise OnexError(
                code=EnumCoreErrorCode.NOT_FOUND,
                message="Resource not found",
            )

        assert exc_info.value.code == EnumCoreErrorCode.NOT_FOUND
        assert exc_info.value.message == "Resource not found"


class TestOnexErrorCodes:
    """Test OnexError with different error codes."""

    @pytest.mark.parametrize(
        "error_code,expected_value",
        [
            (EnumCoreErrorCode.VALIDATION_ERROR, "validation_error"),
            (EnumCoreErrorCode.OPERATION_FAILED, "operation_failed"),
            (EnumCoreErrorCode.NOT_FOUND, "not_found"),
            (EnumCoreErrorCode.CONFIGURATION_ERROR, "configuration_error"),
            (EnumCoreErrorCode.DEPENDENCY_ERROR, "dependency_error"),
            (EnumCoreErrorCode.NETWORK_ERROR, "network_error"),
            (EnumCoreErrorCode.TIMEOUT_ERROR, "timeout_error"),
            (EnumCoreErrorCode.PERMISSION_ERROR, "permission_error"),
            (EnumCoreErrorCode.RESOURCE_ERROR, "resource_error"),
            (EnumCoreErrorCode.INTERNAL_ERROR, "internal_error"),
            (EnumCoreErrorCode.CONVERSION_ERROR, "conversion_error"),
        ],
    )
    def test_onex_error_with_all_error_codes(self, error_code, expected_value):
        """Test OnexError creation with each error code."""
        error = OnexError(
            code=error_code,
            message=f"Test {expected_value}",
        )

        assert error.code == error_code
        assert error.code.value == expected_value
        assert expected_value in str(error)

    def test_error_code_in_string_representation(self):
        """Test that error code is included in string representation."""
        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Test message",
        )

        assert "[validation_error]" in str(error)
        assert "Test message" in str(error)


class TestOnexErrorContext:
    """Test OnexError with error context handling."""

    def test_onex_error_with_empty_context(self):
        """Test OnexError with empty error context."""
        context = ModelErrorContext.with_context({})
        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Test error",
            details=context,
        )

        assert error.details == context
        assert error.details.additional_context == {}
        assert str(error) == "[validation_error] Test error"

    def test_onex_error_with_additional_context(self):
        """Test OnexError with additional context information."""
        context = ModelErrorContext.with_context(
            {
                "field": ModelSchemaValue.from_value("username"),
                "value": ModelSchemaValue.from_value("test_user"),
                "constraint": ModelSchemaValue.from_value("min_length"),
            }
        )

        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Validation failed",
            details=context,
        )

        assert error.details.additional_context["field"].to_value() == "username"
        assert error.details.additional_context["value"].to_value() == "test_user"
        assert error.details.additional_context["constraint"].to_value() == "min_length"

        # Check that context is included in the string representation
        error_str = str(error)
        assert "[validation_error]" in error_str
        assert "Validation failed" in error_str
        assert "Context:" in error_str
        assert "field=username" in error_str
        assert "value=test_user" in error_str
        assert "constraint=min_length" in error_str

    def test_onex_error_with_full_context_fields(self):
        """Test OnexError with all ModelErrorContext fields populated."""
        context = ModelErrorContext(
            file_path="/path/to/file.py",
            line_number=100,
            column_number=15,
            function_name="process_data",
            module_name="data_processor",
            stack_trace="Traceback (most recent call last)...",
            additional_context={
                "error_type": ModelSchemaValue.from_value("validation"),
            },
        )

        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Validation error occurred",
            details=context,
        )

        assert error.details.file_path == "/path/to/file.py"
        assert error.details.line_number == 100
        assert error.details.column_number == 15
        assert error.details.function_name == "process_data"
        assert error.details.module_name == "data_processor"
        assert error.details.stack_trace == "Traceback (most recent call last)..."

    def test_onex_error_with_complex_context_values(self):
        """Test OnexError with complex nested context values."""
        context = ModelErrorContext.with_context(
            {
                "config": ModelSchemaValue.from_value(
                    {"timeout": 30, "retries": 3, "enabled": True}
                ),
                "items": ModelSchemaValue.from_value([1, 2, 3, 4, 5]),
                "status": ModelSchemaValue.from_value(None),
            }
        )

        error = OnexError(
            code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            message="Configuration error",
            details=context,
        )

        # Verify complex values are preserved
        config = error.details.additional_context["config"].to_value()
        assert config["timeout"] == 30
        assert config["retries"] == 3
        assert config["enabled"] is True

        items = error.details.additional_context["items"].to_value()
        assert items == [1, 2, 3, 4, 5]

        status = error.details.additional_context["status"].to_value()
        assert status is None

    def test_onex_error_default_context_creation(self):
        """Test that OnexError creates default context when None provided."""
        error = OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
            message="Test error",
            details=None,
        )

        assert error.details is not None
        assert isinstance(error.details, ModelErrorContext)
        assert error.details.additional_context == {}


class TestOnexErrorCauseChaining:
    """Test OnexError cause exception chaining."""

    def test_onex_error_with_cause_exception(self):
        """Test OnexError with a cause exception."""
        original = ValueError("Original error message")
        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Wrapped error",
            cause=original,
        )

        assert error.cause == original
        assert isinstance(error.cause, ValueError)
        assert str(error.cause) == "Original error message"

    def test_onex_error_with_none_cause(self):
        """Test OnexError with None cause."""
        error = OnexError(
            code=EnumCoreErrorCode.OPERATION_FAILED,
            message="No cause error",
            cause=None,
        )

        assert error.cause is None

    def test_onex_error_chain_multiple_causes(self):
        """Test chaining multiple OnexError exceptions."""
        # Create a chain of errors
        original = TypeError("Type mismatch")
        first_error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="First level error",
            cause=original,
        )
        second_error = OnexError(
            code=EnumCoreErrorCode.OPERATION_FAILED,
            message="Second level error",
            cause=first_error,
        )

        # Verify the chain
        assert second_error.cause == first_error
        assert first_error.cause == original
        assert isinstance(second_error.cause, OnexError)
        assert isinstance(first_error.cause, TypeError)

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
            error = OnexError(
                code=EnumCoreErrorCode.INTERNAL_ERROR,
                message="Wrapped exception",
                cause=original_exception,
            )

            assert error.cause == original_exception
            assert type(error.cause) == type(original_exception)


class TestOnexErrorMessageFormatting:
    """Test OnexError message formatting behaviors."""

    def test_message_format_basic(self):
        """Test basic message formatting without context."""
        error = OnexError(
            code=EnumCoreErrorCode.NOT_FOUND,
            message="Resource not found",
        )

        assert str(error) == "[not_found] Resource not found"

    def test_message_format_with_single_context_item(self):
        """Test message formatting with single context item."""
        context = ModelErrorContext.with_context(
            {"resource_id": ModelSchemaValue.from_value("12345")}
        )

        error = OnexError(
            code=EnumCoreErrorCode.NOT_FOUND,
            message="Resource not found",
            details=context,
        )

        error_str = str(error)
        assert "[not_found] Resource not found" in error_str
        assert "Context:" in error_str
        assert "resource_id=12345" in error_str

    def test_message_format_with_multiple_context_items(self):
        """Test message formatting with multiple context items."""
        context = ModelErrorContext.with_context(
            {
                "param1": ModelSchemaValue.from_value("value1"),
                "param2": ModelSchemaValue.from_value(42),
                "param3": ModelSchemaValue.from_value(True),
            }
        )

        error = OnexError(
            code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            message="Invalid configuration",
            details=context,
        )

        error_str = str(error)
        assert "[configuration_error] Invalid configuration" in error_str
        assert "Context:" in error_str
        assert "param1=value1" in error_str
        assert "param2=42" in error_str
        assert "param3=True" in error_str

    def test_message_format_with_special_characters(self):
        """Test message formatting with special characters in message."""
        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message='Error with "quotes" and special chars: <>!@#$%',
        )

        assert '[validation_error] Error with "quotes"' in str(error)

    def test_message_format_with_unicode(self):
        """Test message formatting with unicode characters."""
        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Error with unicode: 你好 🚀 ñ",
        )

        assert "[validation_error]" in str(error)
        assert "你好" in str(error)
        assert "🚀" in str(error)


class TestOnexErrorEdgeCases:
    """Test OnexError edge cases and boundary conditions."""

    def test_empty_message(self):
        """Test OnexError with empty message."""
        error = OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
            message="",
        )

        assert error.message == ""
        assert str(error) == "[internal_error] "

    def test_very_long_message(self):
        """Test OnexError with very long message."""
        long_message = "A" * 10000
        error = OnexError(
            code=EnumCoreErrorCode.INTERNAL_ERROR,
            message=long_message,
        )

        assert error.message == long_message
        assert len(str(error)) > 10000

    def test_multiline_message(self):
        """Test OnexError with multiline message."""
        message = "Line 1\nLine 2\nLine 3"
        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=message,
        )

        assert error.message == message
        assert "Line 1" in str(error)
        assert "Line 2" in str(error)

    def test_onex_error_equality_not_implemented(self):
        """Test that OnexError instances are compared by identity."""
        error1 = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Test error",
        )
        error2 = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Test error",
        )

        # Exceptions are not equal even with same content
        assert error1 is not error2

    def test_onex_error_attributes_immutable(self):
        """Test that OnexError attributes can be accessed and modified."""
        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Test error",
        )

        # Attributes should be accessible
        assert error.code == EnumCoreErrorCode.VALIDATION_ERROR
        assert error.message == "Test error"

        # Python doesn't enforce immutability, but we can modify
        error.message = "Modified message"
        assert error.message == "Modified message"


class TestOnexErrorIntegration:
    """Integration tests for OnexError usage patterns."""

    def test_raise_and_catch_onex_error(self):
        """Test raising and catching OnexError in try-except block."""

        def function_that_raises():
            raise OnexError(
                code=EnumCoreErrorCode.OPERATION_FAILED,
                message="Operation failed in function",
            )

        with pytest.raises(OnexError) as exc_info:
            function_that_raises()

        assert exc_info.value.code == EnumCoreErrorCode.OPERATION_FAILED
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
                    code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Caught and wrapped error",
                    cause=e,
                )

        with pytest.raises(OnexError) as exc_info:
            outer_function()

        assert exc_info.value.code == EnumCoreErrorCode.VALIDATION_ERROR
        assert isinstance(exc_info.value.cause, ValueError)

    def test_error_context_serialization(self):
        """Test that error context can be serialized."""
        context = ModelErrorContext(
            file_path="/test/file.py",
            line_number=42,
            additional_context={
                "key": ModelSchemaValue.from_value("value"),
            },
        )

        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Test error",
            details=context,
        )

        # Serialize the context
        serialized = error.details.serialize()

        assert isinstance(serialized, dict)
        assert serialized["file_path"] == "/test/file.py"
        assert serialized["line_number"] == 42

    def test_multiple_errors_with_same_code(self):
        """Test creating multiple errors with the same error code."""
        errors = [
            OnexError(
                code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Error {i}",
            )
            for i in range(5)
        ]

        for i, error in enumerate(errors):
            assert error.code == EnumCoreErrorCode.VALIDATION_ERROR
            assert error.message == f"Error {i}"

    def test_error_with_context_validation(self):
        """Test that error context can be validated."""
        context = ModelErrorContext(
            file_path="/test/file.py",
            line_number=42,
        )

        error = OnexError(
            code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Test error",
            details=context,
        )

        # Context should be valid
        assert error.details.validate_instance() is True
