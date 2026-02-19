# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Backward compatibility and union type handling tests for typed payload models.

This module tests the backward compatibility and union type discrimination behavior
of typed payload models. It focuses on:

1. Backwards Compatibility Tests
    - Ensures existing dict-based code continues to work
    - Validates union types accept both dict and typed model inputs

2. Union Type Discrimination Tests
    - Tests that union correctly identifies typed model vs dict at runtime
    - Tests edge cases with model-like dicts, empty dicts, and minimal models

3. Error Handling Tests
    - Tests validation errors for invalid structures
    - Tests clear error messages for type mismatches

Note:
    Integration tests using fixtures from conftest.py should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumEffectType, EnumTransactionState
from omnibase_core.models.context import (
    ModelEffectInputData,
    ModelReducerIntentPayload,
)
from omnibase_core.models.context.model_runtime_directive_payload import (
    ModelRuntimeDirectivePayload,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.effect.model_effect_output import ModelEffectOutput
from omnibase_core.nodes.node_effect import NodeEffect

from .conftest import INTEGRATION_TEST_TIMEOUT_SECONDS

# =============================================================================
# BACKWARDS COMPATIBILITY TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestBackwardsCompatibility:
    """Tests ensuring existing dict-based code continues to work."""

    def test_effect_input_accepts_plain_dict(
        self,
        effect_node: NodeEffect,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test that ModelEffectInput still accepts plain dict operation_data."""
        # This is the legacy pattern - must continue working
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "legacy_123", "extra_field": "value"},
            retry_enabled=False,
        )

        # Dict should be stored as-is
        assert isinstance(input_data.operation_data, dict)
        assert input_data.operation_data["id"] == "legacy_123"
        assert input_data.operation_data["extra_field"] == "value"

        # Should process successfully
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))
        assert result.transaction_state == EnumTransactionState.COMMITTED

    def test_union_type_accepts_dict_and_model(self) -> None:
        """Test that union type ModelEffectInputData | dict accepts both."""
        # Dict variant
        dict_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "123"},
        )
        assert isinstance(dict_input.operation_data, dict)

        # Typed model variant
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/test",
        )
        typed_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_data,
        )
        assert isinstance(typed_input.operation_data, ModelEffectInputData)

    def test_empty_dict_operation_data_works(
        self,
        effect_node: NodeEffect,
    ) -> None:
        """Test that empty dict operation_data is allowed (default)."""
        # Default factory creates empty dict
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
        )

        assert isinstance(input_data.operation_data, dict)
        assert input_data.operation_data == {}

    def test_nested_dict_structures_preserved(self) -> None:
        """Test that complex nested dict structures are preserved."""
        complex_dict: dict[str, Any] = {
            "id": "123",
            "nested": {
                "level1": {"level2": {"value": 42}},
                "array": [1, 2, 3],
            },
            "metadata": {
                "tags": ["a", "b"],
                "config": {"enabled": True},
            },
        }

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=complex_dict,
        )

        # Complex structure should be preserved
        assert input_data.operation_data["nested"]["level1"]["level2"]["value"] == 42
        assert input_data.operation_data["nested"]["array"] == [1, 2, 3]
        assert input_data.operation_data["metadata"]["config"]["enabled"] is True


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestErrorHandling:
    """Tests for error handling with typed payloads."""

    def test_effect_type_mismatch_raises_validation_error(self) -> None:
        """Test that mismatched effect_type between parent and data raises error."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="users",
        )

        # Parent effect_type differs from typed data effect_type
        with pytest.raises(ValueError, match="effect_type mismatch"):
            ModelEffectInput(
                effect_type=EnumEffectType.API_CALL,  # Mismatch!
                operation_data=typed_data,
            )

    def test_effect_type_consistency_validation_succeeds(self) -> None:
        """Test that matching effect_type values pass validation."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com",
        )

        # Should not raise - effect_types match
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_data,
        )

        assert input_data.effect_type == typed_data.effect_type

    def test_invalid_dict_to_typed_model_raises_validation_error(self) -> None:
        """Test that invalid dict structure raises validation error."""
        # Missing required field (effect_type)
        invalid_dict: dict[str, Any] = {
            "resource_path": "/test",
        }

        with pytest.raises(ValidationError):
            ModelEffectInputData(**invalid_dict)

    def test_invalid_enum_value_raises_validation_error(self) -> None:
        """Test that invalid enum value raises validation error."""
        invalid_dict: dict[str, Any] = {
            "effect_type": "INVALID_TYPE",  # Not a valid EnumEffectType
            "resource_path": "/test",
        }

        with pytest.raises(ValidationError):
            ModelEffectInputData(**invalid_dict)

    def test_reducer_intent_payload_validation_errors(self) -> None:
        """Test ModelReducerIntentPayload field validation."""
        # retry_count must be >= 0
        with pytest.raises(ValidationError):
            ModelReducerIntentPayload(retry_count=-1)

        # max_retries must be >= 0
        with pytest.raises(ValidationError):
            ModelReducerIntentPayload(max_retries=-1)

        # timeout_ms must be >= 0
        with pytest.raises(ValidationError):
            ModelReducerIntentPayload(timeout_ms=-1)

    def test_runtime_directive_payload_validation_errors(self) -> None:
        """Test ModelRuntimeDirectivePayload field validation."""
        # priority must be >= 0
        with pytest.raises(ValidationError):
            ModelRuntimeDirectivePayload(priority=-1)

        # backoff_base_ms must be >= 0
        with pytest.raises(ValidationError):
            ModelRuntimeDirectivePayload(backoff_base_ms=-1)

        # backoff_multiplier must be > 0
        with pytest.raises(ValidationError):
            ModelRuntimeDirectivePayload(backoff_multiplier=0.0)

        # jitter_ms must be >= 0
        with pytest.raises(ValidationError):
            ModelRuntimeDirectivePayload(jitter_ms=-1)

    def test_extra_fields_rejected_by_typed_models(self) -> None:
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError):
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path="/test",
                unknown_field="value",  # Extra field should be rejected
            )


# =============================================================================
# UNION TYPE DISCRIMINATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestUnionTypeDiscrimination:
    """Tests for union type discrimination edge cases."""

    def test_union_discriminates_typed_model_from_dict_correctly(self) -> None:
        """Test that union correctly identifies typed model vs dict at runtime."""
        # Dict variant - should be stored as dict
        dict_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"custom_key": "custom_value"},
        )

        # Typed model variant - should be stored as ModelEffectInputData
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/users",
        )
        typed_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_data,
        )

        # Runtime type discrimination should work correctly
        assert type(dict_input.operation_data) is dict
        assert type(typed_input.operation_data) is ModelEffectInputData

        # isinstance checks should also work
        assert isinstance(dict_input.operation_data, dict)
        assert isinstance(typed_input.operation_data, ModelEffectInputData)
        assert not isinstance(dict_input.operation_data, ModelEffectInputData)
        assert not isinstance(typed_input.operation_data, dict)

    def test_union_preserves_type_after_model_copy(self) -> None:
        """Test that model_copy preserves union type discrimination."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="users",
            target_system="postgres",
        )
        original = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data=typed_data,
        )

        # Copy should preserve the typed model
        copied = original.model_copy()
        assert isinstance(copied.operation_data, ModelEffectInputData)
        assert copied.operation_data.effect_type == EnumEffectType.DATABASE_OPERATION

        # Deep copy should also preserve types
        deep_copied = original.model_copy(deep=True)
        assert isinstance(deep_copied.operation_data, ModelEffectInputData)

    def test_union_with_dict_containing_model_like_keys(self) -> None:
        """Test that dict with model-like keys stays as dict."""
        # Dict that happens to have keys matching ModelEffectInputData
        ambiguous_dict: dict[str, Any] = {
            "effect_type": EnumEffectType.API_CALL,
            "resource_path": "/api/test",
            "target_system": "test",
            "extra_key_not_in_model": "extra_value",  # Dict should stay as dict
        }

        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=ambiguous_dict,
        )

        # Should remain a dict (not coerced to ModelEffectInputData)
        assert isinstance(input_data.operation_data, dict)
        assert "extra_key_not_in_model" in input_data.operation_data

    def test_union_with_empty_dict_vs_minimal_model(self) -> None:
        """Test discrimination between empty dict and minimal typed model."""
        # Empty dict
        empty_dict_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={},
        )

        # Minimal typed model (only required fields)
        minimal_model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
        )
        minimal_model_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=minimal_model,
        )

        # Type discrimination should be correct
        assert isinstance(empty_dict_input.operation_data, dict)
        assert len(empty_dict_input.operation_data) == 0
        assert isinstance(minimal_model_input.operation_data, ModelEffectInputData)

    def test_union_default_factory_produces_dict(self) -> None:
        """Test that default_factory produces empty dict, not typed model."""
        # No operation_data provided - should default to empty dict
        default_input = ModelEffectInput(effect_type=EnumEffectType.API_CALL)

        assert isinstance(default_input.operation_data, dict)
        assert default_input.operation_data == {}
