# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

import pytest

# SPDX-FileCopyrightText: 2024 OmniNode Team
#
# SPDX-License-Identifier: Apache-2.0
"""
Tests for ModelComputeInput model hardening (frozen + extra=forbid).

Verifies that ModelComputeInput is properly hardened with frozen=True
and extra="forbid" to match ModelComputeOutput standards.

These tests ensure:
- Model is immutable after creation (frozen=True)
- Extra fields are rejected at instantiation (extra="forbid")
- model_copy() works correctly for creating modified copies
"""

from pydantic import ValidationError

from omnibase_core.models.compute.model_compute_input import ModelComputeInput


@pytest.mark.timeout(30)
@pytest.mark.unit
class TestModelComputeInputHardening:
    """Tests for ModelComputeInput frozen and extra=forbid."""

    def test_frozen_model_prevents_assignment(self) -> None:
        """Verify ModelComputeInput is immutable after creation."""
        input_model = ModelComputeInput(
            data="test_data",
            computation_type="test_computation",
        )
        with pytest.raises(ValidationError):
            input_model.data = "modified_data"  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        """Verify extra fields are rejected at instantiation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelComputeInput(
                data="test_data",
                computation_type="test_computation",
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_model_config_frozen(self) -> None:
        """Verify model_config has frozen=True."""
        config = ModelComputeInput.model_config
        assert config.get("frozen") is True

    def test_model_config_extra_forbid(self) -> None:
        """Verify model_config has extra='forbid'."""
        config = ModelComputeInput.model_config
        assert config.get("extra") == "forbid"

    def test_model_copy_works_for_frozen(self) -> None:
        """Verify model_copy can be used to create modified copies."""
        original = ModelComputeInput(
            data="original_data",
            computation_type="test_computation",
            cache_enabled=True,
            parallel_enabled=False,
        )

        # Create a modified copy (this is the correct pattern for frozen models)
        modified = original.model_copy(update={"cache_enabled": False})

        assert original.cache_enabled is True  # Original unchanged
        assert modified.cache_enabled is False  # Copy has new value
        assert original.data == modified.data  # Other fields preserved
        assert original.computation_type == modified.computation_type

    def test_frozen_prevents_metadata_modification(self) -> None:
        """Verify frozen model prevents metadata field modification."""
        input_model = ModelComputeInput(
            data="test_data",
            metadata={"key": "value"},
        )
        with pytest.raises(ValidationError):
            input_model.metadata = {"new_key": "new_value"}  # type: ignore[misc]

    def test_frozen_prevents_computation_type_modification(self) -> None:
        """Verify frozen model prevents computation_type modification."""
        input_model = ModelComputeInput(
            data="test_data",
            computation_type="original_type",
        )
        with pytest.raises(ValidationError):
            input_model.computation_type = "modified_type"  # type: ignore[misc]

    def test_frozen_prevents_cache_enabled_modification(self) -> None:
        """Verify frozen model prevents cache_enabled modification."""
        input_model = ModelComputeInput(
            data="test_data",
            cache_enabled=True,
        )
        with pytest.raises(ValidationError):
            input_model.cache_enabled = False  # type: ignore[misc]

    def test_frozen_prevents_parallel_enabled_modification(self) -> None:
        """Verify frozen model prevents parallel_enabled modification."""
        input_model = ModelComputeInput(
            data="test_data",
            parallel_enabled=False,
        )
        with pytest.raises(ValidationError):
            input_model.parallel_enabled = True  # type: ignore[misc]

    def test_model_copy_deep_copies_data(self) -> None:
        """Verify model_copy creates independent copies with deep=True."""
        original = ModelComputeInput(
            data={"nested": {"key": "value"}},
            computation_type="test",
        )

        # Create a deep copy
        copied = original.model_copy(deep=True)

        # Verify they are equal
        assert original.data == copied.data
        assert original.operation_id == copied.operation_id

        # Verify independence - modifying copy's nested data doesn't affect original
        # NOTE: This is allowed because the model is frozen (field reassignment blocked)
        # but the nested dict content is mutable (shallow immutability)
        copied.data["nested"]["key"] = "modified"
        assert original.data["nested"]["key"] == "value"  # Original unchanged
        assert copied.data["nested"]["key"] == "modified"  # Copy was modified

    def test_multiple_extra_fields_all_rejected(self) -> None:
        """Verify multiple extra fields are all rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ModelComputeInput(
                data="test_data",
                extra_field_1="fail",  # type: ignore[call-arg]
                extra_field_2="also_fail",  # type: ignore[call-arg]
            )
        assert (
            "extra" in str(exc_info.value).lower()
            or "unexpected" in str(exc_info.value).lower()
        )

    def test_generic_type_parameter_works_with_frozen(self) -> None:
        """Verify generic type parameter T_Input works with frozen model."""
        # Test with dict
        dict_input: ModelComputeInput[dict[str, int]] = ModelComputeInput(
            data={"count": 42},
            computation_type="dict_processing",
        )
        assert dict_input.data == {"count": 42}

        # Test with list
        list_input: ModelComputeInput[list[str]] = ModelComputeInput(
            data=["a", "b", "c"],
            computation_type="list_processing",
        )
        assert list_input.data == ["a", "b", "c"]

        # Both should be frozen
        with pytest.raises(ValidationError):
            dict_input.data = {"count": 100}  # type: ignore[misc]
        with pytest.raises(ValidationError):
            list_input.data = ["x", "y", "z"]  # type: ignore[misc]
