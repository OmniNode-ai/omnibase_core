# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ModelPhaseStep.

This module tests the ModelPhaseStep model which represents a single phase unit
in the ONEX Runtime Execution Sequencing Model.

Test Categories:
1. Model creation with all fields
2. Default values
3. Validation (frozen, extra fields)
4. Helper methods (is_empty, handler_count, has_handler, get_handler_index)
5. Serialization/deserialization
6. String representations

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_handler_execution_phase import EnumHandlerExecutionPhase
from omnibase_core.models.execution.model_phase_step import ModelPhaseStep

# =============================================================================
# Model Creation Tests
# =============================================================================


@pytest.mark.unit
class TestModelPhaseStepCreation:
    """Tests for ModelPhaseStep creation and initialization."""

    def test_create_with_all_fields(self) -> None:
        """Test creating a ModelPhaseStep with all fields specified."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a", "handler_b", "handler_c"],
            ordering_rationale="A must run before B, C depends on both",
            metadata={"priority": "high", "timeout": 30},
        )

        assert step.phase == EnumHandlerExecutionPhase.EXECUTE
        assert step.handler_ids == ["handler_a", "handler_b", "handler_c"]
        assert step.ordering_rationale == "A must run before B, C depends on both"
        assert step.metadata == {"priority": "high", "timeout": 30}

    def test_create_with_required_fields_only(self) -> None:
        """Test creating a ModelPhaseStep with only required fields."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.PREFLIGHT)

        assert step.phase == EnumHandlerExecutionPhase.PREFLIGHT
        assert step.handler_ids == []
        assert step.ordering_rationale is None
        assert step.metadata is None

    def test_create_with_each_phase(self) -> None:
        """Test creating a ModelPhaseStep with each execution phase."""
        for phase in EnumHandlerExecutionPhase:
            step = ModelPhaseStep(phase=phase)
            assert step.phase == phase

    def test_create_with_empty_handler_list(self) -> None:
        """Test creating a ModelPhaseStep with an explicitly empty handler list."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.BEFORE,
            handler_ids=[],
        )

        assert step.handler_ids == []
        assert step.is_empty() is True

    def test_create_with_single_handler(self) -> None:
        """Test creating a ModelPhaseStep with a single handler."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.AFTER,
            handler_ids=["single_handler"],
        )

        assert step.handler_ids == ["single_handler"]
        assert step.handler_count() == 1


# =============================================================================
# Default Values Tests
# =============================================================================


@pytest.mark.unit
class TestModelPhaseStepDefaults:
    """Tests for ModelPhaseStep default values."""

    def test_handler_ids_defaults_to_empty_list(self) -> None:
        """Test that handler_ids defaults to an empty list."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.EMIT)
        assert step.handler_ids == []
        assert isinstance(step.handler_ids, list)

    def test_ordering_rationale_defaults_to_none(self) -> None:
        """Test that ordering_rationale defaults to None."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.FINALIZE)
        assert step.ordering_rationale is None

    def test_metadata_defaults_to_none(self) -> None:
        """Test that metadata defaults to None."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.EXECUTE)
        assert step.metadata is None


# =============================================================================
# Validation Tests
# =============================================================================


@pytest.mark.unit
class TestModelPhaseStepValidation:
    """Tests for ModelPhaseStep validation behavior."""

    def test_phase_is_required(self) -> None:
        """Test that phase field is required."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseStep()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("phase",)
        assert errors[0]["type"] == "missing"

    def test_invalid_phase_value_raises_error(self) -> None:
        """Test that an invalid phase value raises a validation error."""
        with pytest.raises(ValidationError):
            ModelPhaseStep(phase="invalid_phase")  # type: ignore[arg-type]

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are not allowed (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelPhaseStep(
                phase=EnumHandlerExecutionPhase.EXECUTE,
                unknown_field="value",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert any("extra" in str(err).lower() for err in errors)

    def test_model_is_frozen(self) -> None:
        """Test that the model is immutable (frozen=True)."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a"],
        )

        with pytest.raises(ValidationError):
            step.phase = EnumHandlerExecutionPhase.BEFORE  # type: ignore[misc]

        with pytest.raises(ValidationError):
            step.handler_ids = ["new_handler"]  # type: ignore[misc]

    def test_handler_ids_must_be_list_of_strings(self) -> None:
        """Test that handler_ids must be a list of strings."""
        with pytest.raises(ValidationError):
            ModelPhaseStep(
                phase=EnumHandlerExecutionPhase.EXECUTE,
                handler_ids=[1, 2, 3],  # type: ignore[list-item]
            )

    def test_metadata_accepts_various_value_types(self) -> None:
        """Test that metadata accepts basic typed value types."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            metadata={
                "string_key": "string_value",
                "int_key": 42,
                "float_key": 3.14,
                "bool_key": True,
                "null_key": None,
            },
        )

        assert step.metadata is not None
        assert step.metadata["string_key"] == "string_value"
        assert step.metadata["int_key"] == 42
        assert step.metadata["float_key"] == 3.14
        assert step.metadata["bool_key"] is True
        assert step.metadata["null_key"] is None

    def test_metadata_rejects_complex_types(self) -> None:
        """Test that metadata rejects lists and nested dicts (dict[str, Any] anti-pattern)."""
        with pytest.raises(ValidationError):
            ModelPhaseStep(
                phase=EnumHandlerExecutionPhase.EXECUTE,
                metadata={"list_key": [1, 2, 3]},  # type: ignore[dict-item]
            )

        with pytest.raises(ValidationError):
            ModelPhaseStep(
                phase=EnumHandlerExecutionPhase.EXECUTE,
                metadata={"nested_key": {"inner": "value"}},  # type: ignore[dict-item]
            )


# =============================================================================
# Helper Method Tests
# =============================================================================


@pytest.mark.unit
class TestModelPhaseStepHelperMethods:
    """Tests for ModelPhaseStep helper methods."""

    def test_is_empty_returns_true_for_no_handlers(self) -> None:
        """Test that is_empty() returns True when handler_ids is empty."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.EXECUTE)
        assert step.is_empty() is True

    def test_is_empty_returns_false_for_handlers(self) -> None:
        """Test that is_empty() returns False when handler_ids has items."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a"],
        )
        assert step.is_empty() is False

    def test_handler_count_returns_zero_for_empty(self) -> None:
        """Test that handler_count() returns 0 for empty handler list."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.EXECUTE)
        assert step.handler_count() == 0

    def test_handler_count_returns_correct_count(self) -> None:
        """Test that handler_count() returns correct count."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["a", "b", "c", "d", "e"],
        )
        assert step.handler_count() == 5

    def test_has_handler_returns_true_when_present(self) -> None:
        """Test that has_handler() returns True for existing handler."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a", "handler_b", "handler_c"],
        )
        assert step.has_handler("handler_b") is True

    def test_has_handler_returns_false_when_absent(self) -> None:
        """Test that has_handler() returns False for non-existing handler."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a", "handler_b"],
        )
        assert step.has_handler("handler_x") is False

    def test_has_handler_returns_false_for_empty_list(self) -> None:
        """Test that has_handler() returns False when handler list is empty."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.EXECUTE)
        assert step.has_handler("any_handler") is False

    def test_get_handler_index_returns_correct_index(self) -> None:
        """Test that get_handler_index() returns correct zero-based index."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["first", "second", "third"],
        )
        assert step.get_handler_index("first") == 0
        assert step.get_handler_index("second") == 1
        assert step.get_handler_index("third") == 2

    def test_get_handler_index_returns_none_when_not_found(self) -> None:
        """Test that get_handler_index() returns None for non-existing handler."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["first", "second"],
        )
        assert step.get_handler_index("not_found") is None

    def test_get_handler_index_returns_none_for_empty_list(self) -> None:
        """Test that get_handler_index() returns None for empty handler list."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.EXECUTE)
        assert step.get_handler_index("any_handler") is None


# =============================================================================
# Serialization Tests
# =============================================================================


@pytest.mark.unit
class TestModelPhaseStepSerialization:
    """Tests for ModelPhaseStep serialization and deserialization."""

    def test_model_dump_with_all_fields(self) -> None:
        """Test that model_dump() correctly serializes all fields."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a", "handler_b"],
            ordering_rationale="Test rationale",
            metadata={"key": "value"},
        )

        data = step.model_dump()

        assert data["phase"] == EnumHandlerExecutionPhase.EXECUTE
        assert data["handler_ids"] == ["handler_a", "handler_b"]
        assert data["ordering_rationale"] == "Test rationale"
        assert data["metadata"] == {"key": "value"}

    def test_model_dump_with_defaults(self) -> None:
        """Test that model_dump() correctly serializes default values."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.BEFORE)

        data = step.model_dump()

        assert data["phase"] == EnumHandlerExecutionPhase.BEFORE
        assert data["handler_ids"] == []
        assert data["ordering_rationale"] is None
        assert data["metadata"] is None

    def test_model_dump_json(self) -> None:
        """Test that model_dump_json() produces valid JSON."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a"],
            metadata={"key": "value"},
        )

        json_str = step.model_dump_json()

        assert isinstance(json_str, str)
        assert "execute" in json_str.lower()
        assert "handler_a" in json_str

    def test_model_validate_from_dict(self) -> None:
        """Test that model_validate() correctly deserializes from dict."""
        data = {
            "phase": "execute",
            "handler_ids": ["handler_a", "handler_b"],
            "ordering_rationale": "Test",
            "metadata": {"key": "value"},
        }

        step = ModelPhaseStep.model_validate(data)

        assert step.phase == EnumHandlerExecutionPhase.EXECUTE
        assert step.handler_ids == ["handler_a", "handler_b"]
        assert step.ordering_rationale == "Test"
        assert step.metadata == {"key": "value"}

    def test_model_validate_from_enum_value(self) -> None:
        """Test that phase can be specified as string enum value."""
        data = {
            "phase": "preflight",
            "handler_ids": [],
        }

        step = ModelPhaseStep.model_validate(data)
        assert step.phase == EnumHandlerExecutionPhase.PREFLIGHT

    def test_roundtrip_serialization(self) -> None:
        """Test that serialization and deserialization are consistent."""
        original = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.FINALIZE,
            handler_ids=["cleanup_handler", "log_handler"],
            ordering_rationale="Log after cleanup",
            metadata={"final": True},
        )

        data = original.model_dump()
        restored = ModelPhaseStep.model_validate(data)

        assert restored.phase == original.phase
        assert restored.handler_ids == original.handler_ids
        assert restored.ordering_rationale == original.ordering_rationale
        assert restored.metadata == original.metadata


# =============================================================================
# String Representation Tests
# =============================================================================


@pytest.mark.unit
class TestModelPhaseStepStringRepresentation:
    """Tests for ModelPhaseStep string representations."""

    def test_str_with_handlers(self) -> None:
        """Test __str__ with handlers."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["a", "b"],
        )

        str_repr = str(step)
        assert "execute" in str_repr
        assert "a" in str_repr
        assert "b" in str_repr

    def test_str_with_empty_handlers(self) -> None:
        """Test __str__ with empty handler list."""
        step = ModelPhaseStep(phase=EnumHandlerExecutionPhase.PREFLIGHT)

        str_repr = str(step)
        assert "preflight" in str_repr
        assert "(empty)" in str_repr

    def test_repr_includes_all_fields(self) -> None:
        """Test __repr__ includes all fields."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a"],
            ordering_rationale="Test",
            metadata={"key": "value"},
        )

        repr_str = repr(step)
        assert "ModelPhaseStep" in repr_str
        assert "EXECUTE" in repr_str
        assert "handler_a" in repr_str
        assert "Test" in repr_str
        assert "key" in repr_str


# =============================================================================
# Edge Cases and Integration Tests
# =============================================================================


@pytest.mark.unit
class TestModelPhaseStepEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_handler_order_preserved(self) -> None:
        """Test that handler order is preserved exactly as provided."""
        handlers = ["z_handler", "a_handler", "m_handler", "b_handler"]
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=handlers,
        )

        assert step.handler_ids == handlers
        assert step.handler_ids[0] == "z_handler"
        assert step.handler_ids[-1] == "b_handler"

    def test_duplicate_handler_ids_allowed(self) -> None:
        """Test that duplicate handler IDs are allowed (no uniqueness constraint)."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["handler_a", "handler_a", "handler_b"],
        )

        assert step.handler_count() == 3
        assert step.get_handler_index("handler_a") == 0  # Returns first occurrence

    def test_empty_string_handler_id(self) -> None:
        """Test that empty string handler ID is technically valid."""
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=["", "valid_handler"],
        )

        assert step.has_handler("") is True
        assert step.handler_count() == 2

    def test_from_attributes_allows_object_creation(self) -> None:
        """Test that from_attributes=True allows creation from object attributes."""
        # This tests the from_attributes config option used for pytest-xdist compatibility

        class MockPhaseStep:
            phase = EnumHandlerExecutionPhase.EXECUTE
            handler_ids = ["handler_a"]
            ordering_rationale = "Test"
            metadata = None

        mock_obj = MockPhaseStep()
        step = ModelPhaseStep.model_validate(mock_obj, from_attributes=True)

        assert step.phase == EnumHandlerExecutionPhase.EXECUTE
        assert step.handler_ids == ["handler_a"]
        assert step.ordering_rationale == "Test"

    def test_from_attributes_with_init_method(self) -> None:
        """Test from_attributes=True with object using __init__ method.

        Complements test_from_attributes_allows_object_creation which uses
        class attributes. This tests the more common pattern of instance
        attributes set in __init__.
        """

        class MockPhaseStepWithInit:
            def __init__(self) -> None:
                self.phase = EnumHandlerExecutionPhase.EXECUTE
                self.handler_ids = ["mock_handler"]
                self.ordering_rationale = None
                self.metadata = None

        mock_step = MockPhaseStepWithInit()
        step = ModelPhaseStep.model_validate(mock_step, from_attributes=True)

        assert step.phase == EnumHandlerExecutionPhase.EXECUTE
        assert step.handler_ids == ["mock_handler"]
        assert step.ordering_rationale is None
        assert step.metadata is None

    def test_long_handler_list(self) -> None:
        """Test handling of a large number of handlers."""
        handlers = [f"handler_{i}" for i in range(100)]
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=handlers,
        )

        assert step.handler_count() == 100
        assert step.has_handler("handler_0") is True
        assert step.has_handler("handler_99") is True
        assert step.get_handler_index("handler_50") == 50

    def test_unicode_handler_ids(self) -> None:
        """Test that Unicode handler IDs are supported.

        Validates that the model correctly handles handler IDs containing:
        - Chinese characters
        - Japanese characters
        - Emoji characters
        - Mixed Unicode and ASCII
        """
        unicode_handlers = [
            "handler_\u4e2d\u6587",  # Chinese characters (handler_中文)
            "\u30cf\u30f3\u30c9\u30e9\u30fc_\u65e5\u672c",  # Japanese (ハンドラー_日本)
            "emoji_handler_\u2728\u2705",  # Emoji (emoji_handler_✨✅)
            "mixed_\u03b1\u03b2\u03b3_handler",  # Greek letters (mixed_αβγ_handler)
        ]
        step = ModelPhaseStep(
            phase=EnumHandlerExecutionPhase.EXECUTE,
            handler_ids=unicode_handlers,
        )

        # Verify all Unicode handlers are present and retrievable
        assert step.handler_count() == 4
        assert step.has_handler("handler_\u4e2d\u6587") is True
        assert step.has_handler("\u30cf\u30f3\u30c9\u30e9\u30fc_\u65e5\u672c") is True
        assert step.has_handler("emoji_handler_\u2728\u2705") is True
        assert step.has_handler("mixed_\u03b1\u03b2\u03b3_handler") is True
        assert step.get_handler_index("handler_\u4e2d\u6587") == 0
        assert step.get_handler_index("emoji_handler_\u2728\u2705") == 2
