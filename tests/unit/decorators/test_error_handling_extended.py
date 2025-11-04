"""
Comprehensive tests for error handling decorators.

Tests cover:
- standard_error_handling decorator with various exception types
- validation_error_handling decorator for validation-specific errors
- io_error_handling decorator for file/network operations
- Exception propagation and chaining
- Error context preservation
- Decorator stacking and composition
- Edge cases and boundary conditions

Target: 90%+ coverage for decorators/error_handling.py
"""

import pytest

from omnibase_core.decorators.error_handling import (
    io_error_handling,
    standard_error_handling,
    validation_error_handling,
)
from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


class TestStandardErrorHandling:
    """Test standard_error_handling decorator."""

    def test_standard_error_handling_success(self):
        """Test decorator allows successful execution."""

        @standard_error_handling("Test operation")
        def successful_function(value: int) -> int:
            return value * 2

        result = successful_function(5)
        assert result == 10

    def test_standard_error_handling_with_no_args(self):
        """Test decorator with default operation name."""

        @standard_error_handling()
        def test_function() -> str:
            return "success"

        result = test_function()
        assert result == "success"

    def test_standard_error_handling_propagates_onex_error(self):
        """Test that ModelOnexError is re-raised without wrapping."""

        @standard_error_handling("Test operation")
        def raises_onex_error():
            raise ModelOnexError(
                "Original ONEX error",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        with pytest.raises(ModelOnexError) as exc_info:
            raises_onex_error()

        # Should be the same error, not wrapped
        assert exc_info.value.message == "Original ONEX error"
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_standard_error_handling_wraps_generic_exception(self):
        """Test that generic exceptions are wrapped in ModelOnexError."""

        @standard_error_handling("Data processing")
        def raises_value_error():
            raise ValueError("Invalid data format")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_value_error()

        # Should be wrapped with proper error code
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Data processing failed" in exc_info.value.message
        assert "Invalid data format" in exc_info.value.message

        # Original exception should be chained
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert str(exc_info.value.__cause__) == "Invalid data format"

    def test_standard_error_handling_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""

        @standard_error_handling("Test")
        def documented_function():
            """This is a test function."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is a test function."

    def test_standard_error_handling_with_args_and_kwargs(self):
        """Test decorator works with functions accepting various arguments."""

        @standard_error_handling("Calculation")
        def calculate(a: int, b: int, operation: str = "add") -> int:
            if operation == "add":
                return a + b
            elif operation == "multiply":
                return a * b
            raise ValueError(f"Unknown operation: {operation}")

        assert calculate(3, 4) == 7
        assert calculate(3, 4, operation="multiply") == 12

        with pytest.raises(ModelOnexError) as exc_info:
            calculate(3, 4, operation="invalid")

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Calculation failed" in exc_info.value.message

    def test_standard_error_handling_with_different_exception_types(self):
        """Test decorator handles various exception types correctly."""
        exception_types = [
            (TypeError, "Type error occurred"),
            (KeyError, "key_not_found"),
            (AttributeError, "Attribute missing"),
            (RuntimeError, "Runtime problem"),
            (ZeroDivisionError, "Division by zero"),
        ]

        for exc_type, exc_message in exception_types:

            @standard_error_handling("Operation")
            def raises_exception(
                _exc_type: type[Exception] = exc_type,
                _exc_message: str = exc_message,
            ):
                raise _exc_type(_exc_message)

            with pytest.raises(ModelOnexError) as exc_info:
                raises_exception()

            assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
            assert isinstance(exc_info.value.__cause__, exc_type)

    def test_standard_error_handling_with_return_none(self):
        """Test decorator works with functions returning None."""

        @standard_error_handling("Void operation")
        def returns_none() -> None:
            pass

        result = returns_none()
        assert result is None

    def test_standard_error_handling_with_complex_return_types(self):
        """Test decorator works with complex return types."""

        @standard_error_handling("Complex operation")
        def returns_dict() -> dict[str, int]:
            return {"a": 1, "b": 2, "c": 3}

        result = returns_dict()
        assert result == {"a": 1, "b": 2, "c": 3}


class TestValidationErrorHandling:
    """Test validation_error_handling decorator."""

    def test_validation_error_handling_success(self):
        """Test decorator allows successful validation."""

        @validation_error_handling("User validation")
        def validate_user(username: str) -> bool:
            return len(username) >= 3

        result = validate_user("john")
        assert result is True

    def test_validation_error_handling_propagates_onex_error(self):
        """Test that ModelOnexError is re-raised without wrapping."""

        @validation_error_handling("Schema validation")
        def validate_schema():
            raise ModelOnexError(
                "Schema mismatch",
                error_code=EnumCoreErrorCode.VALIDATION_FAILED,
            )

        with pytest.raises(ModelOnexError) as exc_info:
            validate_schema()

        assert exc_info.value.message == "Schema mismatch"
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_FAILED

    def test_validation_error_handling_wraps_validation_error(self):
        """Test that validation errors get VALIDATION_ERROR code."""

        class ValidationError(Exception):
            """Custom validation error with errors attribute."""

            def __init__(self, message: str):
                super().__init__(message)
                self.errors = [{"field": "username", "error": "too short"}]

        @validation_error_handling("User validation")
        def validate_with_pydantic_style():
            raise ValidationError("Validation failed")

        with pytest.raises(ModelOnexError) as exc_info:
            validate_with_pydantic_style()

        # Should use VALIDATION_ERROR code for errors with .errors attribute
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "User validation failed" in exc_info.value.message
        assert isinstance(exc_info.value.__cause__, ValidationError)

    def test_validation_error_handling_detects_validation_in_message(self):
        """Test that 'validation' in error message triggers VALIDATION_ERROR code."""

        @validation_error_handling("Contract validation")
        def validate_contract():
            raise ValueError("Validation of contract field failed")

        with pytest.raises(ModelOnexError) as exc_info:
            validate_contract()

        # Should detect 'validation' in message and use VALIDATION_ERROR code
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Contract validation failed" in exc_info.value.message

    def test_validation_error_handling_generic_exception_fallback(self):
        """Test non-validation exceptions get OPERATION_FAILED code."""

        @validation_error_handling("Data check")
        def check_data():
            raise RuntimeError("Database connection failed")

        with pytest.raises(ModelOnexError) as exc_info:
            check_data()

        # Generic errors should fall back to OPERATION_FAILED
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Data check failed" in exc_info.value.message

    def test_validation_error_handling_preserves_function_signature(self):
        """Test decorator preserves function signature."""

        @validation_error_handling("Email validation")
        def validate_email(email: str, strict: bool = False) -> bool:
            """Validate email format."""
            if strict and "@" not in email:
                raise ValueError("Invalid email format")
            return "@" in email

        # Should work normally
        assert validate_email("test@example.com") is True
        assert validate_email("test.example.com") is False

        # Should raise wrapped error in strict mode
        with pytest.raises(ModelOnexError):
            validate_email("invalid", strict=True)


class TestIOErrorHandling:
    """Test io_error_handling decorator."""

    def test_io_error_handling_success(self):
        """Test decorator allows successful I/O operation."""

        @io_error_handling("File reading")
        def read_data(data: str) -> str:
            return data.upper()

        result = read_data("hello")
        assert result == "HELLO"

    def test_io_error_handling_propagates_onex_error(self):
        """Test that ModelOnexError is re-raised without wrapping."""

        @io_error_handling("Database query")
        def query_database():
            raise ModelOnexError(
                "Query failed",
                error_code=EnumCoreErrorCode.DATABASE_QUERY_ERROR,
            )

        with pytest.raises(ModelOnexError) as exc_info:
            query_database()

        assert exc_info.value.message == "Query failed"
        assert exc_info.value.error_code == EnumCoreErrorCode.DATABASE_QUERY_ERROR

    def test_io_error_handling_file_not_found(self):
        """Test FileNotFoundError gets FILE_NOT_FOUND code."""

        @io_error_handling("Config file reading")
        def read_config():
            raise FileNotFoundError("config.yaml not found")

        with pytest.raises(ModelOnexError) as exc_info:
            read_config()

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND
        assert "Config file reading failed" in exc_info.value.message
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    def test_io_error_handling_is_a_directory_error(self):
        """Test IsADirectoryError gets FILE_OPERATION_ERROR code."""

        @io_error_handling("File reading")
        def read_file():
            raise IsADirectoryError("/path/to/directory")

        with pytest.raises(ModelOnexError) as exc_info:
            read_file()

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_OPERATION_ERROR
        assert "File reading failed" in exc_info.value.message
        assert isinstance(exc_info.value.__cause__, IsADirectoryError)

    def test_io_error_handling_permission_error(self):
        """Test PermissionError gets FILE_OPERATION_ERROR code."""

        @io_error_handling("Log file writing")
        def write_log():
            raise PermissionError("Permission denied: /var/log/app.log")

        with pytest.raises(ModelOnexError) as exc_info:
            write_log()

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_OPERATION_ERROR
        assert "Log file writing failed" in exc_info.value.message
        assert isinstance(exc_info.value.__cause__, PermissionError)

    def test_io_error_handling_generic_exception_fallback(self):
        """Test non-I/O exceptions get OPERATION_FAILED code."""

        @io_error_handling("Network request")
        def make_request():
            raise ValueError("Invalid URL format")

        with pytest.raises(ModelOnexError) as exc_info:
            make_request()

        # Generic errors should fall back to OPERATION_FAILED
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Network request failed" in exc_info.value.message

    def test_io_error_handling_custom_operation_name(self):
        """Test decorator with custom operation name."""

        @io_error_handling("Database connection initialization")
        def connect_db():
            raise ConnectionError("Cannot connect to database")

        with pytest.raises(ModelOnexError) as exc_info:
            connect_db()

        assert "Database connection initialization failed" in exc_info.value.message


class TestDecoratorStacking:
    """Test decorator composition and stacking."""

    def test_stacking_standard_and_validation(self):
        """Test stacking standard_error_handling with validation_error_handling."""

        # This pattern doesn't make practical sense but tests stacking behavior
        @standard_error_handling("Outer operation")
        @validation_error_handling("Inner validation")
        def double_decorated():
            raise ValueError("Test error")

        with pytest.raises(ModelOnexError) as exc_info:
            double_decorated()

        # Inner decorator wraps first, outer re-raises ModelOnexError
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Inner validation failed" in exc_info.value.message

    def test_multiple_standard_decorators(self):
        """Test multiple standard_error_handling decorators."""

        @standard_error_handling("Outer layer")
        @standard_error_handling("Inner layer")
        def multi_standard():
            raise TypeError("Type error")

        with pytest.raises(ModelOnexError) as exc_info:
            multi_standard()

        # Inner wraps first with "Inner layer failed"
        # Outer re-raises the ModelOnexError as-is
        assert "Inner layer failed" in exc_info.value.message


class TestErrorContextPreservation:
    """Test that error context is properly preserved."""

    def test_error_context_from_original_exception(self):
        """Test that original exception details are preserved in context."""

        @standard_error_handling("Processing")
        def process_data():
            try:
                result = 10 / 0
            except ZeroDivisionError as e:
                raise ValueError("Cannot process data with zero") from e

        with pytest.raises(ModelOnexError) as exc_info:
            process_data()

        # Verify the exception chain
        assert isinstance(exc_info.value.__cause__, ValueError)
        assert isinstance(exc_info.value.__cause__.__cause__, ZeroDivisionError)

    def test_error_message_includes_original_details(self):
        """Test that wrapped error message includes original error details."""

        @validation_error_handling("Schema validation")
        def validate_schema():
            raise ValueError(
                "Field 'email' is required and must be a valid email address"
            )

        with pytest.raises(ModelOnexError) as exc_info:
            validate_schema()

        # Error message should include original details
        assert "Schema validation failed" in exc_info.value.message
        assert "Field 'email' is required" in exc_info.value.message


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_decorator_with_class_method(self):
        """Test decorators work with class methods."""

        class DataProcessor:
            @standard_error_handling("Process method")
            def process(self, value: int) -> int:
                if value < 0:
                    raise ValueError("Negative values not allowed")
                return value * 2

        processor = DataProcessor()
        assert processor.process(5) == 10

        with pytest.raises(ModelOnexError) as exc_info:
            processor.process(-1)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_decorator_with_static_method(self):
        """Test decorators work with static methods."""

        class MathUtils:
            @staticmethod
            @standard_error_handling("Math operation")
            def divide(a: float, b: float) -> float:
                if b == 0:
                    raise ZeroDivisionError("Cannot divide by zero")
                return a / b

        assert MathUtils.divide(10, 2) == 5.0

        with pytest.raises(ModelOnexError) as exc_info:
            MathUtils.divide(10, 0)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_decorator_with_generator(self):
        """Test decorators work with generator functions."""

        @standard_error_handling("Generator operation")
        def generate_values(n: int):
            # Check happens inside generator
            for i in range(n):
                if i < 0:
                    raise ValueError("Negative value")
                yield i * 2

        # Generator creation and iteration should work
        gen = generate_values(3)
        assert list(gen) == [0, 2, 4]

        # Decorator wraps the generator function call itself
        gen2 = generate_values(5)
        assert callable(gen2.__next__)

    def test_decorator_with_none_return(self):
        """Test decorators handle functions returning None."""

        @standard_error_handling("Side effect operation")
        def side_effect_function() -> None:
            pass

        result = side_effect_function()
        assert result is None

    def test_empty_operation_name(self):
        """Test decorator with empty operation name."""

        @standard_error_handling("")
        def test_function():
            raise ValueError("Error")

        with pytest.raises(ModelOnexError) as exc_info:
            test_function()

        # Should still wrap error even with empty operation name
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert " failed: Error" in exc_info.value.message
