# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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

Target: 90%+ coverage for decorators/decorator_error_handling.py
"""

import pytest

from omnibase_core.decorators.decorator_error_handling import (
    io_error_handling,
    standard_error_handling,
    validation_error_handling,
)
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
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

        # Inner decorator wraps first with VALIDATION_ERROR (ValueError is a validation error)
        # Outer decorator re-raises ModelOnexError as-is, preserving the error code
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
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


@pytest.mark.unit
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


@pytest.mark.unit
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


@pytest.mark.unit
class TestAsyncStandardErrorHandling:
    """Test standard_error_handling decorator with async functions."""

    @pytest.mark.asyncio
    async def test_async_standard_error_handling_success(self):
        """Test decorator allows successful async execution."""
        import asyncio

        @standard_error_handling("Async operation")
        async def async_successful_function(value: int) -> int:
            await asyncio.sleep(0.001)
            return value * 2

        result = await async_successful_function(5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_async_standard_error_handling_wraps_exception(self):
        """Test that exceptions in async functions are wrapped."""
        import asyncio

        @standard_error_handling("Async data processing")
        async def async_raises_error():
            await asyncio.sleep(0.001)
            raise ValueError("Async invalid data")

        with pytest.raises(ModelOnexError) as exc_info:
            await async_raises_error()

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "Async data processing failed" in exc_info.value.message
        assert "Async invalid data" in exc_info.value.message
        assert isinstance(exc_info.value.__cause__, ValueError)

    @pytest.mark.asyncio
    async def test_async_standard_error_handling_propagates_onex_error(self):
        """Test that ModelOnexError is re-raised without wrapping in async."""
        import asyncio

        @standard_error_handling("Async operation")
        async def async_raises_onex_error():
            await asyncio.sleep(0.001)
            raise ModelOnexError(
                "Original async ONEX error",
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            )

        with pytest.raises(ModelOnexError) as exc_info:
            await async_raises_onex_error()

        assert exc_info.value.message == "Original async ONEX error"
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_async_standard_error_handling_propagates_cancelled_error(self):
        """Test that CancelledError is always re-raised in async."""
        import asyncio

        @standard_error_handling("Async cancellation test")
        async def async_raises_cancelled():
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await async_raises_cancelled()

    @pytest.mark.asyncio
    async def test_async_standard_error_handling_preserves_function_metadata(self):
        """Test that decorator preserves async function name and docstring."""

        @standard_error_handling("Test")
        async def async_documented_function():
            """This is an async test function."""
            return "result"

        assert async_documented_function.__name__ == "async_documented_function"
        assert async_documented_function.__doc__ == "This is an async test function."

    @pytest.mark.asyncio
    async def test_async_wrapper_is_coroutine_function(self):
        """Test that decorated async functions remain coroutine functions."""
        import asyncio

        @standard_error_handling("Async operation")
        async def async_func():
            return "result"

        assert asyncio.iscoroutinefunction(async_func)


@pytest.mark.unit
class TestAsyncValidationErrorHandling:
    """Test validation_error_handling decorator with async functions."""

    @pytest.mark.asyncio
    async def test_async_validation_error_handling_success(self):
        """Test decorator allows successful async validation."""
        import asyncio

        @validation_error_handling("Async user validation")
        async def async_validate_user(username: str) -> bool:
            await asyncio.sleep(0.001)
            return len(username) >= 3

        result = await async_validate_user("john")
        assert result is True

    @pytest.mark.asyncio
    async def test_async_validation_error_handling_wraps_validation_error(self):
        """Test that validation errors get VALIDATION_ERROR code in async."""
        import asyncio

        class ValidationError(Exception):
            def __init__(self, message: str):
                super().__init__(message)
                self.errors = [{"field": "email", "error": "invalid"}]

        @validation_error_handling("Async email validation")
        async def async_validate_with_errors():
            await asyncio.sleep(0.001)
            raise ValidationError("Email validation failed")

        with pytest.raises(ModelOnexError) as exc_info:
            await async_validate_with_errors()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Async email validation failed" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_async_validation_error_handling_detects_validation_in_message(self):
        """Test 'validation' in message triggers VALIDATION_ERROR code in async."""
        import asyncio

        @validation_error_handling("Async contract validation")
        async def async_validate_contract():
            await asyncio.sleep(0.001)
            raise ValueError("Validation of async contract field failed")

        with pytest.raises(ModelOnexError) as exc_info:
            await async_validate_contract()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    @pytest.mark.asyncio
    async def test_async_validation_error_handling_propagates_cancelled_error(self):
        """Test that CancelledError is always re-raised in async validation."""
        import asyncio

        @validation_error_handling("Async validation")
        async def async_validation_cancelled():
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await async_validation_cancelled()


@pytest.mark.unit
class TestAsyncIOErrorHandling:
    """Test io_error_handling decorator with async functions."""

    @pytest.mark.asyncio
    async def test_async_io_error_handling_success(self):
        """Test decorator allows successful async I/O operation."""
        import asyncio

        @io_error_handling("Async file reading")
        async def async_read_data(data: str) -> str:
            await asyncio.sleep(0.001)
            return data.upper()

        result = await async_read_data("hello")
        assert result == "HELLO"

    @pytest.mark.asyncio
    async def test_async_io_error_handling_file_not_found(self):
        """Test async FileNotFoundError gets FILE_NOT_FOUND code."""
        import asyncio

        @io_error_handling("Async config file reading")
        async def async_read_config():
            await asyncio.sleep(0.001)
            raise FileNotFoundError("async_config.yaml not found")

        with pytest.raises(ModelOnexError) as exc_info:
            await async_read_config()

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_NOT_FOUND
        assert "Async config file reading failed" in exc_info.value.message
        assert isinstance(exc_info.value.__cause__, FileNotFoundError)

    @pytest.mark.asyncio
    async def test_async_io_error_handling_permission_error(self):
        """Test async PermissionError gets FILE_OPERATION_ERROR code."""
        import asyncio

        @io_error_handling("Async log file writing")
        async def async_write_log():
            await asyncio.sleep(0.001)
            raise PermissionError("Permission denied: /var/log/async_app.log")

        with pytest.raises(ModelOnexError) as exc_info:
            await async_write_log()

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_OPERATION_ERROR
        assert "Async log file writing failed" in exc_info.value.message
        assert isinstance(exc_info.value.__cause__, PermissionError)

    @pytest.mark.asyncio
    async def test_async_io_error_handling_is_a_directory_error(self):
        """Test async IsADirectoryError gets FILE_OPERATION_ERROR code."""
        import asyncio

        @io_error_handling("Async file reading")
        async def async_read_file():
            await asyncio.sleep(0.001)
            raise IsADirectoryError("/path/to/async_directory")

        with pytest.raises(ModelOnexError) as exc_info:
            await async_read_file()

        assert exc_info.value.error_code == EnumCoreErrorCode.FILE_OPERATION_ERROR
        assert isinstance(exc_info.value.__cause__, IsADirectoryError)

    @pytest.mark.asyncio
    async def test_async_io_error_handling_generic_exception_fallback(self):
        """Test async non-I/O exceptions get OPERATION_FAILED code."""
        import asyncio

        @io_error_handling("Async network request")
        async def async_make_request():
            await asyncio.sleep(0.001)
            raise ValueError("Invalid async URL format")

        with pytest.raises(ModelOnexError) as exc_info:
            await async_make_request()

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    @pytest.mark.asyncio
    async def test_async_io_error_handling_propagates_cancelled_error(self):
        """Test that CancelledError is always re-raised in async I/O."""
        import asyncio

        @io_error_handling("Async file operation")
        async def async_io_cancelled():
            raise asyncio.CancelledError

        with pytest.raises(asyncio.CancelledError):
            await async_io_cancelled()

    @pytest.mark.asyncio
    async def test_async_io_error_handling_propagates_onex_error(self):
        """Test that ModelOnexError is re-raised without wrapping in async I/O."""
        import asyncio

        @io_error_handling("Async database query")
        async def async_query_database():
            await asyncio.sleep(0.001)
            raise ModelOnexError(
                "Async query failed",
                error_code=EnumCoreErrorCode.DATABASE_QUERY_ERROR,
            )

        with pytest.raises(ModelOnexError) as exc_info:
            await async_query_database()

        assert exc_info.value.message == "Async query failed"
        assert exc_info.value.error_code == EnumCoreErrorCode.DATABASE_QUERY_ERROR


@pytest.mark.unit
class TestAsyncDecoratorEdgeCases:
    """Test edge cases for async decorator behavior."""

    @pytest.mark.asyncio
    async def test_sync_function_remains_sync(self):
        """Test that sync functions decorated remain sync (not async)."""
        import asyncio

        @standard_error_handling("Sync operation")
        def sync_func():
            return "sync result"

        # Should NOT be a coroutine function
        assert not asyncio.iscoroutinefunction(sync_func)
        result = sync_func()
        assert result == "sync result"

    @pytest.mark.asyncio
    async def test_async_decorator_with_class_method(self):
        """Test async decorators work with async class methods."""
        import asyncio

        class AsyncDataProcessor:
            @standard_error_handling("Async process method")
            async def process(self, value: int) -> int:
                await asyncio.sleep(0.001)
                if value < 0:
                    raise ValueError("Negative values not allowed")
                return value * 2

        processor = AsyncDataProcessor()
        assert await processor.process(5) == 10

        with pytest.raises(ModelOnexError) as exc_info:
            await processor.process(-1)

        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    @pytest.mark.asyncio
    async def test_async_decorator_stacking(self):
        """Test stacking decorators with async functions."""

        @standard_error_handling("Outer async")
        @validation_error_handling("Inner async validation")
        async def double_decorated_async():
            raise ValueError("Async test error")

        with pytest.raises(ModelOnexError) as exc_info:
            await double_decorated_async()

        # Inner decorator wraps first
        assert "Inner async validation failed" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_async_propagates_keyboard_interrupt(self):
        """Test that KeyboardInterrupt is always propagated in async."""
        import asyncio

        @standard_error_handling("Async keyboard test")
        async def async_keyboard_interrupt():
            await asyncio.sleep(0.001)
            raise KeyboardInterrupt

        with pytest.raises(KeyboardInterrupt):
            await async_keyboard_interrupt()

    @pytest.mark.asyncio
    async def test_async_propagates_system_exit(self):
        """Test that SystemExit is always propagated in async."""
        import asyncio

        @standard_error_handling("Async system exit test")
        async def async_system_exit():
            await asyncio.sleep(0.001)
            raise SystemExit(1)

        with pytest.raises(SystemExit):
            await async_system_exit()

    @pytest.mark.asyncio
    async def test_async_propagates_generator_exit(self):
        """Test that GeneratorExit is always propagated in async."""

        @standard_error_handling("Async generator exit test")
        async def async_generator_exit():
            raise GeneratorExit

        with pytest.raises(GeneratorExit):
            await async_generator_exit()


@pytest.mark.unit
class TestValidationErrorDetection:
    """Test the validation error detection heuristics."""

    def test_pydantic_style_error_with_error_count_detected(self):
        """Test that exceptions with Pydantic-style error_count() are detected."""

        class PydanticStyleError(Exception):
            """Mock Pydantic-style error with error_count method."""

            def __init__(self, message: str):
                super().__init__(message)
                self._errors = [
                    {"loc": ("field",), "msg": "error", "type": "value_error"}
                ]

            def errors(self):
                return self._errors

            def error_count(self):
                return len(self._errors)

        @validation_error_handling("Pydantic-style validation")
        def raises_pydantic_style():
            raise PydanticStyleError("Validation failed")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_pydantic_style()

        # Should be detected as validation error via error_count() method
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_error_with_only_error_count_detected(self):
        """Test that exceptions with only error_count() are detected."""

        class ErrorCountOnlyError(Exception):
            """Error with error_count but no errors method."""

            def error_count(self):
                return 1

        @validation_error_handling("Error count validation")
        def raises_error_count_only():
            raise ErrorCountOnlyError("Has error count")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_error_count_only()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_validation_timeout_error_not_detected_as_validation(self):
        """Test that ValidationTimeoutError is NOT detected as validation error."""

        class ValidationTimeoutError(Exception):
            """Timeout during validation - NOT a validation error."""

        @validation_error_handling("Validation with timeout")
        def raises_validation_timeout():
            raise ValidationTimeoutError("Validation timed out")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_validation_timeout()

        # Should NOT be detected as validation error (denylist)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_validation_cancelled_error_not_detected_as_validation(self):
        """Test that ValidationCancelledError is NOT detected as validation error."""

        class ValidationCancelledError(Exception):
            """Validation was cancelled - NOT a validation error."""

        @validation_error_handling("Cancelled validation")
        def raises_validation_cancelled():
            raise ValidationCancelledError("Validation was cancelled")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_validation_cancelled()

        # Should NOT be detected as validation error (denylist)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_schema_validation_error_detected(self):
        """Test that SchemaValidationError IS detected (not in denylist)."""

        class SchemaValidationError(Exception):
            """Schema validation failed - IS a validation error."""

        @validation_error_handling("Schema validation")
        def raises_schema_validation():
            raise SchemaValidationError("Schema invalid")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_schema_validation()

        # Should be detected as validation error (not in denylist)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_input_validation_exception_detected(self):
        """Test that InputValidationException IS detected (not in denylist)."""

        class InputValidationException(Exception):
            """Input validation failed - IS a validation error."""

        @validation_error_handling("Input validation")
        def raises_input_validation():
            raise InputValidationException("Invalid input")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_input_validation()

        # Should be detected as validation error (not in denylist)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_error_with_non_callable_error_count_not_detected(self):
        """Test that non-callable error_count attribute doesn't trigger detection."""

        class BadErrorCount(Exception):
            """Error with error_count as non-callable attribute."""

            def __init__(self, message: str):
                super().__init__(message)
                self.error_count = 5  # Not callable

        @validation_error_handling("Bad error count")
        def raises_bad_error_count():
            raise BadErrorCount("Has error_count attribute")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_bad_error_count()

        # Should NOT be detected as validation error (error_count not callable)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_error_with_error_count_returning_non_int_not_detected(self):
        """Test that error_count() returning non-int doesn't trigger detection."""

        class WeirdErrorCount(Exception):
            """Error with error_count returning wrong type."""

            def error_count(self):
                return "many"  # Not an int

        @validation_error_handling("Weird error count")
        def raises_weird_error_count():
            raise WeirdErrorCount("Has weird error_count")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_weird_error_count()

        # Should NOT be detected as validation error (error_count returns string)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_error_with_throwing_error_count_not_detected(self):
        """Test that error_count() that throws doesn't trigger detection."""

        class ThrowingErrorCount(Exception):
            """Error with error_count that throws."""

            def error_count(self):
                raise RuntimeError("Cannot count errors")

        @validation_error_handling("Throwing error count")
        def raises_throwing_error_count():
            raise ThrowingErrorCount("Has throwing error_count")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_throwing_error_count()

        # Should NOT be detected as validation error (error_count throws)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_pydantic_errors_structure_with_input_key(self):
        """Test that errors() with Pydantic v2 structure including 'input' key works."""

        class PydanticV2StyleError(Exception):
            """Mock Pydantic v2 error with full error structure."""

            def errors(self):
                return [
                    {
                        "type": "string_type",
                        "loc": ("name",),
                        "msg": "Input should be a valid string",
                        "input": 123,
                        "url": "https://errors.pydantic.dev/2.12/v/string_type",
                    }
                ]

        @validation_error_handling("Pydantic v2 style")
        def raises_pydantic_v2():
            raise PydanticV2StyleError("Full Pydantic v2 structure")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_pydantic_v2()

        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_errors_returning_empty_list_detected(self):
        """Test that errors() returning empty list is detected as validation error."""

        class EmptyErrorsError(Exception):
            """Error with errors() returning empty list."""

            def errors(self):
                return []

        @validation_error_handling("Empty errors")
        def raises_empty_errors():
            raise EmptyErrorsError("No errors yet")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_empty_errors()

        # Empty errors list is valid Pydantic structure
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_errors_returning_non_list_not_detected(self):
        """Test that errors() returning non-list doesn't trigger detection."""

        class NonListErrors(Exception):
            """Error with errors() returning dict."""

            def errors(self):
                return {"field": "error"}

        @validation_error_handling("Non-list errors")
        def raises_non_list_errors():
            raise NonListErrors("Has non-list errors")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_non_list_errors()

        # Dict is not valid Pydantic structure
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_errors_with_missing_required_keys_not_detected(self):
        """Test that errors() with missing required keys doesn't trigger detection."""

        class PartialErrors(Exception):
            """Error with errors() missing required Pydantic keys."""

            def errors(self):
                # Missing 'type' key
                return [{"loc": ("field",), "msg": "error"}]

        @validation_error_handling("Partial errors")
        def raises_partial_errors():
            raise PartialErrors("Has partial errors")

        with pytest.raises(ModelOnexError) as exc_info:
            raises_partial_errors()

        # Missing 'type' key means not Pydantic structure
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
