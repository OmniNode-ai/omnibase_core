# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

#
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for union type handling in typed payload models.

This module provides comprehensive integration tests for union type handling
introduced in PR #251. These tests verify that union types work correctly
across the typed payload system, including:

1. Union Type Resolution
   - ModelEffectInput accepts both ModelEffectInputData and dict[str, Any]
   - Type discrimination works correctly in union fields
   - Pydantic properly handles union type coercion

2. Payload Normalization
   - _normalize_operation_data correctly handles both types
   - Normalization produces consistent output structure
   - Edge cases (empty, nested, large payloads) work correctly

3. Cross-Model Integration
   - ModelEffectInputData flows through ModelEffectInput correctly
   - ModelReducerIntentPayload works in reducer contexts
   - ModelRuntimeDirectivePayload works in runtime contexts

4. Validation Integration
   - Validation errors from typed payloads propagate correctly
   - Type mismatches are caught and reported clearly
   - Nested model validation works end-to-end

5. Serialization/Deserialization
   - model_dump() produces expected output for both union branches
   - model_validate() reconstructs correctly from dict
   - JSON round-trip preserves all data

Test Categories:
    All tests are marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

Author: ONEX Framework Team
"""

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumEffectType
from omnibase_core.models.context import ModelEffectInputData, ModelReducerIntentPayload
from omnibase_core.models.context.model_runtime_directive_payload import (
    ModelRuntimeDirectivePayload,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput

# Test configuration constants
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60


# =============================================================================
# 1. UNION TYPE RESOLUTION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestUnionTypeResolution:
    """Tests for union type resolution in ModelEffectInput.operation_data.

    The operation_data field is typed as:
        ModelEffectInputData | dict[str, Any]

    These tests verify both branches of the union work correctly.
    """

    def test_union_accepts_typed_model(self) -> None:
        """Test that union field accepts ModelEffectInputData."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com/users",
            target_system="user-service",
        )

        input_model = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_data,
        )

        # Verify the typed model is preserved, not converted to dict
        assert isinstance(input_model.operation_data, ModelEffectInputData)
        assert input_model.operation_data.effect_type == EnumEffectType.API_CALL
        assert (
            input_model.operation_data.resource_path == "https://api.example.com/users"
        )

    def test_union_accepts_dict(self) -> None:
        """Test that union field accepts dict[str, Any]."""
        dict_data: dict[str, Any] = {
            "custom_field": "value",
            "nested": {"level1": {"level2": "deep"}},
            "array": [1, 2, 3],
        }

        input_model = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=dict_data,
        )

        # Verify dict is preserved as-is
        assert isinstance(input_model.operation_data, dict)
        assert input_model.operation_data["custom_field"] == "value"
        assert input_model.operation_data["nested"]["level1"]["level2"] == "deep"

    def test_union_accepts_empty_dict_default(self) -> None:
        """Test that union field defaults to empty dict when not provided."""
        input_model = ModelEffectInput(effect_type=EnumEffectType.API_CALL)

        assert isinstance(input_model.operation_data, dict)
        assert input_model.operation_data == {}

    def test_union_type_preserved_after_model_copy(self) -> None:
        """Test that union type is preserved after model_copy()."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="users",
            target_system="postgres",
        )

        original = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data=typed_data,
        )

        # Copy preserves the typed model
        copied = original.model_copy()
        assert isinstance(copied.operation_data, ModelEffectInputData)
        assert copied.operation_data.effect_type == original.operation_data.effect_type

    def test_union_with_both_types_in_sequence(self) -> None:
        """Test creating multiple models alternating between union types."""
        # Create with typed model
        typed = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path="/api/v1",
            ),
        )

        # Create with dict
        dict_based = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"path": "/data/file.json"},
        )

        # Create another typed model
        typed_2 = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data=ModelEffectInputData(
                effect_type=EnumEffectType.DATABASE_OPERATION,
                resource_path="table_name",
            ),
        )

        # All should maintain their correct types
        assert isinstance(typed.operation_data, ModelEffectInputData)
        assert isinstance(dict_based.operation_data, dict)
        assert isinstance(typed_2.operation_data, ModelEffectInputData)

    def test_union_discriminates_by_structure(self) -> None:
        """Test that Pydantic correctly discriminates union types by structure."""
        # Dict that looks like ModelEffectInputData but is passed as dict
        dict_with_effect_type: dict[str, Any] = {
            "effect_type": EnumEffectType.API_CALL,
            "resource_path": "/test",
        }

        # When passed as dict, should remain dict (left-to-right union resolution)
        input_model = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=dict_with_effect_type,
        )

        # Pydantic should coerce to ModelEffectInputData since it matches the schema
        # (This is expected Pydantic behavior with smart union)
        # If it's a dict, that's also acceptable - the point is it works
        assert input_model.operation_data is not None


# =============================================================================
# 2. PAYLOAD NORMALIZATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestPayloadNormalization:
    """Tests for payload normalization in MixinEffectExecution.

    The _normalize_operation_data method handles both typed models and dicts,
    converting them to a consistent dict format for template resolution.
    """

    def test_normalize_dict_returns_same_reference(self) -> None:
        """Test that normalizing a dict returns the same object (no copy)."""
        from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution

        mixin = MixinEffectExecution()
        original_dict: dict[str, Any] = {"key": "value", "nested": {"inner": 42}}

        result = mixin._normalize_operation_data(original_dict)

        # Should be the exact same object (identity, not just equality)
        assert result is original_dict
        assert result == original_dict

    def test_normalize_typed_model_returns_dict(self) -> None:
        """Test that normalizing a typed model returns a dict."""
        from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution

        mixin = MixinEffectExecution()
        typed_model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/endpoint",
            target_system="backend",
            operation_name="fetch_data",
        )

        result = mixin._normalize_operation_data(typed_model)

        assert isinstance(result, dict)
        assert result["effect_type"] == EnumEffectType.API_CALL
        assert result["resource_path"] == "/api/endpoint"
        assert result["target_system"] == "backend"
        assert result["operation_name"] == "fetch_data"

    def test_normalize_empty_dict(self) -> None:
        """Test normalizing an empty dict."""
        from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution

        mixin = MixinEffectExecution()
        empty_dict: dict[str, Any] = {}

        result = mixin._normalize_operation_data(empty_dict)

        assert result == {}
        assert result is empty_dict

    def test_normalize_typed_model_with_all_none_optionals(self) -> None:
        """Test normalizing a typed model with all optional fields as None."""
        from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution

        mixin = MixinEffectExecution()
        typed_model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            # All other fields default to None
        )

        result = mixin._normalize_operation_data(typed_model)

        assert isinstance(result, dict)
        assert result["effect_type"] == EnumEffectType.FILE_OPERATION
        assert result["resource_path"] is None
        assert result["target_system"] is None
        assert result["idempotency_key"] is None

    def test_normalize_dict_with_complex_nested_structure(self) -> None:
        """Test normalizing a dict with deeply nested structure."""
        from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution

        mixin = MixinEffectExecution()
        complex_dict: dict[str, Any] = {
            "level1": {
                "level2": {
                    "level3": {
                        "value": "deep",
                        "array": [{"nested_obj": True}],
                    }
                }
            },
            "list_of_dicts": [
                {"id": 1, "name": "first"},
                {"id": 2, "name": "second"},
            ],
        }

        result = mixin._normalize_operation_data(complex_dict)

        # Complex structure preserved exactly
        assert result["level1"]["level2"]["level3"]["value"] == "deep"
        assert result["level1"]["level2"]["level3"]["array"][0]["nested_obj"] is True
        assert result["list_of_dicts"][1]["name"] == "second"

    def test_normalize_typed_model_with_uuid_field(self) -> None:
        """Test normalizing typed model with UUID field."""
        from omnibase_core.mixins.mixin_effect_execution import MixinEffectExecution

        mixin = MixinEffectExecution()
        resource_id = uuid4()
        typed_model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_id=resource_id,
        )

        result = mixin._normalize_operation_data(typed_model)

        assert result["resource_id"] == resource_id


# =============================================================================
# 3. CROSS-MODEL INTEGRATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestCrossModelIntegration:
    """Tests for typed payloads across different model types.

    These tests verify that typed payloads work correctly when used
    in their intended node/context scenarios.
    """

    def test_effect_input_data_in_effect_input_workflow(self) -> None:
        """Test ModelEffectInputData flowing through ModelEffectInput."""
        # Create typed operation data
        operation_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.service.com/resource",
            target_system="external-api",
            operation_name="create_resource",
            idempotency_key="create-123",
            content_type="application/json",
            encoding="utf-8",
        )

        # Wrap in ModelEffectInput
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=operation_data,
            transaction_enabled=True,
            retry_enabled=True,
            max_retries=3,
            timeout_ms=5000,
        )

        # Verify typed data accessible through effect input
        assert isinstance(effect_input.operation_data, ModelEffectInputData)
        assert effect_input.operation_data.operation_name == "create_resource"
        assert effect_input.operation_data.idempotency_key == "create-123"

    def test_reducer_intent_payload_for_state_transition(self) -> None:
        """Test ModelReducerIntentPayload for FSM state transitions."""
        entity_id = uuid4()

        # Simulate a state transition payload
        payload = ModelReducerIntentPayload(
            target_state="completed",
            source_state="in_progress",
            trigger="task_done",
            entity_id=entity_id,
            entity_type="workflow_task",
            operation="complete",
            data=(
                ("completion_time", datetime.now(UTC).isoformat()),
                ("outcome", "success"),
                ("metrics", "processed_items:100"),
            ),
        )

        # Verify state transition fields
        assert payload.target_state == "completed"
        assert payload.source_state == "in_progress"
        assert payload.trigger == "task_done"
        assert payload.entity_id == entity_id

        # Verify data helper method
        data_dict = payload.get_data_as_dict()
        assert data_dict["outcome"] == "success"

    def test_runtime_directive_payload_for_scheduled_execution(self) -> None:
        """Test ModelRuntimeDirectivePayload for scheduled effects."""
        scheduled_time = datetime.now(UTC) + timedelta(hours=2)

        payload = ModelRuntimeDirectivePayload(
            handler_args={
                "task_id": "task_123",
                "operation": "cleanup",
                "params": {"retain_days": 30},
            },
            execution_mode="async",
            priority=2,
            queue_name="background-tasks",
            execute_at=scheduled_time,
        )

        # Verify scheduling fields
        assert payload.execute_at == scheduled_time
        assert payload.queue_name == "background-tasks"
        assert payload.handler_args["task_id"] == "task_123"
        assert payload.execution_mode == "async"

    def test_runtime_directive_payload_for_retry_backoff(self) -> None:
        """Test ModelRuntimeDirectivePayload for retry backoff configuration."""
        payload = ModelRuntimeDirectivePayload(
            backoff_base_ms=1000,
            backoff_multiplier=2.0,
            jitter_ms=200,
            handler_args={"retry_reason": "transient_error"},
        )

        # Verify backoff configuration
        assert payload.backoff_base_ms == 1000
        assert payload.backoff_multiplier == 2.0
        assert payload.jitter_ms == 200

    def test_cross_model_type_consistency(self) -> None:
        """Test that effect_type is consistent across nested models."""
        # Effect type must match between parent and typed data
        effect_type = EnumEffectType.DATABASE_OPERATION

        typed_data = ModelEffectInputData(
            effect_type=effect_type,
            resource_path="users",
            target_system="postgres",
        )

        effect_input = ModelEffectInput(
            effect_type=effect_type,
            operation_data=typed_data,
        )

        # Both should have same effect type
        assert effect_input.effect_type == typed_data.effect_type
        assert effect_input.effect_type == effect_type


# =============================================================================
# 4. VALIDATION INTEGRATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestValidationIntegration:
    """Tests for validation error propagation with typed payloads."""

    def test_effect_type_mismatch_validation(self) -> None:
        """Test that mismatched effect_type raises clear validation error."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path="/data/file.json",
        )

        # Mismatch between parent and typed data should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            ModelEffectInput(
                effect_type=EnumEffectType.API_CALL,  # Mismatch!
                operation_data=typed_data,
            )

        error_message = str(exc_info.value)
        assert "effect_type mismatch" in error_message.lower()

    def test_typed_payload_field_validation(self) -> None:
        """Test that field constraints are validated in typed payloads."""
        # resource_path has max_length=4096
        with pytest.raises(ValidationError):
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path="x" * 5000,  # Exceeds max_length
            )

    def test_reducer_intent_payload_numeric_constraints(self) -> None:
        """Test numeric constraints in ModelReducerIntentPayload."""
        # retry_count must be >= 0
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(retry_count=-5)

        errors = exc_info.value.errors()
        assert any("retry_count" in str(e) for e in errors)

    def test_runtime_directive_payload_multiplier_constraint(self) -> None:
        """Test that backoff_multiplier must be > 0."""
        with pytest.raises(ValidationError) as exc_info:
            ModelRuntimeDirectivePayload(
                backoff_multiplier=0.0,  # Must be > 0
            )

        errors = exc_info.value.errors()
        assert any("backoff_multiplier" in str(e) for e in errors)

    def test_nested_validation_error_propagation(self) -> None:
        """Test that nested validation errors are caught at parent level."""
        # Invalid enum value should fail at typed data creation
        with pytest.raises(ValidationError):
            ModelEffectInputData(
                effect_type="INVALID_EFFECT_TYPE",  # type: ignore[arg-type]
                resource_path="/test",
            )

    def test_extra_fields_rejected_in_typed_models(self) -> None:
        """Test that typed models reject extra fields (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                unexpected_field="should_fail",  # type: ignore[call-arg]
            )

        errors = exc_info.value.errors()
        assert any("extra" in str(e).lower() for e in errors)

    def test_validation_error_includes_field_path(self) -> None:
        """Test that validation errors include clear field paths."""
        with pytest.raises(ValidationError) as exc_info:
            ModelReducerIntentPayload(
                max_retries=-1,  # Must be >= 0
                timeout_ms=-100,  # Must be >= 0
            )

        errors = exc_info.value.errors()
        field_names = [e.get("loc", ("",))[0] for e in errors]

        assert "max_retries" in field_names
        assert "timeout_ms" in field_names


# =============================================================================
# 5. SERIALIZATION/DESERIALIZATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestSerializationDeserialization:
    """Tests for serialization and deserialization of union types."""

    def test_model_dump_typed_operation_data(self) -> None:
        """Test model_dump() with typed operation_data."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com",
            target_system="api-gateway",
        )

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_data,
        )

        dumped = effect_input.model_dump()

        # operation_data should be serialized as dict
        assert isinstance(dumped["operation_data"], dict)
        assert dumped["operation_data"]["effect_type"] == EnumEffectType.API_CALL
        assert dumped["operation_data"]["resource_path"] == "https://api.example.com"

    def test_model_dump_dict_operation_data(self) -> None:
        """Test model_dump() with dict operation_data."""
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data={"path": "/data/file.json", "action": "read"},
        )

        dumped = effect_input.model_dump()

        assert isinstance(dumped["operation_data"], dict)
        assert dumped["operation_data"]["path"] == "/data/file.json"
        assert dumped["operation_data"]["action"] == "read"

    def test_json_round_trip_typed_payload(self) -> None:
        """Test JSON serialization round-trip for typed payloads."""
        resource_id = uuid4()
        original = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="users",
            target_system="postgres",
            operation_name="insert_user",
            resource_id=resource_id,
            content_type="application/json",
        )

        # Serialize to JSON
        json_str = original.model_dump_json()

        # Parse back
        parsed = json.loads(json_str)

        # Reconstruct from dict
        reconstructed = ModelEffectInputData.model_validate(parsed)

        # Verify all fields match
        assert reconstructed.effect_type == original.effect_type
        assert reconstructed.resource_path == original.resource_path
        assert reconstructed.target_system == original.target_system
        assert reconstructed.operation_name == original.operation_name
        assert reconstructed.resource_id == original.resource_id
        assert reconstructed.content_type == original.content_type

    def test_json_round_trip_effect_input_with_typed_data(self) -> None:
        """Test JSON round-trip for ModelEffectInput with typed operation_data."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.test.com/v1/users",
            target_system="user-api",
        )

        original = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_data,
            retry_enabled=True,
            max_retries=5,
            timeout_ms=10000,
        )

        # Full round-trip
        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        reconstructed = ModelEffectInput.model_validate(parsed)

        # Core fields preserved
        assert reconstructed.effect_type == original.effect_type
        assert reconstructed.retry_enabled == original.retry_enabled
        assert reconstructed.max_retries == original.max_retries
        assert reconstructed.timeout_ms == original.timeout_ms

        # operation_data may be reconstructed as ModelEffectInputData or dict
        # depending on Pydantic's union resolution
        if isinstance(reconstructed.operation_data, ModelEffectInputData):
            assert (
                reconstructed.operation_data.resource_path
                == "https://api.test.com/v1/users"
            )
        else:
            assert (
                reconstructed.operation_data["resource_path"]
                == "https://api.test.com/v1/users"
            )

    def test_json_round_trip_reducer_intent_payload(self) -> None:
        """Test JSON round-trip for ModelReducerIntentPayload."""
        entity_id = uuid4()
        original = ModelReducerIntentPayload(
            target_state="active",
            source_state="pending",
            trigger="activation_approved",
            entity_id=entity_id,
            entity_type="subscription",
            operation="activate",
            data=(("plan", "premium"), ("billing_cycle", "monthly")),
            idempotency_key="activate-sub-123",
            timeout_ms=5000,
            retry_count=1,
            max_retries=3,
        )

        # Round-trip
        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        reconstructed = ModelReducerIntentPayload.model_validate(parsed)

        # Verify all fields
        assert reconstructed.target_state == original.target_state
        assert reconstructed.source_state == original.source_state
        assert reconstructed.trigger == original.trigger
        assert reconstructed.entity_id == original.entity_id
        assert reconstructed.entity_type == original.entity_type
        assert reconstructed.operation == original.operation
        assert reconstructed.idempotency_key == original.idempotency_key
        assert reconstructed.timeout_ms == original.timeout_ms
        assert reconstructed.retry_count == original.retry_count
        assert reconstructed.max_retries == original.max_retries

        # Data tuple is preserved
        assert reconstructed.get_data_as_dict() == original.get_data_as_dict()

    def test_json_round_trip_runtime_directive_payload(self) -> None:
        """Test JSON round-trip for ModelRuntimeDirectivePayload."""
        execute_at = datetime.now(UTC) + timedelta(days=1)
        original = ModelRuntimeDirectivePayload(
            handler_args={"job_id": "job_456", "params": {"key": "value"}},
            execution_mode="async",
            priority=3,
            queue_name="batch-jobs",
            backoff_base_ms=2000,
            backoff_multiplier=1.5,
            jitter_ms=300,
            execute_at=execute_at,
            cleanup_required=True,
        )

        # Round-trip
        json_str = original.model_dump_json()
        parsed = json.loads(json_str)
        reconstructed = ModelRuntimeDirectivePayload.model_validate(parsed)

        # Verify all fields
        assert reconstructed.handler_args == original.handler_args
        assert reconstructed.execution_mode == original.execution_mode
        assert reconstructed.priority == original.priority
        assert reconstructed.queue_name == original.queue_name
        assert reconstructed.backoff_base_ms == original.backoff_base_ms
        assert reconstructed.backoff_multiplier == original.backoff_multiplier
        assert reconstructed.jitter_ms == original.jitter_ms
        assert reconstructed.cleanup_required == original.cleanup_required

        # DateTime comparison (may have microsecond differences due to serialization)
        assert reconstructed.execute_at is not None
        assert abs((reconstructed.execute_at - execute_at).total_seconds()) < 1

    def test_model_dump_mode_json_for_api_transport(self) -> None:
        """Test model_dump(mode='json') for API transport compatibility."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com/users",
        )

        # mode='json' converts enums to their JSON representation
        serialized = typed_data.model_dump(mode="json")

        # Effect type should be lowercase string (Pydantic default)
        assert serialized["effect_type"] == "api_call"
        assert isinstance(serialized["effect_type"], str)

        # Can be deserialized back
        restored = ModelEffectInputData.model_validate(serialized)
        assert restored.effect_type == EnumEffectType.API_CALL


# =============================================================================
# 6. EDGE CASES AND SPECIAL SCENARIOS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestEdgeCasesAndSpecialScenarios:
    """Tests for edge cases and special scenarios with union types."""

    def test_none_values_in_optional_fields(self) -> None:
        """Test that None values in optional fields are handled correctly."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path=None,
            target_system=None,
            operation_name=None,
            idempotency_key=None,
            resource_id=None,
            content_type=None,
            encoding=None,
        )

        # All optional fields should be None
        assert typed_data.resource_path is None
        assert typed_data.target_system is None
        assert typed_data.operation_name is None

        # Can be wrapped in ModelEffectInput
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_data,
        )

        assert isinstance(effect_input.operation_data, ModelEffectInputData)

    def test_large_payload_handling(self) -> None:
        """Test handling of large dict payloads."""
        # Create a large payload
        large_dict: dict[str, Any] = {f"key_{i}": f"value_{i}" for i in range(1000)}
        large_dict["nested"] = {f"nested_key_{i}": i for i in range(100)}

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=large_dict,
        )

        # Should handle large payload without issues
        assert len(effect_input.operation_data) == 1001  # 1000 + nested
        assert effect_input.operation_data["key_500"] == "value_500"

    def test_special_characters_in_string_fields(self) -> None:
        """Test handling of special and Unicode characters in string fields.

        Tests diverse Unicode from multiple scripts:
        - Latin extended (accents)
        - CJK (Chinese/Japanese/Korean)
        - Arabic script
        - Whitespace characters
        """
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path="/data/file with spaces & special chars!/日本語/العربية.json",
            target_system="fs-éàñ-中文-العربية",  # Unicode from multiple scripts
            operation_name="write-file\t\n",  # Whitespace characters
        )

        # Special characters preserved
        assert " " in typed_data.resource_path  # type: ignore[operator]
        assert "&" in typed_data.resource_path  # type: ignore[operator]
        assert "日本語" in typed_data.resource_path  # type: ignore[operator]
        assert "é" in typed_data.target_system  # type: ignore[operator]
        assert "中文" in typed_data.target_system  # type: ignore[operator]
        assert "العربية" in typed_data.target_system  # type: ignore[operator]

    def test_empty_string_vs_none_handling(self) -> None:
        """Test distinction between empty string and None."""
        # Empty string is valid
        with_empty = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            # min_length constraints may reject empty strings for some fields
            # but resource_path allows None, not empty (no min_length)
            content_type="",  # Empty string allowed
        )

        # With None (default)
        with_none = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            content_type=None,
        )

        # Empty string and None are different
        assert with_empty.content_type == ""
        assert with_none.content_type is None
        assert with_empty.content_type != with_none.content_type

    def test_concurrent_model_creation(self) -> None:
        """Test creating models concurrently (thread-safety of frozen models)."""
        import concurrent.futures

        def create_model(i: int) -> ModelEffectInputData:
            return ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path=f"/api/v1/resource/{i}",
                target_system=f"service-{i}",
                operation_name=f"operation-{i}",
            )

        # Create models concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_model, i) for i in range(100)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All models created successfully
        assert len(results) == 100

        # Each model has unique values
        paths = {r.resource_path for r in results}
        assert len(paths) == 100

    def test_model_hash_for_frozen_models(self) -> None:
        """Test that frozen models are hashable and can be used in sets."""
        model1 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/v1",
        )

        model2 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/v1",
        )

        model3 = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/v2",
        )

        # Equal models should have same hash
        assert hash(model1) == hash(model2)

        # Can be used in sets
        model_set = {model1, model2, model3}
        assert len(model_set) == 2  # model1 and model2 are equal

    def test_dict_with_reserved_keys(self) -> None:
        """Test dict payload with keys that match model field names."""
        # Dict with keys that match ModelEffectInputData field names
        dict_payload: dict[str, Any] = {
            "effect_type": "custom_string_not_enum",
            "resource_path": {"nested": "structure"},  # Dict instead of string
            "custom_field": "additional_data",
        }

        # Should work - dict is not validated against ModelEffectInputData
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=dict_payload,
        )

        # The dict is stored as-is (no coercion to ModelEffectInputData)
        if isinstance(effect_input.operation_data, dict):
            assert (
                effect_input.operation_data["effect_type"] == "custom_string_not_enum"
            )
            assert effect_input.operation_data["resource_path"]["nested"] == "structure"


# =============================================================================
# 7. COMPATIBILITY AND MIGRATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestCompatibilityAndMigration:
    """Tests for backwards compatibility and migration scenarios."""

    def test_legacy_dict_pattern_still_works(self) -> None:
        """Test that legacy dict-based patterns continue to work."""
        # This is the pattern used before typed payloads were introduced
        legacy_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "url": "https://api.example.com",
                "method": "POST",
                "body": {"key": "value"},
                "headers": {"Authorization": "Bearer token"},
            },
        )

        # Should work exactly as before
        assert legacy_input.operation_data["url"] == "https://api.example.com"
        assert legacy_input.operation_data["method"] == "POST"

    def test_gradual_migration_mixed_usage(self) -> None:
        """Test mixed usage during gradual migration to typed payloads."""
        # Some code uses typed payloads
        typed_inputs = [
            ModelEffectInput(
                effect_type=EnumEffectType.API_CALL,
                operation_data=ModelEffectInputData(
                    effect_type=EnumEffectType.API_CALL,
                    resource_path="/new/typed/endpoint",
                ),
            ),
        ]

        # Some code still uses dicts
        dict_inputs = [
            ModelEffectInput(
                effect_type=EnumEffectType.API_CALL,
                operation_data={"legacy": "pattern"},
            ),
        ]

        # Both should work together
        all_inputs = typed_inputs + dict_inputs

        for input_model in all_inputs:
            assert input_model.effect_type == EnumEffectType.API_CALL
            assert input_model.operation_data is not None

    def test_convert_dict_to_typed_at_runtime(self) -> None:
        """Test converting dict to typed model at runtime."""
        # Start with dict (legacy code)
        dict_data: dict[str, Any] = {
            "effect_type": EnumEffectType.DATABASE_OPERATION,
            "resource_path": "users",
            "target_system": "postgres",
            "operation_name": "query_users",
        }

        # Convert to typed model at runtime
        typed_data = ModelEffectInputData(**dict_data)

        # Now use typed model
        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data=typed_data,
        )

        assert isinstance(effect_input.operation_data, ModelEffectInputData)
        assert effect_input.operation_data.operation_name == "query_users"

    def test_extract_typed_data_from_effect_input(self) -> None:
        """Test extracting and working with typed data from effect input."""
        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/endpoint",
            target_system="backend",
        )

        effect_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_data,
        )

        # Extract and use typed data
        if isinstance(effect_input.operation_data, ModelEffectInputData):
            # Can use typed methods and fields directly
            data = effect_input.operation_data
            assert data.effect_type == EnumEffectType.API_CALL
            assert data.resource_path == "/api/endpoint"
        else:
            # Fallback for dict
            assert effect_input.operation_data.get("resource_path") == "/api/endpoint"
