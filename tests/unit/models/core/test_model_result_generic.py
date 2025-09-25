"""
Unit tests for generic Result[T, E] pattern.

Tests the generic type parameter functionality, monadic operations,
and type safety of the Result implementation for CLI operations.
"""

from typing import Any

import pytest

from src.omnibase_core.models.infrastructure.model_result import (
    Result,
    collect_results,
    err,
    ok,
    try_result,
)


class TestResultGeneric:
    """Test cases for generic Result[T, E] functionality."""

    def test_result_ok_creation(self):
        """Test creating successful results with different types."""
        # String result
        str_result = Result.ok("success")
        assert str_result.is_ok()
        assert str_result.value == "success"
        assert str_result.error is None

        # Integer result
        int_result = Result.ok(42)
        assert int_result.is_ok()
        assert int_result.value == 42

        # Dict result
        dict_result = Result.ok({"key": "value"})
        assert dict_result.is_ok()
        assert dict_result.value == {"key": "value"}

        # List result
        list_result = Result.ok([1, 2, 3])
        assert list_result.is_ok()
        assert list_result.value == [1, 2, 3]

    def test_result_err_creation(self):
        """Test creating error results with different types."""
        # String error
        str_error = Result.err("error message")
        assert str_error.is_err()
        assert str_error.error == "error message"
        assert str_error.value is None

        # Exception error
        exc_error = Result.err(ValueError("invalid value"))
        assert exc_error.is_err()
        assert isinstance(exc_error.error, ValueError)
        assert str(exc_error.error) == "invalid value"

        # Custom error type
        custom_error = Result.err({"code": 404, "message": "Not found"})
        assert custom_error.is_err()
        assert custom_error.error == {"code": 404, "message": "Not found"}

    def test_result_unwrap_operations(self):
        """Test unwrap operations on results."""
        # Successful unwrap
        success = Result.ok("value")
        assert success.unwrap() == "value"

        # Failed unwrap should raise
        failure = Result.err("error")
        with pytest.raises(
            ValueError, match="Called unwrap\\(\\) on error result: error"
        ):
            failure.unwrap()

    def test_result_unwrap_or_operations(self):
        """Test unwrap_or operations on results."""
        # Successful unwrap_or
        success = Result.ok("value")
        assert success.unwrap_or("default") == "value"

        # Failed unwrap_or should return default
        failure = Result.err("error")
        assert failure.unwrap_or("default") == "default"

    def test_result_unwrap_or_else_operations(self):
        """Test unwrap_or_else operations on results."""
        # Successful unwrap_or_else
        success = Result.ok("value")
        assert success.unwrap_or_else(lambda e: f"error: {e}") == "value"

        # Failed unwrap_or_else should compute from error
        failure = Result.err("original error")
        assert (
            failure.unwrap_or_else(lambda e: f"handled: {e}")
            == "handled: original error"
        )

    def test_result_expect_operations(self):
        """Test expect operations on results."""
        # Successful expect
        success = Result.ok("value")
        assert success.expect("Should not fail") == "value"

        # Failed expect should raise with custom message
        failure = Result.err("original error")
        with pytest.raises(ValueError, match="Custom error message: original error"):
            failure.expect("Custom error message")

    def test_result_map_operations(self):
        """Test map operations on results."""
        # Map on success
        success = Result.ok(5)
        mapped = success.map(lambda x: x * 2)
        assert mapped.is_ok()
        assert mapped.unwrap() == 10

        # Map on error should preserve error
        failure = Result.err("error")
        mapped = failure.map(lambda x: x * 2)
        assert mapped.is_err()
        assert mapped.error == "error"

        # Map with exception should convert to error
        success = Result.ok("text")
        mapped = success.map(lambda x: int(x))  # Will raise ValueError
        assert mapped.is_err()
        assert isinstance(mapped.error, ValueError)

    def test_result_map_err_operations(self):
        """Test map_err operations on results."""
        # Map_err on success should preserve success
        success = Result.ok("value")
        mapped = success.map_err(lambda e: f"mapped: {e}")
        assert mapped.is_ok()
        assert mapped.unwrap() == "value"

        # Map_err on error should transform error
        failure = Result.err("original error")
        mapped = failure.map_err(lambda e: f"transformed: {e}")
        assert mapped.is_err()
        assert mapped.error == "transformed: original error"

    def test_result_and_then_operations(self):
        """Test and_then (flat map) operations on results."""

        def divide_by_two(x: int) -> Result[int, str]:
            if x % 2 == 0:
                return Result.ok(x // 2)
            else:
                return Result.err("Not divisible by 2")

        # Chain on success
        success = Result.ok(10)
        chained = success.and_then(divide_by_two)
        assert chained.is_ok()
        assert chained.unwrap() == 5

        # Chain on success but operation fails
        success = Result.ok(7)
        chained = success.and_then(divide_by_two)
        assert chained.is_err()
        assert chained.error == "Not divisible by 2"

        # Chain on error should preserve error
        failure = Result.err("original error")
        chained = failure.and_then(divide_by_two)
        assert chained.is_err()
        assert chained.error == "original error"

    def test_result_or_else_operations(self):
        """Test or_else operations on results."""

        def recover_from_error(e: str) -> Result[str, str]:
            if "recoverable" in e:
                return Result.ok("recovered")
            else:
                return Result.err(f"unrecoverable: {e}")

        # or_else on success should preserve success
        success = Result.ok("value")
        recovered = success.or_else(recover_from_error)
        assert recovered.is_ok()
        assert recovered.unwrap() == "value"

        # or_else on recoverable error
        failure = Result.err("recoverable error")
        recovered = failure.or_else(recover_from_error)
        assert recovered.is_ok()
        assert recovered.unwrap() == "recovered"

        # or_else on unrecoverable error
        failure = Result.err("fatal error")
        recovered = failure.or_else(recover_from_error)
        assert recovered.is_err()
        assert recovered.error == "unrecoverable: fatal error"

    def test_result_boolean_conversion(self):
        """Test boolean conversion of results."""
        success = Result.ok("value")
        failure = Result.err("error")

        assert bool(success) is True
        assert bool(failure) is False

        # Can be used in conditionals
        if success:
            assert True
        else:
            assert False, "Should not reach here"

        if failure:
            assert False, "Should not reach here"
        else:
            assert True

    def test_result_string_representations(self):
        """Test string representations of results."""
        success = Result.ok("value")
        failure = Result.err("error")

        assert repr(success) == "Result.ok('value')"
        assert repr(failure) == "Result.err('error')"

        assert str(success) == "Success: value"
        assert str(failure) == "Error: error"

    def test_result_explicit_generic_types(self):
        """Test explicit generic types following ONEX conventions."""
        # Result[str, str] - String success, string error
        str_success: Result[str, str] = Result.ok("success")
        str_failure: Result[str, str] = Result.err("error")

        assert str_success.unwrap() == "success"
        assert str_failure.error == "error"

        # Result[bool, str] - Boolean success, string error
        bool_success: Result[bool, str] = Result.ok(True)
        bool_failure: Result[bool, str] = Result.err("validation failed")

        assert bool_success.unwrap() is True
        assert bool_failure.error == "validation failed"

        # Result[int, str] - Integer success, string error
        int_success: Result[int, str] = Result.ok(42)
        int_failure: Result[int, str] = Result.err("parse error")

        assert int_success.unwrap() == 42
        assert int_failure.error == "parse error"

        # Result[dict[str, str], str] - Dictionary success, string error
        data_success: Result[dict[str, str], str] = Result.ok({"key": "value"})
        data_failure: Result[dict[str, str], str] = Result.err("invalid format")

        assert data_success.unwrap() == {"key": "value"}
        assert data_failure.error == "invalid format"

        # Result[list[int], str] - List success, string error
        list_success: Result[list[int], str] = Result.ok([1, 2, 3])
        list_failure: Result[list[int], str] = Result.err("empty list")

        assert list_success.unwrap() == [1, 2, 3]
        assert list_failure.error == "empty list"

    def test_result_factory_functions(self):
        """Test global factory functions."""
        # ok function
        success = ok("value")
        assert success.is_ok()
        assert success.unwrap() == "value"

        # err function
        failure = err("error")
        assert failure.is_err()
        assert failure.error == "error"

    def test_try_result_function(self):
        """Test try_result function for exception handling."""

        # Successful operation
        def successful_operation():
            return 42

        result = try_result(successful_operation)
        assert result.is_ok()
        assert result.unwrap() == 42

        # Failing operation
        def failing_operation():
            raise ValueError("operation failed")

        result = try_result(failing_operation)
        assert result.is_err()
        assert isinstance(result.error, ValueError)
        assert str(result.error) == "operation failed"

    def test_collect_results_function(self):
        """Test collect_results function for combining results."""
        # All successful results
        results = [Result.ok(1), Result.ok(2), Result.ok(3)]
        collected = collect_results(results)
        assert collected.is_ok()
        assert collected.unwrap() == [1, 2, 3]

        # Some failed results
        results = [
            Result.ok(1),
            Result.err("error1"),
            Result.ok(3),
            Result.err("error2"),
        ]
        collected = collect_results(results)
        assert collected.is_err()
        assert collected.error == ["error1", "error2"]

        # All failed results
        results = [Result.err("error1"), Result.err("error2")]
        collected = collect_results(results)
        assert collected.is_err()
        assert collected.error == ["error1", "error2"]

        # Empty list
        results = []
        collected = collect_results(results)
        assert collected.is_ok()
        assert collected.unwrap() == []

    def test_result_pydantic_validation(self):
        """Test Pydantic validation with Result."""
        # Valid success result
        success = Result.ok("value")
        assert success.success is True
        assert success.value == "value"
        assert success.error is None

        # Valid error result
        failure = Result.err("error")
        assert failure.success is False
        assert failure.value is None
        assert failure.error == "error"

    def test_result_validation_errors(self):
        """Test Result validation edge cases."""
        # These should raise validation errors during initialization
        with pytest.raises(ValueError, match="Success result must have a value"):
            Result(success=True, value=None, error=None)

        with pytest.raises(ValueError, match="Error result must have an error"):
            Result(success=False, value=None, error=None)

        with pytest.raises(ValueError, match="Success result cannot have an error"):
            Result(success=True, value="value", error="error")

        with pytest.raises(ValueError, match="Error result cannot have a value"):
            Result(success=False, value="value", error="error")


class TestResultGenericComplexTypes:
    """Test Result with complex generic types."""

    def test_result_with_nested_generics(self):
        """Test Result with nested generic types."""
        # Result[dict[str, list[int]], str]
        complex_data = {"numbers": [1, 2, 3], "values": [10, 20, 30]}
        result = Result.ok(complex_data)

        assert result.is_ok()
        assert result.unwrap() == complex_data

        # Map operation should preserve type structure
        mapped = result.map(lambda d: {k: [x * 2 for x in v] for k, v in d.items()})
        expected = {"numbers": [2, 4, 6], "values": [20, 40, 60]}
        assert mapped.unwrap() == expected

    def test_result_chaining_with_complex_types(self):
        """Test chaining operations with complex types."""

        def parse_config(data: dict[str, Any]) -> Result[dict[str, int], str]:
            try:
                return Result.ok({k: int(v) for k, v in data.items()})
            except (ValueError, TypeError):
                return Result.err("Invalid configuration format")

        def validate_config(config: dict[str, int]) -> Result[dict[str, int], str]:
            if all(v > 0 for v in config.values()):
                return Result.ok(config)
            else:
                return Result.err("All values must be positive")

        # Successful chain
        input_data = {"timeout": "30", "retries": "3"}
        result = Result.ok(input_data).and_then(parse_config).and_then(validate_config)

        assert result.is_ok()
        assert result.unwrap() == {"timeout": 30, "retries": 3}

        # Failed parsing
        input_data = {"timeout": "invalid", "retries": "3"}
        result = Result.ok(input_data).and_then(parse_config).and_then(validate_config)

        assert result.is_err()
        assert result.error == "Invalid configuration format"

        # Failed validation
        input_data = {"timeout": "-1", "retries": "3"}
        result = Result.ok(input_data).and_then(parse_config).and_then(validate_config)

        assert result.is_err()
        assert result.error == "All values must be positive"

    def test_result_with_custom_classes(self):
        """Test Result with custom class types."""

        class Config:
            def __init__(self, name: str, value: int):
                self.name = name
                self.value = value

            def __eq__(self, other):
                return (
                    isinstance(other, Config)
                    and self.name == other.name
                    and self.value == other.value
                )

        # Success with custom class
        config = Config("test", 42)
        result = Result.ok(config)

        assert result.is_ok()
        assert result.unwrap() == config
        assert result.unwrap().name == "test"
        assert result.unwrap().value == 42

        # Map with custom class
        mapped = result.map(lambda c: Config(c.name.upper(), c.value * 2))
        assert mapped.unwrap().name == "TEST"
        assert mapped.unwrap().value == 84


class TestResultGenericEdgeCases:
    """Test edge cases for generic Result[T, E]."""

    def test_result_with_none_values(self):
        """Test Result behavior with None values."""
        # Note: Our Result implementation doesn't allow None as success value
        # This is a design choice to ensure explicit values
        with pytest.raises(ValueError, match="Success result must have a value"):
            Result.ok(None)

        # None as error value is also not allowed in our implementation
        with pytest.raises(ValueError, match="Error result must have an error"):
            Result.err(None)

    def test_result_recursive_operations(self):
        """Test recursive operations with Results."""

        def factorial(n: int) -> Result[int, str]:
            if n < 0:
                return Result.err("Negative numbers not supported")
            elif n == 0 or n == 1:
                return Result.ok(1)
            else:
                prev_result = factorial(n - 1)
                return prev_result.map(lambda x: x * n)

        # Successful recursion
        result = factorial(5)
        assert result.is_ok()
        assert result.unwrap() == 120

        # Failed recursion
        result = factorial(-1)
        assert result.is_err()
        assert result.error == "Negative numbers not supported"

    def test_result_exception_in_operations(self):
        """Test exception handling in Result operations."""
        success = Result.ok("test")

        # Exception in map should convert to error
        mapped = success.map(lambda x: x / 0)  # TypeError (str / int)
        assert mapped.is_err()
        assert isinstance(mapped.error, TypeError)

        # Exception in and_then should convert to error
        def failing_operation(x):
            raise RuntimeError("Operation failed")

        chained = success.and_then(failing_operation)
        assert chained.is_err()
        assert isinstance(chained.error, RuntimeError)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
