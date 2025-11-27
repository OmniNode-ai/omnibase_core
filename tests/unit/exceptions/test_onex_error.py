"""
Comprehensive unit tests for ModelOnexError exception class.

Tests cover:
- ModelOnexError initialization and basic behaviors
- Error code validation and handling
- Error context handling with TypedDictBasicErrorContext
- Exception inheritance and chaining
- Message formatting with and without context
- Edge cases and error scenarios
"""

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestModelOnexErrorBasicBehavior:
    """Test basic ModelOnexError initialization and behaviors."""

    def test_onex_error_with_minimal_args(self):
        """Test ModelOnexError creation with only required arguments."""
        error = ModelOnexError(
            message="Test validation error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert error.message == "Test validation error"
        assert error.context is not None
        assert isinstance(error.context, dict)
        assert str(error) == "[ONEX_CORE_006_VALIDATION_ERROR] Test validation error"

    def test_onex_error_with_all_args(self):
        """Test ModelOnexError creation with all arguments."""
        error = ModelOnexError(
            message="Operation failed",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
            file_path="/test/file.py",
            line_number=42,
            function_name="test_function",
        )

        assert error.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert error.message == "Operation failed"
        assert error.context["file_path"] == "/test/file.py"
        assert error.context["line_number"] == 42
        assert error.context["function_name"] == "test_function"
        assert str(error) == "[ONEX_CORE_081_OPERATION_FAILED] Operation failed"

    def test_onex_error_is_exception(self):
        """Test that ModelOnexError is a proper Exception subclass."""
        error = ModelOnexError(
            message="Internal error",
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
        )

        assert isinstance(error, Exception)
        assert isinstance(error, ModelOnexError)

    def test_onex_error_can_be_raised(self):
        """Test that ModelOnexError can be raised and caught."""
        with pytest.raises(ModelOnexError) as exc_info:
            raise ModelOnexError(
                message="Resource not found",
                error_code=EnumCoreErrorCode.RESOURCE_NOT_FOUND,
            )

        assert exc_info.value.error_code == EnumCoreErrorCode.RESOURCE_NOT_FOUND
        assert exc_info.value.message == "Resource not found"


class TestModelOnexErrorCodes:
    """Test ModelOnexError with different error codes."""

    @pytest.mark.parametrize(
        ("error_code", "expected_code_string"),
        [
            (EnumCoreErrorCode.INVALID_PARAMETER, "ONEX_CORE_001_INVALID_PARAMETER"),
            (EnumCoreErrorCode.VALIDATION_FAILED, "ONEX_CORE_005_VALIDATION_FAILED"),
            (EnumCoreErrorCode.FILE_NOT_FOUND, "ONEX_CORE_021_FILE_NOT_FOUND"),
            (
                EnumCoreErrorCode.INVALID_CONFIGURATION,
                "ONEX_CORE_041_INVALID_CONFIGURATION",
            ),
            (EnumCoreErrorCode.OPERATION_FAILED, "ONEX_CORE_081_OPERATION_FAILED"),
            (EnumCoreErrorCode.TIMEOUT_EXCEEDED, "ONEX_CORE_082_TIMEOUT_EXCEEDED"),
            (EnumCoreErrorCode.RESOURCE_NOT_FOUND, "ONEX_CORE_085_RESOURCE_NOT_FOUND"),
            (EnumCoreErrorCode.INVALID_STATE, "ONEX_CORE_086_INVALID_STATE"),
            (
                EnumCoreErrorCode.DATABASE_CONNECTION_ERROR,
                "ONEX_CORE_131_DATABASE_CONNECTION_ERROR",
            ),
        ],
    )
    def test_onex_error_with_all_error_codes(self, error_code, expected_code_string):
        """Test ModelOnexError creation with each error code."""
        error = ModelOnexError(
            message=f"Test {expected_code_string}",
            error_code=error_code,
        )

        assert error.error_code == error_code
        assert error.error_code.value == expected_code_string
        assert expected_code_string in str(error)

    def test_error_code_in_string_representation(self):
        """Test that error code is included in string representation."""
        error = ModelOnexError(
            message="Test message",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

        assert "[ONEX_CORE_006_VALIDATION_ERROR]" in str(error)
        assert "Test message" in str(error)


class TestModelOnexErrorContext:
    """Test ModelOnexError with error context handling."""

    def test_onex_error_with_empty_context(self):
        """Test ModelOnexError with empty error context."""
        error = ModelOnexError(
            message="Test error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

        assert error.context == {}
        assert str(error) == "[ONEX_CORE_006_VALIDATION_ERROR] Test error"

    def test_onex_error_with_additional_context(self):
        """Test ModelOnexError with additional context information."""
        error = ModelOnexError(
            message="Validation failed",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            field="username",
            value="test_user",
            constraint="min_length",
        )

        assert error.context["additional_context"]["field"] == "username"
        assert error.context["additional_context"]["value"] == "test_user"
        assert error.context["additional_context"]["constraint"] == "min_length"

        # Check that context is included in the string representation
        error_str = str(error)
        assert "[ONEX_CORE_006_VALIDATION_ERROR]" in error_str
        assert "Validation failed" in error_str

    def test_onex_error_with_full_context_fields(self):
        """Test ModelOnexError with all context fields populated."""
        error = ModelOnexError(
            message="Validation error occurred",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
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
        assert error.context["additional_context"]["error_type"] == "validation"

    def test_onex_error_with_complex_context_values(self):
        """Test ModelOnexError with complex nested context values."""
        error = ModelOnexError(
            message="Configuration error",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            config={"timeout": 30, "retries": 3, "enabled": True},
            items=[1, 2, 3, 4, 5],
            state=None,
        )

        # Verify complex values are preserved
        assert error.context["additional_context"]["config"]["timeout"] == 30
        assert error.context["additional_context"]["config"]["retries"] == 3
        assert error.context["additional_context"]["config"]["enabled"] is True
        assert error.context["additional_context"]["items"] == [1, 2, 3, 4, 5]
        assert error.context["additional_context"]["state"] is None

    def test_onex_error_default_context_creation(self):
        """Test that ModelOnexError creates default context when no context provided."""
        error = ModelOnexError(
            message="Test error",
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
        )

        assert error.context is not None
        assert isinstance(error.context, dict)
        assert error.context == {}


class TestModelOnexErrorCauseChaining:
    """Test ModelOnexError cause exception chaining using Python's standard __cause__."""

    def test_onex_error_with_cause_exception(self):
        """Test ModelOnexError with a cause exception using 'from' syntax."""
        original = ValueError("Original error message")

        try:
            raise ModelOnexError(
                message="Wrapped error",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            ) from original
        except ModelOnexError as error:
            assert error.__cause__ == original
            assert isinstance(error.__cause__, ValueError)
            assert str(error.__cause__) == "Original error message"

    def test_onex_error_with_none_cause(self):
        """Test ModelOnexError with None cause."""
        error = ModelOnexError(
            message="No cause error",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
        )

        assert error.__cause__ is None

    def test_onex_error_chain_multiple_causes(self):
        """Test chaining multiple ModelOnexError exceptions."""
        # Create a chain of errors using standard Python exception chaining
        original = TypeError("Type mismatch")

        try:
            try:
                raise original
            except TypeError as e:
                raise ModelOnexError(
                    message="First level error",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                ) from e
        except ModelOnexError as first_error:
            try:
                raise ModelOnexError(
                    message="Second level error",
                    error_code=EnumCoreErrorCode.OPERATION_FAILED,
                ) from first_error
            except ModelOnexError as second_error:
                # Verify the chain
                assert second_error.__cause__ == first_error
                assert first_error.__cause__ == original
                assert isinstance(second_error.__cause__, ModelOnexError)
                assert isinstance(first_error.__cause__, TypeError)

    def test_onex_error_with_different_exception_types(self):
        """Test ModelOnexError with various exception types as cause."""
        exception_types = [
            ValueError("Value error"),
            TypeError("Type error"),
            KeyError("Key error"),
            AttributeError("Attribute error"),
            RuntimeError("Runtime error"),
        ]

        for original_exception in exception_types:
            try:
                raise ModelOnexError(
                    message="Wrapped exception",
                    error_code=EnumCoreErrorCode.INTERNAL_ERROR,
                ) from original_exception
            except ModelOnexError as error:
                assert error.__cause__ == original_exception
                assert type(error.__cause__) == type(original_exception)


class TestModelOnexErrorMessageFormatting:
    """Test ModelOnexError message formatting behaviors."""

    def test_message_format_basic(self):
        """Test basic message formatting without context."""
        error = ModelOnexError(
            error_code=EnumCoreErrorCode.NOT_FOUND,
            message="Resource not found",
        )

        assert str(error) == "[ONEX_CORE_028_NOT_FOUND] Resource not found"

    def test_message_format_with_single_context_item(self):
        """Test message formatting with single context item."""
        error = ModelOnexError(
            message="Resource not found",
            error_code=EnumCoreErrorCode.NOT_FOUND,
            resource_id="12345",
        )

        # Verify error string includes error code and message
        error_str = str(error)
        assert error_str == "[ONEX_CORE_028_NOT_FOUND] Resource not found"

        # Verify context is accessible
        assert error.context["additional_context"]["resource_id"] == "12345"

    def test_message_format_with_multiple_context_items(self):
        """Test message formatting with multiple context items."""
        error = ModelOnexError(
            message="Invalid configuration",
            error_code=EnumCoreErrorCode.CONFIGURATION_ERROR,
            param1="value1",
            param2=42,
            param3=True,
        )

        # Verify error string includes error code and message
        error_str = str(error)
        assert error_str == "[ONEX_CORE_044_CONFIGURATION_ERROR] Invalid configuration"

        # Verify context values are accessible
        assert error.context["additional_context"]["param1"] == "value1"
        assert error.context["additional_context"]["param2"] == 42
        assert error.context["additional_context"]["param3"] is True

    def test_message_format_with_special_characters(self):
        """Test message formatting with special characters in message."""
        error = ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message='Error with "quotes" and special chars: <>!@#$%',
        )

        assert '[ONEX_CORE_006_VALIDATION_ERROR] Error with "quotes"' in str(error)

    def test_message_format_with_unicode(self):
        """Test message formatting with unicode characters."""
        error = ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message="Error with unicode: 你好 🚀 ñ",
        )

        assert "[ONEX_CORE_006_VALIDATION_ERROR]" in str(error)
        assert "你好" in str(error)
        assert "🚀" in str(error)


class TestModelOnexErrorEdgeCases:
    """Test ModelOnexError edge cases and boundary conditions."""

    def test_empty_message(self):
        """Test ModelOnexError with empty message."""
        error = ModelOnexError(
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
            message="",
        )

        assert error.message == ""
        assert str(error) == "[ONEX_CORE_089_INTERNAL_ERROR] "

    def test_very_long_message(self):
        """Test ModelOnexError with very long message."""
        long_message = "A" * 10000
        error = ModelOnexError(
            error_code=EnumCoreErrorCode.INTERNAL_ERROR,
            message=long_message,
        )

        assert error.message == long_message
        assert len(str(error)) > 10000

    def test_multiline_message(self):
        """Test ModelOnexError with multiline message."""
        message = "Line 1\nLine 2\nLine 3"
        error = ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=message,
        )

        assert error.message == message
        assert "Line 1" in str(error)
        assert "Line 2" in str(error)

    def test_onex_error_equality_not_implemented(self):
        """Test that ModelOnexError instances are compared by identity."""
        error1 = ModelOnexError(
            "Test error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )
        error2 = ModelOnexError(
            "Test error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

        # Exceptions are not equal even with same content
        assert error1 is not error2

    def test_onex_error_attributes_immutable(self):
        """Test that ModelOnexError attributes can be accessed and modified."""
        error = ModelOnexError(
            "Test error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
        )

        # Attributes should be accessible
        assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert error.message == "Test error"

        # Python doesn't enforce immutability, but we can modify
        error.model.message = "Modified message"
        assert error.message == "Modified message"


class TestModelOnexErrorIntegration:
    """Integration tests for ModelOnexError usage patterns."""

    def test_raise_and_catch_onex_error(self):
        """Test raising and catching ModelOnexError in try-except block."""

        def function_that_raises():
            raise ModelOnexError(
                "Operation failed in function",
                error_code=EnumCoreErrorCode.OPERATION_FAILED,
            )

        with pytest.raises(ModelOnexError) as exc_info:
            function_that_raises()

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Operation failed in function" in str(exc_info.value)

    def test_catch_and_rewrap_exception(self):
        """Test catching an exception and wrapping it in ModelOnexError."""

        def inner_function():
            raise ValueError("Invalid value")

        def outer_function():
            try:
                inner_function()
            except ValueError as e:
                raise ModelOnexError(
                    "Caught and wrapped error",
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                ) from e

        with pytest.raises(ModelOnexError) as exc_info:
            outer_function()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_error_context_serialization(self):
        """Test that error context can be serialized."""
        error = ModelOnexError(
            "Test error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            file_path="/test/file.py",
            line_number=42,
            key="value",
        )

        # Serialize the context
        serialized = error.context

        assert isinstance(serialized, dict)
        assert serialized["file_path"] == "/test/file.py"
        assert serialized["line_number"] == 42
        assert serialized["additional_context"]["key"] == "value"

    def test_multiple_errors_with_same_code(self):
        """Test creating multiple errors with the same error code."""
        errors = [
            ModelOnexError(
                f"Error {i}",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )
            for i in range(5)
        ]

        for i, error in enumerate(errors):
            assert error.error_code == EnumCoreErrorCode.VALIDATION_ERROR
            assert error.message == f"Error {i}"

    def test_error_with_context_validation(self):
        """Test that error context can be validated."""
        error = ModelOnexError(
            "Test error",
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            file_path="/test/file.py",
            line_number=42,
        )

        # Context should be accessible and valid
        assert error._simple_context["file_path"] == "/test/file.py"
        assert error._simple_context["line_number"] == 42
        assert isinstance(error._simple_context, dict)
