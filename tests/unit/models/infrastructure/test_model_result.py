"""
Tests for ModelResult pattern.

Validates Result[T, E] functionality including creation, validation, monadic operations,
error handling, serialization, and utility functions following ONEX testing standards.
"""

import json
from typing import Any
from unittest.mock import Mock

import pytest

from omnibase_core.models.errors.model_onex_error import ModelOnexError as OnexError
from omnibase_core.models.infrastructure.model_result import (
    ModelResult,
    collect_results,
    err,
    ok,
    try_result,
)


class TestModelResultCreation:
    """Test basic Result creation patterns."""

    def test_ok_creation_class_method(self):
        """Test creating successful result using class method."""
        result = ModelResult.ok("success_value")

        assert result.success is True
        assert result.value == "success_value"
        assert result.error is None
        assert result.is_ok() is True
        assert result.is_err() is False

    def test_err_creation_class_method(self):
        """Test creating error result using class method."""
        result = ModelResult.err("error_message")

        assert result.success is False
        assert result.value is None
        assert result.error == "error_message"
        assert result.is_ok() is False
        assert result.is_err() is True

    def test_constructor_success_valid(self):
        """Test constructor with valid success parameters."""
        result = ModelResult(success=True, value=42, error=None)

        assert result.success is True
        assert result.value == 42
        assert result.error is None

    def test_constructor_error_valid(self):
        """Test constructor with valid error parameters."""
        result = ModelResult(success=False, value=None, error="failed")

        assert result.success is False
        assert result.value is None
        assert result.error == "failed"

    def test_constructor_success_without_value_fails(self):
        """Test constructor validation: success result must have value."""
        with pytest.raises(OnexError) as exc_info:
            ModelResult(success=True, value=None, error=None)

        assert "Success result must have a value" in str(exc_info.value)

    def test_constructor_error_without_error_fails(self):
        """Test constructor validation: error result must have error."""
        with pytest.raises(OnexError) as exc_info:
            ModelResult(success=False, value=None, error=None)

        assert "Error result must have an error" in str(exc_info.value)

    def test_constructor_success_with_error_fails(self):
        """Test constructor validation: success result cannot have error."""
        with pytest.raises(OnexError) as exc_info:
            ModelResult(success=True, value="value", error="error")

        assert "Success result cannot have an error" in str(exc_info.value)

    def test_constructor_error_with_value_fails(self):
        """Test constructor validation: error result cannot have value."""
        with pytest.raises(OnexError) as exc_info:
            ModelResult(success=False, value="value", error="error")

        assert "Error result cannot have a value" in str(exc_info.value)

    def test_ok_with_various_types(self):
        """Test ok() with different value types."""
        int_result = ModelResult.ok(42)
        assert int_result.value == 42

        str_result = ModelResult.ok("test")
        assert str_result.value == "test"

        list_result = ModelResult.ok([1, 2, 3])
        assert list_result.value == [1, 2, 3]

        dict_result = ModelResult.ok({"key": "value"})
        assert dict_result.value == {"key": "value"}

        # None is no longer allowed for success results in ONEX compliance
        # Use a different value type instead
        empty_string_result = ModelResult.ok("")
        assert empty_string_result.value == ""

    def test_err_with_various_types(self):
        """Test err() with different error types."""
        str_err = ModelResult.err("string error")
        assert str_err.error == "string error"

        int_err = ModelResult.err(404)
        assert str_err.error == "string error"

        exception_err = ModelResult.err(ValueError("validation failed"))
        assert isinstance(exception_err.error, str)
        assert exception_err.error == "validation failed"

        dict_err = ModelResult.err({"code": "E001", "message": "Error occurred"})
        # Use safe dictionary access with isinstance check
        assert isinstance(dict_err.error, dict)
        assert dict_err.error.get("code") == "E001"


class TestModelResultUnwrapping:
    """Test value unwrapping methods."""

    def test_unwrap_success(self):
        """Test unwrapping successful result."""
        result = ModelResult.ok("test_value")
        value = result.unwrap()

        assert value == "test_value"

    def test_unwrap_error_fails(self):
        """Test unwrapping error result fails."""
        result = ModelResult.err("error_message")

        with pytest.raises(OnexError) as exc_info:
            result.unwrap()

        assert "Called unwrap() on error result: error_message" in str(exc_info.value)

    def test_unwrap_or_success(self):
        """Test unwrap_or with successful result."""
        result = ModelResult.ok("actual_value")
        value = result.unwrap_or("default_value")

        assert value == "actual_value"

    def test_unwrap_or_error(self):
        """Test unwrap_or with error result."""
        result = ModelResult.err("some_error")
        value = result.unwrap_or("default_value")

        assert value == "default_value"

    def test_unwrap_or_else_success(self):
        """Test unwrap_or_else with successful result."""
        result = ModelResult.ok("actual_value")
        value = result.unwrap_or_else(lambda err: f"recovered_from_{err}")

        assert value == "actual_value"

    def test_unwrap_or_else_error(self):
        """Test unwrap_or_else with error result."""
        result = ModelResult.err("original_error")
        value = result.unwrap_or_else(lambda err: f"recovered_from_{err}")

        assert value == "recovered_from_original_error"

    def test_expect_success(self):
        """Test expect with successful result."""
        result = ModelResult.ok(100)
        value = result.expect("Should have succeeded")

        assert value == 100

    def test_expect_error_fails(self):
        """Test expect with error result fails."""
        result = ModelResult.err("failure")

        with pytest.raises(OnexError) as exc_info:
            result.expect("Expected success but got")

        assert "Expected success but got: failure" in str(exc_info.value)


class TestModelResultMonadicOperations:
    """Test monadic operations (map, and_then, or_else)."""

    def test_map_success(self):
        """Test mapping function over successful result."""
        result = ModelResult.ok(10)
        mapped = result.map(lambda x: x * 2)

        assert mapped.is_ok()
        assert mapped.unwrap() == 20

    def test_map_error_passthrough(self):
        """Test mapping over error result passes through error."""
        result = ModelResult.err("original_error")
        mapped = result.map(lambda x: x * 2)

        assert mapped.is_err()
        assert mapped.error == "original_error"

    def test_map_function_exception(self):
        """Test mapping function that raises exception."""
        result = ModelResult.ok("not_a_number")
        mapped = result.map(lambda x: int(x))  # Will raise ValueError

        assert mapped.is_err()
        assert isinstance(mapped.error, str)
        assert "invalid literal" in mapped.error

    def test_map_chaining(self):
        """Test chaining multiple map operations."""
        result = ModelResult.ok(5)
        chained = result.map(lambda x: x * 2).map(lambda x: x + 1).map(lambda x: str(x))

        assert chained.is_ok()
        assert chained.unwrap() == "11"

    def test_map_err_success_passthrough(self):
        """Test map_err over successful result passes through value."""
        result = ModelResult.ok("success_value")
        mapped = result.map_err(lambda err: f"transformed_{err}")

        assert mapped.is_ok()
        assert mapped.unwrap() == "success_value"

    def test_map_err_error(self):
        """Test mapping function over error."""
        result = ModelResult.err("original_error")
        mapped = result.map_err(lambda err: f"transformed_{err}")

        assert mapped.is_err()
        assert mapped.error == "transformed_original_error"

    def test_map_err_function_exception(self):
        """Test map_err function that raises exception."""
        result = ModelResult.err("error")

        def failing_mapper(err: str) -> str:
            raise RuntimeError("Mapper failed")

        mapped = result.map_err(failing_mapper)

        assert mapped.is_err()
        assert isinstance(mapped.error, str)
        assert mapped.error == "Mapper failed"

    def test_and_then_success(self):
        """Test and_then (bind) with successful result."""
        result = ModelResult.ok(10)

        def double_if_positive(x: int) -> ModelResult[int, str]:
            if x > 0:
                return ModelResult.ok(x * 2)
            return ModelResult.err("Value must be positive")

        chained = result.and_then(double_if_positive)

        assert chained.is_ok()
        assert chained.unwrap() == 20

    def test_and_then_success_to_error(self):
        """Test and_then that converts success to error."""
        result = ModelResult.ok(-5)

        def double_if_positive(x: int) -> ModelResult[int, str]:
            if x > 0:
                return ModelResult.ok(x * 2)
            return ModelResult.err("Value must be positive")

        chained = result.and_then(double_if_positive)

        assert chained.is_err()
        assert chained.error == "Value must be positive"

    def test_and_then_error_passthrough(self):
        """Test and_then with error result passes through error."""
        result = ModelResult.err("original_error")

        def should_not_be_called(x: Any) -> ModelResult[Any, str]:
            assert False, "This should not be called"

        chained = result.and_then(should_not_be_called)

        assert chained.is_err()
        assert chained.error == "original_error"

    def test_and_then_function_exception(self):
        """Test and_then function that raises exception."""
        result = ModelResult.ok(10)

        def failing_bind(x: int) -> ModelResult[int, str]:
            raise ValueError("Bind function failed")

        chained = result.and_then(failing_bind)

        assert chained.is_err()
        assert isinstance(chained.error, str)
        assert chained.error == "Bind function failed"

    def test_or_else_success_passthrough(self):
        """Test or_else with successful result passes through value."""
        result = ModelResult.ok("success_value")

        def should_not_be_called(err: Any) -> ModelResult[str, Any]:
            assert False, "This should not be called"

        alternative = result.or_else(should_not_be_called)

        assert alternative.is_ok()
        assert alternative.unwrap() == "success_value"

    def test_or_else_error_recovery(self):
        """Test or_else for error recovery."""
        result = ModelResult.err("original_error")

        def recover_from_error(err: str) -> ModelResult[str, str]:
            if "error" in err:
                return ModelResult.ok("recovered_value")
            return ModelResult.err("unrecoverable")

        recovered = result.or_else(recover_from_error)

        assert recovered.is_ok()
        assert recovered.unwrap() == "recovered_value"

    def test_or_else_error_to_error(self):
        """Test or_else that converts error to different error."""
        result = ModelResult.err("unknown_problem")

        def recover_from_error(err: str) -> ModelResult[str, str]:
            if "error" in err:
                return ModelResult.ok("recovered_value")
            return ModelResult.err("unrecoverable")

        failed_recovery = result.or_else(recover_from_error)

        assert failed_recovery.is_err()
        assert failed_recovery.error == "unrecoverable"

    def test_or_else_function_exception(self):
        """Test or_else function that raises exception."""
        result = ModelResult.err("error")

        def failing_recovery(err: str) -> ModelResult[str, str]:
            raise RuntimeError("Recovery failed")

        recovered = result.or_else(failing_recovery)

        assert recovered.is_err()
        assert isinstance(recovered.error, str)
        assert recovered.error == "Recovery failed"


class TestModelResultUtilityFunctions:
    """Test utility functions for Result handling."""

    def test_ok_factory_function(self):
        """Test ok() factory function."""
        result = ok("test_value")

        assert isinstance(result, ModelResult)
        assert result.is_ok()
        assert result.unwrap() == "test_value"

    def test_err_factory_function(self):
        """Test err() factory function."""
        result = err("error_message")

        assert isinstance(result, ModelResult)
        assert result.is_err()
        assert result.error == "error_message"

    def test_try_result_success(self):
        """Test try_result with successful function."""

        def successful_function() -> str:
            return "success"

        result = try_result(successful_function)

        assert result.is_ok()
        assert result.unwrap() == "success"

    def test_try_result_exception(self):
        """Test try_result with failing function."""

        def failing_function() -> str:
            raise ValueError("Function failed")

        result = try_result(failing_function)

        assert result.is_err()
        assert isinstance(result.error, str)
        assert "Function failed" in result.error

    def test_try_result_with_side_effects(self):
        """Test try_result with function that has side effects."""
        mock_side_effect = Mock()

        def function_with_side_effects() -> int:
            mock_side_effect()
            return 42

        result = try_result(function_with_side_effects)

        assert result.is_ok()
        assert result.unwrap() == 42
        mock_side_effect.assert_called_once()

    def test_collect_results_all_success(self):
        """Test collect_results with all successful results."""
        results = [
            ModelResult.ok(1),
            ModelResult.ok(2),
            ModelResult.ok(3),
        ]

        collected = collect_results(results)

        assert collected.is_ok()
        assert collected.unwrap() == [1, 2, 3]

    def test_collect_results_all_errors(self):
        """Test collect_results with all error results."""
        results = [
            ModelResult.err("error1"),
            ModelResult.err("error2"),
            ModelResult.err("error3"),
        ]

        collected = collect_results(results)

        assert collected.is_err()
        assert collected.error == ["error1", "error2", "error3"]

    def test_collect_results_mixed(self):
        """Test collect_results with mixed success and error results."""
        results = [
            ModelResult.ok(1),
            ModelResult.err("error1"),
            ModelResult.ok(3),
            ModelResult.err("error2"),
        ]

        collected = collect_results(results)

        assert collected.is_err()
        assert collected.error == ["error1", "error2"]

    def test_collect_results_empty_list(self):
        """Test collect_results with empty list."""
        results: list[ModelResult[int, str]] = []

        collected = collect_results(results)

        assert collected.is_ok()
        assert collected.unwrap() == []


class TestModelResultStringRepresentation:
    """Test string representation methods."""

    def test_repr_success(self):
        """Test __repr__ for successful result."""
        result = ModelResult.ok("test_value")
        repr_str = repr(result)

        assert repr_str == "ModelResult.ok('test_value')"

    def test_repr_error(self):
        """Test __repr__ for error result."""
        result = ModelResult.err("error_message")
        repr_str = repr(result)

        assert repr_str == "ModelResult.err('error_message')"

    def test_str_success(self):
        """Test __str__ for successful result."""
        result = ModelResult.ok(42)
        str_repr = str(result)

        assert str_repr == "Success: 42"

    def test_str_error(self):
        """Test __str__ for error result."""
        result = ModelResult.err("Something went wrong")
        str_repr = str(result)

        assert str_repr == "Error: Something went wrong"

    def test_bool_conversion_success(self):
        """Test boolean conversion for successful result."""
        result = ModelResult.ok("value")

        assert bool(result) is True
        assert result  # Direct truthiness test

    def test_bool_conversion_error(self):
        """Test boolean conversion for error result."""
        result = ModelResult.err("error")

        assert bool(result) is False
        assert not result  # Direct falsiness test


class TestModelResultSerialization:
    """Test serialization and deserialization capabilities."""

    def test_json_serialization_success(self):
        """Test JSON serialization of successful result."""
        result = ModelResult.ok({"data": "test", "count": 42})

        serialized = result.model_dump()

        assert serialized["success"] is True
        assert serialized["value"] == {"data": "test", "count": 42}
        assert serialized["error"] is None

    def test_json_serialization_error(self):
        """Test JSON serialization of error result."""
        result = ModelResult.err("Operation failed")

        serialized = result.model_dump()

        assert serialized["success"] is False
        assert serialized["value"] is None
        assert serialized["error"] == "Operation failed"

    def test_json_deserialization_success(self):
        """Test JSON deserialization of successful result."""
        json_data = {"success": True, "value": "deserialized_value", "error": None}

        result = ModelResult[str, str].model_validate(json_data)

        assert result.is_ok()
        assert result.unwrap() == "deserialized_value"

    def test_json_deserialization_error(self):
        """Test JSON deserialization of error result."""
        json_data = {"success": False, "value": None, "error": "deserialized_error"}

        result = ModelResult[str, str].model_validate(json_data)

        assert result.is_err()
        assert result.error == "deserialized_error"

    def test_round_trip_serialization(self):
        """Test full round-trip serialization."""
        original = ModelResult.ok([1, 2, {"nested": "data"}])

        # Serialize to JSON string
        json_str = original.model_dump_json()

        # Parse and create new instance
        json_data = json.loads(json_str)
        deserialized = ModelResult[list[Any], str].model_validate(json_data)

        assert deserialized.is_ok()
        assert deserialized.unwrap() == [1, 2, {"nested": "data"}]


class TestModelResultComplexScenarios:
    """Test complex real-world usage scenarios."""

    def test_result_chaining_pipeline(self):
        """Test complex result processing pipeline."""

        def parse_number(text: str) -> ModelResult[int, str]:
            try:
                return ModelResult.ok(int(text))
            except ValueError:
                return ModelResult.err(f"'{text}' is not a valid number")

        def validate_positive(num: int) -> ModelResult[int, str]:
            if num > 0:
                return ModelResult.ok(num)
            return ModelResult.err(f"Number {num} must be positive")

        def calculate_square(num: int) -> ModelResult[int, str]:
            return ModelResult.ok(num * num)

        # Success pipeline
        result = (
            parse_number("5").and_then(validate_positive).and_then(calculate_square)
        )

        assert result.is_ok()
        assert result.unwrap() == 25

        # Error in parsing
        result_parse_error = (
            parse_number("not_a_number")
            .and_then(validate_positive)
            .and_then(calculate_square)
        )

        assert result_parse_error.is_err()
        assert "'not_a_number' is not a valid number" in result_parse_error.error

        # Error in validation
        result_validation_error = (
            parse_number("-5").and_then(validate_positive).and_then(calculate_square)
        )

        assert result_validation_error.is_err()
        assert "Number -5 must be positive" in result_validation_error.error

    def test_error_recovery_pattern(self):
        """Test error recovery patterns."""

        def risky_operation() -> ModelResult[str, str]:
            return ModelResult.err("network_timeout")

        def fallback_operation(error: str) -> ModelResult[str, str]:
            if "network" in error:
                return ModelResult.ok("used_cache")
            return ModelResult.err("unrecoverable_error")

        def final_fallback(error: str) -> ModelResult[str, str]:
            return ModelResult.ok("default_value")

        # Successful recovery
        result = risky_operation().or_else(fallback_operation)

        assert result.is_ok()
        assert result.unwrap() == "used_cache"

        # Multi-level fallback
        def unrecoverable_error() -> ModelResult[str, str]:
            return ModelResult.err("database_corruption")

        result_multi_fallback = (
            unrecoverable_error().or_else(fallback_operation).or_else(final_fallback)
        )

        assert result_multi_fallback.is_ok()
        assert result_multi_fallback.unwrap() == "default_value"

    def test_parallel_processing_pattern(self):
        """Test collecting results from parallel operations."""

        def process_item(item: int) -> ModelResult[int, str]:
            if item % 2 == 0:
                return ModelResult.ok(item * 2)
            return ModelResult.err(f"Odd number {item} not allowed")

        # All success
        items = [2, 4, 6, 8]
        results = [process_item(item) for item in items]
        collected = collect_results(results)

        assert collected.is_ok()
        assert collected.unwrap() == [4, 8, 12, 16]

        # Mixed results
        mixed_items = [2, 3, 4, 5]
        mixed_results = [process_item(item) for item in mixed_items]
        mixed_collected = collect_results(mixed_results)

        assert mixed_collected.is_err()
        assert "Odd number 3 not allowed" in mixed_collected.error
        assert "Odd number 5 not allowed" in mixed_collected.error

    def test_configuration_validation_pattern(self):
        """Test configuration validation using Result pattern."""

        def validate_port(port: Any) -> ModelResult[int, str]:
            if not isinstance(port, int):
                return ModelResult.err("Port must be an integer")
            if port < 1 or port > 65535:
                return ModelResult.err(f"Port {port} must be between 1 and 65535")
            return ModelResult.ok(port)

        def validate_host(host: Any) -> ModelResult[str, str]:
            if not isinstance(host, str):
                return ModelResult.err("Host must be a string")
            if not host.strip():
                return ModelResult.err("Host cannot be empty")
            return ModelResult.ok(host.strip())

        def validate_config(
            config: dict[str, Any],
        ) -> ModelResult[dict[str, Any], list[str]]:
            host_result = validate_host(config.get("host"))
            port_result = validate_port(config.get("port"))

            errors = []
            if host_result.is_err():
                errors.append(host_result.error)
            if port_result.is_err():
                errors.append(port_result.error)

            if errors:
                return ModelResult.err(errors)

            return ModelResult.ok(
                {"host": host_result.unwrap(), "port": port_result.unwrap()},
            )

        # Valid configuration
        valid_config = {"host": "localhost", "port": 8080}
        result = validate_config(valid_config)
        assert result.is_ok()
        assert result.unwrap() == {"host": "localhost", "port": 8080}

        # Invalid configuration
        invalid_config = {"host": "", "port": "not_a_number"}
        result = validate_config(invalid_config)
        assert result.is_err()
        assert "Host cannot be empty" in result.error
        assert "Port must be an integer" in result.error
