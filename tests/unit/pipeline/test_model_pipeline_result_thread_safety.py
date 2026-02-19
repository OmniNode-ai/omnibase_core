# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Tests for ModelPipelineResult thread safety features.

This module tests the thread-safety guarantees of ModelPipelineResult,
including defensive copying, frozen_copy(), and frozen_context_data.
"""

from types import MappingProxyType

import pytest

from omnibase_core.models.pipeline.model_hook_error import ModelHookError
from omnibase_core.models.pipeline.model_pipeline_context import ModelPipelineContext
from omnibase_core.models.pipeline.model_pipeline_result import ModelPipelineResult


@pytest.mark.unit
class TestModelPipelineResultDefensiveCopy:
    """Test defensive copying on initialization."""

    @pytest.mark.unit
    def test_context_defensive_copy_breaks_external_reference(self) -> None:
        """Defensive copy prevents external modification of context."""
        # Create context with nested data
        original_data = {"key": {"nested": "original_value"}}
        ctx = ModelPipelineContext(data=original_data)

        # Create result - defensive copy should be made
        result = ModelPipelineResult(success=True, context=ctx)

        # Modify original context after result creation
        ctx.data["key"]["nested"] = "modified_value"
        ctx.data["new_key"] = "new_value"

        # Result's context should be unaffected
        assert result.context is not None
        assert result.context.data["key"]["nested"] == "original_value"
        assert "new_key" not in result.context.data

    @pytest.mark.unit
    def test_context_defensive_copy_from_dict_input(self) -> None:
        """Defensive copy works when context is passed as mapping."""
        original_data = {"key": {"nested": "value"}}
        ctx = ModelPipelineContext(data=original_data)

        # Create result using model_validate (from_attributes path)
        result = ModelPipelineResult.model_validate(
            {"success": True, "context": ctx},
            from_attributes=True,
        )

        # Modify original
        original_data["key"]["nested"] = "modified"

        # Result should be unaffected
        assert result.context is not None
        assert result.context.data["key"]["nested"] == "value"

    @pytest.mark.unit
    def test_errors_converted_to_tuple(self) -> None:
        """List of errors is converted to immutable tuple."""
        error = ModelHookError(
            phase="execute",
            hook_name="test_hook",
            error_type="ValueError",
            error_message="Test error",
        )
        errors_list = [error]

        result = ModelPipelineResult(success=False, errors=errors_list)

        # Should be a tuple, not a list
        assert isinstance(result.errors, tuple)
        assert len(result.errors) == 1
        assert result.errors[0] is error


@pytest.mark.unit
class TestModelPipelineResultFrozenCopy:
    """Test frozen_copy() method for thread-safe sharing."""

    @pytest.mark.unit
    def test_frozen_copy_creates_independent_context(self) -> None:
        """frozen_copy() creates a new context with copied data."""
        ctx = ModelPipelineContext(data={"key": {"nested": "value"}})
        result = ModelPipelineResult(success=True, context=ctx)

        # Create frozen copy
        frozen = result.frozen_copy()

        # Modify original result's context
        assert result.context is not None
        result.context.data["key"]["nested"] = "modified"

        # Frozen copy should be unaffected
        assert frozen.context is not None
        assert frozen.context.data["key"]["nested"] == "value"

    @pytest.mark.unit
    def test_frozen_copy_creates_independent_errors_tuple(self) -> None:
        """frozen_copy() creates a new errors tuple for complete isolation."""
        error = ModelHookError(
            phase="after",
            hook_name="test",
            error_type="RuntimeError",
            error_message="Error message",
        )
        result = ModelPipelineResult(success=False, errors=(error,), context=None)

        # Create frozen copy
        frozen = result.frozen_copy()

        # Errors should be different tuple objects (complete isolation)
        assert frozen.errors is not result.errors
        # But contents should be equal
        assert frozen.errors == result.errors
        assert len(frozen.errors) == 1
        assert frozen.errors[0].hook_name == "test"

    @pytest.mark.unit
    def test_frozen_copy_with_none_context(self) -> None:
        """frozen_copy() handles None context correctly."""
        result = ModelPipelineResult(success=True, context=None)

        frozen = result.frozen_copy()

        assert frozen.success is True
        assert frozen.context is None

    @pytest.mark.unit
    def test_frozen_copy_preserves_success_field(self) -> None:
        """frozen_copy() preserves success field."""
        result_success = ModelPipelineResult(success=True, context=None)
        result_failure = ModelPipelineResult(success=False, context=None)

        frozen_success = result_success.frozen_copy()
        frozen_failure = result_failure.frozen_copy()

        assert frozen_success.success is True
        assert frozen_failure.success is False

    @pytest.mark.unit
    def test_frozen_copy_with_complex_nested_data(self) -> None:
        """frozen_copy() correctly deep copies complex nested structures."""
        complex_data = {
            "level1": {
                "level2": {
                    "level3": ["item1", "item2", {"key": "value"}],
                },
            },
            "list_data": [1, 2, {"nested": "dict"}],
        }
        ctx = ModelPipelineContext(data=complex_data)
        result = ModelPipelineResult(success=True, context=ctx)

        frozen = result.frozen_copy()

        # Modify deeply nested data in original
        assert result.context is not None
        result.context.data["level1"]["level2"]["level3"][2]["key"] = "modified"
        result.context.data["list_data"][2]["nested"] = "also_modified"

        # Frozen copy should be unaffected
        assert frozen.context is not None
        assert frozen.context.data["level1"]["level2"]["level3"][2]["key"] == "value"
        assert frozen.context.data["list_data"][2]["nested"] == "dict"


@pytest.mark.unit
class TestModelPipelineResultFrozenContextData:
    """Test frozen_context_data property for immutable access."""

    @pytest.mark.unit
    def test_frozen_context_data_returns_mapping_proxy(self) -> None:
        """frozen_context_data returns MappingProxyType."""
        ctx = ModelPipelineContext(data={"key": "value"})
        result = ModelPipelineResult(success=True, context=ctx)

        frozen_data = result.frozen_context_data

        assert isinstance(frozen_data, MappingProxyType)

    @pytest.mark.unit
    def test_frozen_context_data_is_immutable(self) -> None:
        """frozen_context_data cannot be modified."""
        ctx = ModelPipelineContext(data={"key": "value"})
        result = ModelPipelineResult(success=True, context=ctx)

        frozen_data = result.frozen_context_data

        # Attempting to modify should raise TypeError
        with pytest.raises(TypeError):
            frozen_data["key"] = "new_value"  # type: ignore[index]

        with pytest.raises(TypeError):
            frozen_data["new_key"] = "value"  # type: ignore[index]

    @pytest.mark.unit
    def test_frozen_context_data_returns_deep_copy(self) -> None:
        """frozen_context_data returns a deep copy of the data."""
        ctx = ModelPipelineContext(data={"key": {"nested": "value"}})
        result = ModelPipelineResult(success=True, context=ctx)

        frozen_data1 = result.frozen_context_data
        frozen_data2 = result.frozen_context_data

        # Each call should return a new copy
        # Note: MappingProxyType wraps a new dict each time
        assert frozen_data1 == frozen_data2
        assert frozen_data1["key"]["nested"] == "value"

    @pytest.mark.unit
    def test_frozen_context_data_with_none_context(self) -> None:
        """frozen_context_data returns empty proxy for None context."""
        result = ModelPipelineResult(success=True, context=None)

        frozen_data = result.frozen_context_data

        assert isinstance(frozen_data, MappingProxyType)
        assert len(frozen_data) == 0

    @pytest.mark.unit
    def test_frozen_context_data_isolated_from_result_context(self) -> None:
        """frozen_context_data is isolated from result's context."""
        ctx = ModelPipelineContext(data={"key": {"nested": "value"}})
        result = ModelPipelineResult(success=True, context=ctx)

        frozen_data = result.frozen_context_data

        # Modify result's context
        assert result.context is not None
        result.context.data["key"]["nested"] = "modified"

        # frozen_data should be unaffected (it's a deep copy)
        assert frozen_data["key"]["nested"] == "value"


@pytest.mark.unit
class TestModelPipelineResultImmutability:
    """Test immutability guarantees of ModelPipelineResult."""

    @pytest.mark.unit
    def test_result_is_frozen(self) -> None:
        """ModelPipelineResult is frozen (top-level fields immutable)."""
        result = ModelPipelineResult(success=True, context=None)

        with pytest.raises(Exception):  # ValidationError for frozen model
            result.success = False  # type: ignore[misc]

    @pytest.mark.unit
    def test_errors_tuple_is_immutable(self) -> None:
        """Errors tuple cannot be modified."""
        error = ModelHookError(
            phase="execute",
            hook_name="test",
            error_type="ValueError",
            error_message="Test",
        )
        result = ModelPipelineResult(success=False, errors=(error,))

        # Verify it's a tuple (tuples don't have append)
        assert isinstance(result.errors, tuple)
        assert not hasattr(result.errors, "append")

        # Tuples don't support item assignment
        with pytest.raises(TypeError):
            result.errors[0] = error  # type: ignore[index]

    @pytest.mark.unit
    def test_model_hook_error_is_frozen(self) -> None:
        """ModelHookError instances are frozen."""
        error = ModelHookError(
            phase="execute",
            hook_name="test",
            error_type="ValueError",
            error_message="Test",
        )

        with pytest.raises(Exception):  # ValidationError for frozen model
            error.phase = "after"  # type: ignore[misc]


@pytest.mark.unit
class TestModelPipelineResultThreadSafetyDocumentation:
    """Test that thread safety documentation assertions hold."""

    @pytest.mark.unit
    def test_errors_field_type_is_tuple(self) -> None:
        """Errors field is stored as tuple for thread safety."""
        error = ModelHookError(
            phase="execute",
            hook_name="test",
            error_type="ValueError",
            error_message="Test",
        )
        # Pass as list
        result = ModelPipelineResult(success=False, errors=[error])  # type: ignore[arg-type]

        # Should be converted to tuple
        assert isinstance(result.errors, tuple)

    @pytest.mark.unit
    def test_frozen_copy_object_isolation(self) -> None:
        """frozen_copy() provides complete object isolation."""
        error = ModelHookError(
            phase="execute",
            hook_name="test",
            error_type="ValueError",
            error_message="Test",
        )
        ctx = ModelPipelineContext(data={"key": "value"})
        original = ModelPipelineResult(success=True, errors=(error,), context=ctx)

        copy = original.frozen_copy()

        # Object identity checks (isolation verification)
        assert copy is not original
        assert copy.errors is not original.errors  # New tuple
        assert copy.context is not original.context  # New context
        # But values should be equal
        assert copy.success == original.success
        assert copy.errors == original.errors
        assert copy.context is not None and original.context is not None
        assert copy.context.data == original.context.data


__all__ = []
