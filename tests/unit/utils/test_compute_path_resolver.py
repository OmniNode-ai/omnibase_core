# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for compute_path_resolver shared utility.

Tests the path resolution functions extracted for v1.1 to reduce duplication
between compute_executor.py and compute_transformations.py.

Test Categories:
    - Simple path resolution (resolve_path)
    - Input path resolution (resolve_input_path)
    - Step path resolution (resolve_step_path)
    - Pipeline path resolution (resolve_pipeline_path)
    - Private attribute security
    - Error handling and edge cases
"""

from dataclasses import dataclass
from typing import Any

import pytest

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.utils.util_compute_path_resolver import (
    PathResolutionError,
    resolve_input_path,
    resolve_path,
    resolve_pipeline_path,
    resolve_step_path,
)


# Test fixtures and helpers
@dataclass
class MockStepResult:
    """Mock step result with output attribute for testing."""

    output: Any
    step_name: str = "mock_step"


@dataclass
class MockObject:
    """Mock object with various attributes for testing."""

    name: str
    value: int
    _private: str = "secret"


class NestedObject:
    """Object with nested structure for testing attribute access."""

    def __init__(self) -> None:
        self.user = MockObject(name="Alice", value=42)
        self.items = [1, 2, 3]


# =============================================================================
# Test resolve_path (simple dot-notation paths)
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestResolvePath:
    """Tests for resolve_path function (simple dot-notation paths)."""

    def test_root_access_empty_string(self) -> None:
        """Test empty string returns root object."""
        data = {"name": "test"}
        assert resolve_path("", data) == data

    def test_root_access_dollar_sign(self) -> None:
        """Test $ returns root object."""
        data = {"name": "test"}
        assert resolve_path("$", data) == data

    def test_simple_field_access(self) -> None:
        """Test simple field access without $ prefix."""
        data = {"name": "Alice", "age": 30}
        assert resolve_path("name", data) == "Alice"
        assert resolve_path("age", data) == 30

    def test_field_access_with_dollar_prefix(self) -> None:
        """Test field access with $. prefix."""
        data = {"name": "Bob", "active": True}
        assert resolve_path("$.name", data) == "Bob"
        assert resolve_path("$.active", data) is True

    def test_nested_field_access(self) -> None:
        """Test nested field access."""
        data = {"user": {"name": "Charlie", "profile": {"age": 25}}}
        assert resolve_path("user.name", data) == "Charlie"
        assert resolve_path("$.user.profile.age", data) == 25

    def test_deeply_nested_access(self) -> None:
        """Test deeply nested field access."""
        data = {"a": {"b": {"c": {"d": {"e": "deep"}}}}}
        assert resolve_path("a.b.c.d.e", data) == "deep"
        assert resolve_path("$.a.b.c.d.e", data) == "deep"

    def test_object_attribute_access(self) -> None:
        """Test accessing attributes on objects (not dicts)."""
        obj = MockObject(name="Test", value=100)
        assert resolve_path("name", obj) == "Test"
        assert resolve_path("value", obj) == 100

    def test_nested_object_attribute_access(self) -> None:
        """Test nested object attribute access."""
        container = NestedObject()
        assert resolve_path("user.name", container) == "Alice"
        assert resolve_path("user.value", container) == 42

    def test_mixed_dict_and_object_access(self) -> None:
        """Test mixed dictionary and object attribute access."""
        data = {"container": NestedObject()}
        assert resolve_path("container.user.name", data) == "Alice"

    def test_missing_key_raises_error(self) -> None:
        """Test missing dictionary key raises PathResolutionError."""
        data = {"name": "test"}
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_path("missing", data)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "missing" in str(exc_info.value.message)

    def test_missing_attribute_raises_error(self) -> None:
        """Test missing object attribute raises PathResolutionError."""
        obj = MockObject(name="Test", value=1)
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_path("nonexistent", obj)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_private_attribute_blocked_by_default(self) -> None:
        """Test private attribute access is blocked by default."""
        obj = MockObject(name="Test", value=1, _private="secret")
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_path("_private", obj)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "private" in str(exc_info.value.message).lower()

    def test_private_attribute_allowed_when_disabled(self) -> None:
        """Test private attribute access when check_private=False."""
        obj = MockObject(name="Test", value=1, _private="secret")
        result = resolve_path("_private", obj, check_private=False)
        assert result == "secret"

    def test_underscore_dict_key_accessible(self) -> None:
        """Test dictionary keys starting with _ are accessible."""
        data = {"_private_key": "allowed"}
        assert resolve_path("_private_key", data) == "allowed"

    def test_none_value_accessible(self) -> None:
        """Test None values can be accessed."""
        data = {"nullable": None}
        assert resolve_path("nullable", data) is None

    def test_empty_string_value_accessible(self) -> None:
        """Test empty string values can be accessed."""
        data = {"empty": ""}
        assert resolve_path("empty", data) == ""

    def test_list_value_accessible(self) -> None:
        """Test list values can be accessed."""
        data = {"items": [1, 2, 3]}
        assert resolve_path("items", data) == [1, 2, 3]

    def test_boolean_values(self) -> None:
        """Test boolean values can be accessed."""
        data = {"active": True, "deleted": False}
        assert resolve_path("active", data) is True
        assert resolve_path("deleted", data) is False


# =============================================================================
# Test resolve_input_path ($.input prefix)
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestResolveInputPath:
    """Tests for resolve_input_path function ($.input prefix paths)."""

    def test_full_input_access(self) -> None:
        """Test $.input returns full input object."""
        input_data = {"text": "hello", "count": 5}
        assert resolve_input_path("$.input", input_data) == input_data

    def test_full_input_access_shorthand(self) -> None:
        """Test $input shorthand returns full input object."""
        input_data = {"text": "hello"}
        assert resolve_input_path("$input", input_data) == input_data

    def test_input_field_access(self) -> None:
        """Test $.input.<field> access."""
        input_data = {"text": "hello", "count": 5}
        assert resolve_input_path("$.input.text", input_data) == "hello"
        assert resolve_input_path("$.input.count", input_data) == 5

    def test_input_field_access_shorthand(self) -> None:
        """Test $input.<field> shorthand access."""
        input_data = {"text": "hello"}
        assert resolve_input_path("$input.text", input_data) == "hello"

    def test_nested_input_field_access(self) -> None:
        """Test $.input.<field>.<subfield> access."""
        input_data = {"user": {"name": "John", "id": 123}}
        assert resolve_input_path("$.input.user.name", input_data) == "John"
        assert resolve_input_path("$.input.user.id", input_data) == 123

    def test_deeply_nested_input_access(self) -> None:
        """Test deeply nested input field access."""
        input_data = {"a": {"b": {"c": {"d": "deep"}}}}
        assert resolve_input_path("$.input.a.b.c.d", input_data) == "deep"

    def test_missing_input_field_raises_error(self) -> None:
        """Test missing input field raises error."""
        input_data = {"name": "test"}
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_input_path("$.input.missing", input_data)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_private_attribute_blocked_on_input_objects(self) -> None:
        """Test private attribute access blocked on input objects."""
        input_data = MockObject(name="Test", value=1, _private="secret")
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_input_path("$.input._private", input_data)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_underscore_dict_key_accessible_in_input(self) -> None:
        """Test underscore dict keys are accessible in input."""
        input_data = {"_metadata": {"version": 1}}
        assert resolve_input_path("$.input._metadata.version", input_data) == 1

    def test_invalid_input_path_format_raises_error(self) -> None:
        """Test invalid input path format raises error."""
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_input_path("$.other.field", {})
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR


# =============================================================================
# Test resolve_step_path ($.steps prefix)
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestResolveStepPath:
    """Tests for resolve_step_path function ($.steps prefix paths)."""

    def test_step_output_shorthand(self) -> None:
        """Test $.steps.<name> returns output (shorthand)."""
        step_results = {"transform": MockStepResult(output="HELLO")}
        assert resolve_step_path("$.steps.transform", step_results) == "HELLO"

    def test_step_output_explicit(self) -> None:
        """Test $.steps.<name>.output returns output (explicit)."""
        step_results = {"transform": MockStepResult(output="HELLO")}
        assert resolve_step_path("$.steps.transform.output", step_results) == "HELLO"

    def test_step_output_shorthand_and_explicit_equivalent(self) -> None:
        """Test shorthand and explicit forms return same value."""
        step_results = {"normalize": MockStepResult(output={"data": "value"})}
        shorthand = resolve_step_path("$.steps.normalize", step_results)
        explicit = resolve_step_path("$.steps.normalize.output", step_results)
        assert shorthand == explicit

    def test_multiple_steps(self) -> None:
        """Test resolving from multiple step results."""
        step_results = {
            "step1": MockStepResult(output="first"),
            "step2": MockStepResult(output="second"),
            "step3": MockStepResult(output="third"),
        }
        assert resolve_step_path("$.steps.step1", step_results) == "first"
        assert resolve_step_path("$.steps.step2", step_results) == "second"
        assert resolve_step_path("$.steps.step3.output", step_results) == "third"

    def test_step_with_dict_output(self) -> None:
        """Test step result with dictionary output."""
        step_results = {"transform": MockStepResult(output={"key": "value"})}
        result = resolve_step_path("$.steps.transform", step_results)
        assert result == {"key": "value"}

    def test_step_with_list_output(self) -> None:
        """Test step result with list output."""
        step_results = {"collect": MockStepResult(output=[1, 2, 3])}
        result = resolve_step_path("$.steps.collect", step_results)
        assert result == [1, 2, 3]

    def test_step_with_none_output(self) -> None:
        """Test step result with None output."""
        step_results = {"nullable": MockStepResult(output=None)}
        result = resolve_step_path("$.steps.nullable", step_results)
        assert result is None

    def test_missing_step_raises_error(self) -> None:
        """Test missing step raises error."""
        step_results = {"existing": MockStepResult(output="value")}
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_step_path("$.steps.nonexistent", step_results)
        assert exc_info.value.error_code == EnumCoreErrorCode.OPERATION_FAILED
        assert "nonexistent" in str(exc_info.value.message)

    def test_invalid_step_subpath_raises_error(self) -> None:
        """Test invalid step subpath (not .output) raises error."""
        step_results = {"transform": MockStepResult(output="HELLO")}
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_step_path("$.steps.transform.invalid", step_results)
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "only '.output' supported" in str(exc_info.value.message)

    def test_invalid_step_path_format_raises_error(self) -> None:
        """Test invalid step path format raises error."""
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_step_path("$.input.field", {})
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_empty_step_name_raises_error(self) -> None:
        """Test empty step name raises error."""
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_step_path("$.steps.", {})
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR

    def test_step_result_without_output_attribute(self) -> None:
        """Test step result that's just a value (no .output attribute)."""
        # Some implementations may store raw values instead of objects
        step_results: dict[str, Any] = {"direct": "raw_value"}
        result = resolve_step_path("$.steps.direct", step_results)
        assert result == "raw_value"


# =============================================================================
# Test resolve_pipeline_path (unified resolver)
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestResolvePipelinePath:
    """Tests for resolve_pipeline_path function (unified pipeline resolver)."""

    def test_routes_to_input_path(self) -> None:
        """Test input paths are routed correctly."""
        input_data = {"text": "hello"}
        step_results: dict[str, Any] = {}
        result = resolve_pipeline_path("$.input.text", input_data, step_results)
        assert result == "hello"

    def test_routes_to_step_path(self) -> None:
        """Test step paths are routed correctly."""
        input_data: dict[str, Any] = {}
        step_results = {"transform": MockStepResult(output="HELLO")}
        result = resolve_pipeline_path("$.steps.transform", input_data, step_results)
        assert result == "HELLO"

    def test_full_input_via_pipeline_resolver(self) -> None:
        """Test $.input via pipeline resolver."""
        input_data = {"data": "value"}
        result = resolve_pipeline_path("$.input", input_data, {})
        assert result == input_data

    def test_input_shorthand_via_pipeline_resolver(self) -> None:
        """Test $input shorthand via pipeline resolver."""
        input_data = {"data": "value"}
        result = resolve_pipeline_path("$input", input_data, {})
        assert result == input_data

    def test_nested_input_via_pipeline_resolver(self) -> None:
        """Test nested $.input paths via pipeline resolver."""
        input_data = {"user": {"name": "Alice"}}
        result = resolve_pipeline_path("$.input.user.name", input_data, {})
        assert result == "Alice"

    def test_step_output_via_pipeline_resolver(self) -> None:
        """Test $.steps paths via pipeline resolver."""
        step_results = {"process": MockStepResult(output=42)}
        result = resolve_pipeline_path("$.steps.process.output", {}, step_results)
        assert result == 42

    def test_path_without_dollar_prefix_raises_error(self) -> None:
        """Test path without $ prefix raises error."""
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_pipeline_path("input.field", {}, {})
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "must start with '$'" in str(exc_info.value.message)

    def test_invalid_prefix_raises_error(self) -> None:
        """Test invalid path prefix raises error."""
        with pytest.raises(PathResolutionError) as exc_info:
            resolve_pipeline_path("$.other.path", {}, {})
        assert exc_info.value.error_code == EnumCoreErrorCode.VALIDATION_ERROR
        assert "Invalid path prefix" in str(exc_info.value.message)


# =============================================================================
# Test PathResolutionError
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestPathResolutionError:
    """Tests for PathResolutionError exception class."""

    def test_basic_error_creation(self) -> None:
        """Test basic error creation."""
        error = PathResolutionError(
            message="Test error",
            error_code=EnumCoreErrorCode.OPERATION_FAILED,
        )
        assert "Test error" in str(error.message)
        assert error.error_code == EnumCoreErrorCode.OPERATION_FAILED

    def test_error_with_path_context(self) -> None:
        """Test error with path in context."""
        error = PathResolutionError(
            message="Path not found",
            path="$.input.missing",
        )
        assert error.context is not None
        # Custom context is stored in additional_context.context by ModelOnexError
        additional = error.context.get("additional_context", {})
        inner_context = additional.get("context", {})
        assert inner_context.get("path") == "$.input.missing"

    def test_error_with_segment_context(self) -> None:
        """Test error with segment in context."""
        error = PathResolutionError(
            message="Missing key",
            path="$.input.user.name",
            segment="name",
        )
        assert error.context is not None
        # Custom context is stored in additional_context.context by ModelOnexError
        additional = error.context.get("additional_context", {})
        inner_context = additional.get("context", {})
        assert inner_context.get("segment") == "name"

    def test_error_with_available_keys_context(self) -> None:
        """Test error with available_keys in context."""
        error = PathResolutionError(
            message="Key not found",
            path="$.input.missing",
            segment="missing",
            available_keys=["name", "age", "email"],
        )
        assert error.context is not None
        # Custom context is stored in additional_context.context by ModelOnexError
        additional = error.context.get("additional_context", {})
        inner_context = additional.get("context", {})
        assert inner_context.get("available_keys") == ["name", "age", "email"]

    def test_error_is_model_onex_error_subclass(self) -> None:
        """Test PathResolutionError is a ModelOnexError subclass."""
        from omnibase_core.models.errors.model_onex_error import ModelOnexError

        error = PathResolutionError(message="Test")
        assert isinstance(error, ModelOnexError)


# =============================================================================
# Test edge cases and security
# =============================================================================


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestEdgeCasesAndSecurity:
    """Tests for edge cases and security considerations."""

    def test_empty_dict_traversal(self) -> None:
        """Test traversing into empty dict."""
        data: dict[str, Any] = {}
        with pytest.raises(PathResolutionError):
            resolve_path("missing", data)

    def test_nested_empty_dict(self) -> None:
        """Test nested empty dict access."""
        data: dict[str, Any] = {"outer": {}}
        with pytest.raises(PathResolutionError):
            resolve_path("outer.inner", data)

    def test_path_with_consecutive_dots(self) -> None:
        """Test path with consecutive dots (empty segments are skipped)."""
        data = {"outer": {"inner": "value"}}
        # Consecutive dots in middle of path (e.g., "outer..inner") result in
        # empty segments that are skipped, equivalent to "outer.inner"
        result = resolve_path("outer..inner", data)
        assert result == "value"

        # Multiple consecutive dots (3+ dots)
        result = resolve_path("outer...inner", data)
        assert result == "value"

        # Trailing consecutive dots
        data_simple = {"field": "value"}
        result = resolve_path("field..", data_simple)
        assert result == "value"

        # Leading consecutive dots (empty segments at start are skipped)
        result = resolve_path("..outer.inner", data)
        assert result == "value"

        # Mixed: leading, middle, and trailing consecutive dots
        result = resolve_path("..outer..inner..", data)
        assert result == "value"

    def test_path_with_trailing_dot(self) -> None:
        """Test path with trailing dot."""
        data = {"field": "value"}
        # Trailing dot results in empty final segment, skipped
        result = resolve_path("field.", data)
        assert result == "value"

    def test_unicode_keys(self) -> None:
        """Test paths with unicode keys."""
        data = {"user_name": "test", "full_name": "Test User"}
        assert resolve_path("user_name", data) == "test"
        assert resolve_path("full_name", data) == "Test User"

    def test_numeric_string_keys(self) -> None:
        """Test paths with numeric string keys."""
        data = {"123": "numeric_key", "0": "zero"}
        assert resolve_path("123", data) == "numeric_key"
        assert resolve_path("0", data) == "zero"

    def test_special_characters_in_keys(self) -> None:
        """Test dictionary keys with special characters."""
        data = {"key-with-dash": "dash", "key_with_underscore": "underscore"}
        # These should work as they're dict keys
        assert resolve_path("key-with-dash", data) == "dash"
        assert resolve_path("key_with_underscore", data) == "underscore"

    def test_very_long_path(self) -> None:
        """Test resolution of very long paths."""
        # Build a deeply nested structure
        depth = 50
        data: dict[str, Any] = {"value": "found"}
        for i in range(depth - 1, -1, -1):
            data = {f"level{i}": data}

        # Build the path
        path = ".".join(f"level{i}" for i in range(depth)) + ".value"
        assert resolve_path(path, data) == "found"

    def test_step_names_with_underscores(self) -> None:
        """Test step names containing underscores."""
        step_results = {
            "my_step": MockStepResult(output="value1"),
            "another_longer_step_name": MockStepResult(output="value2"),
        }
        assert resolve_step_path("$.steps.my_step", step_results) == "value1"
        assert (
            resolve_step_path("$.steps.another_longer_step_name", step_results)
            == "value2"
        )

    def test_step_names_with_numbers(self) -> None:
        """Test step names containing numbers."""
        step_results = {
            "step1": MockStepResult(output="first"),
            "process_v2": MockStepResult(output="second"),
        }
        assert resolve_step_path("$.steps.step1", step_results) == "first"
        assert resolve_step_path("$.steps.process_v2", step_results) == "second"
