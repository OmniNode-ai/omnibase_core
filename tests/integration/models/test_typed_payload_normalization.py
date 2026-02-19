# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Normalization and type conversion tests for typed payload models.

This module tests the normalization logic and type conversion behavior of typed
payload models. It focuses on:

1. Normalization Logic Tests
    - Tests the _normalize_operation_data method in MixinEffectExecution
    - Verifies consistent outputs from typed and dict inputs

2. Type Coercion/Conversion Tests
    - Tests dict to typed model conversion
    - Tests model_dump() produces expected dict structure
    - Tests round-trip: dict -> model -> dict

3. Immutability Tests
    - Verifies frozen model behavior
    - Tests that modifications raise ValidationError

4. Helper Method Tests
    - Tests get_data_as_dict() method
    - Tests is_retryable() method
    - Tests with_incremented_retry() method

Note:
    Integration tests using fixtures from conftest.py should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

from typing import Any
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumEffectType
from omnibase_core.models.context import (
    ModelEffectInputData,
    ModelReducerIntentPayload,
)
from omnibase_core.models.context.model_runtime_directive_payload import (
    ModelRuntimeDirectivePayload,
)
from omnibase_core.nodes.node_effect import NodeEffect

from .conftest import INTEGRATION_TEST_TIMEOUT_SECONDS

# =============================================================================
# NORMALIZATION LOGIC TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestNormalizationLogic:
    """Tests for the _normalize_operation_data method in MixinEffectExecution."""

    def test_normalize_dict_input_returns_same_dict(
        self,
        effect_node: NodeEffect,
    ) -> None:
        """Test that dict input is returned as-is."""
        dict_input: dict[str, Any] = {"id": "123", "name": "test"}

        # Access the mixin's normalization method
        result = effect_node._normalize_operation_data(dict_input)

        assert result == dict_input
        assert result is dict_input  # Same object, not a copy

    def test_normalize_typed_model_returns_dict(
        self,
        effect_node: NodeEffect,
    ) -> None:
        """Test that typed ModelEffectInputData is normalized to dict."""
        typed_input = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com/users",
            target_system="user-service",
            operation_name="create_user",
        )

        result = effect_node._normalize_operation_data(typed_input)

        # Result should be a dict
        assert isinstance(result, dict)
        # Dict should contain the model's fields
        assert result["effect_type"] == EnumEffectType.API_CALL
        assert result["resource_path"] == "https://api.example.com/users"
        assert result["target_system"] == "user-service"
        assert result["operation_name"] == "create_user"

    def test_normalize_produces_consistent_outputs(
        self,
        effect_node: NodeEffect,
    ) -> None:
        """Test that normalization produces consistent dict structure."""
        # Create equivalent dict and typed model
        dict_input: dict[str, Any] = {
            "effect_type": EnumEffectType.API_CALL,
            "resource_path": "https://api.example.com/test",
            "target_system": "test-service",
            "operation_name": "test_op",
            "idempotency_key": None,
            "resource_id": None,
            "content_type": None,
            "encoding": None,
        }

        typed_input = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com/test",
            target_system="test-service",
            operation_name="test_op",
        )

        dict_result = effect_node._normalize_operation_data(dict_input)
        typed_result = effect_node._normalize_operation_data(typed_input)

        # Both should be dicts
        assert isinstance(dict_result, dict)
        assert isinstance(typed_result, dict)

        # Key fields should match
        assert dict_result["effect_type"] == typed_result["effect_type"]
        assert dict_result["resource_path"] == typed_result["resource_path"]
        assert dict_result["target_system"] == typed_result["target_system"]
        assert dict_result["operation_name"] == typed_result["operation_name"]


# =============================================================================
# TYPE COERCION/CONVERSION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestTypeCoercionConversion:
    """Tests for type coercion and conversion between dict and typed models."""

    def test_dict_to_model_effect_input_data(self) -> None:
        """Test converting dict to ModelEffectInputData."""
        source_dict = {
            "effect_type": EnumEffectType.API_CALL,
            "resource_path": "https://api.example.com",
            "target_system": "api-service",
            "operation_name": "fetch_data",
            "idempotency_key": "key_123",
            "content_type": "application/json",
            "encoding": "utf-8",
        }

        # Convert dict to typed model
        model = ModelEffectInputData(**source_dict)

        # Verify all fields transferred correctly
        assert model.effect_type == EnumEffectType.API_CALL
        assert model.resource_path == "https://api.example.com"
        assert model.target_system == "api-service"
        assert model.operation_name == "fetch_data"
        assert model.idempotency_key == "key_123"
        assert model.content_type == "application/json"
        assert model.encoding == "utf-8"

    def test_model_dump_produces_expected_dict(self) -> None:
        """Test that model_dump() produces expected dict structure."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="users",
            target_system="postgres",
            operation_name="insert_user",
        )

        result = model.model_dump()

        assert isinstance(result, dict)
        assert result["effect_type"] == EnumEffectType.DATABASE_OPERATION
        assert result["resource_path"] == "users"
        assert result["target_system"] == "postgres"
        assert result["operation_name"] == "insert_user"
        # Optional fields should be present with None values
        assert "idempotency_key" in result
        assert "resource_id" in result
        assert "content_type" in result
        assert "encoding" in result

    def test_round_trip_dict_to_model_to_dict(self) -> None:
        """Test round-trip: dict -> model -> dict maintains data."""
        resource_id = uuid4()
        original_dict = {
            "effect_type": EnumEffectType.FILE_OPERATION,
            "resource_path": "/data/file.json",
            "target_system": "local-fs",
            "operation_name": "write_file",
            "idempotency_key": "file_write_001",
            "resource_id": resource_id,
            "content_type": "application/json",
            "encoding": "utf-8",
        }

        # Round-trip: dict -> model -> dict
        model = ModelEffectInputData(**original_dict)
        result_dict = model.model_dump()

        # All values should be preserved
        assert result_dict["effect_type"] == original_dict["effect_type"]
        assert result_dict["resource_path"] == original_dict["resource_path"]
        assert result_dict["target_system"] == original_dict["target_system"]
        assert result_dict["operation_name"] == original_dict["operation_name"]
        assert result_dict["idempotency_key"] == original_dict["idempotency_key"]
        assert result_dict["resource_id"] == original_dict["resource_id"]
        assert result_dict["content_type"] == original_dict["content_type"]
        assert result_dict["encoding"] == original_dict["encoding"]

    def test_reducer_intent_payload_round_trip(self) -> None:
        """Test round-trip for ModelReducerIntentPayload."""
        entity_id = uuid4()
        original = ModelReducerIntentPayload(
            target_state="completed",
            source_state="processing",
            trigger="task_finished",
            entity_id=entity_id,
            entity_type="task",
            operation="complete",
            data=(("result", "success"), ("count", 42)),
            idempotency_key="task_complete_001",
            timeout_ms=10000,
            retry_count=1,
            max_retries=5,
        )

        # Round-trip
        dumped = original.model_dump()
        restored = ModelReducerIntentPayload(**dumped)

        # Verify all fields preserved
        assert restored.target_state == original.target_state
        assert restored.source_state == original.source_state
        assert restored.trigger == original.trigger
        assert restored.entity_id == original.entity_id
        assert restored.entity_type == original.entity_type
        assert restored.operation == original.operation
        assert restored.data == original.data
        assert restored.idempotency_key == original.idempotency_key
        assert restored.timeout_ms == original.timeout_ms
        assert restored.retry_count == original.retry_count
        assert restored.max_retries == original.max_retries

    def test_runtime_directive_payload_round_trip(self) -> None:
        """Test round-trip for ModelRuntimeDirectivePayload."""
        from datetime import UTC, datetime, timedelta

        execute_at = datetime.now(UTC) + timedelta(hours=1)
        original = ModelRuntimeDirectivePayload(
            handler_args={"action": "process", "priority": 1},
            execution_mode="async",
            priority=2,
            queue_name="default",
            backoff_base_ms=500,
            backoff_multiplier=1.5,
            jitter_ms=50,
            execute_at=execute_at,
            cancellation_reason=None,
            cleanup_required=True,
        )

        # Round-trip
        dumped = original.model_dump()
        restored = ModelRuntimeDirectivePayload(**dumped)

        # Verify all fields preserved
        assert restored.handler_args == original.handler_args
        assert restored.execution_mode == original.execution_mode
        assert restored.priority == original.priority
        assert restored.queue_name == original.queue_name
        assert restored.backoff_base_ms == original.backoff_base_ms
        assert restored.backoff_multiplier == original.backoff_multiplier
        assert restored.jitter_ms == original.jitter_ms
        assert restored.execute_at == original.execute_at
        assert restored.cancellation_reason == original.cancellation_reason
        assert restored.cleanup_required == original.cleanup_required


# =============================================================================
# IMMUTABILITY TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestImmutability:
    """Tests for frozen model immutability."""

    def test_model_effect_input_data_is_immutable(self) -> None:
        """Test that ModelEffectInputData is frozen."""
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/test",
        )

        with pytest.raises(ValidationError):
            model.resource_path = "/modified"

    def test_reducer_intent_payload_is_immutable(self) -> None:
        """Test that ModelReducerIntentPayload is frozen."""
        payload = ModelReducerIntentPayload(
            target_state="active",
            entity_type="user",
        )

        with pytest.raises(ValidationError):
            payload.target_state = "inactive"

    def test_runtime_directive_payload_is_immutable(self) -> None:
        """Test that ModelRuntimeDirectivePayload is frozen."""
        payload = ModelRuntimeDirectivePayload(
            priority=1,
        )

        with pytest.raises(ValidationError):
            payload.priority = 2

    def test_reducer_intent_payload_with_incremented_retry_creates_new_instance(
        self,
    ) -> None:
        """Test that with_incremented_retry returns a new instance."""
        original = ModelReducerIntentPayload(retry_count=1, max_retries=5)
        incremented = original.with_incremented_retry()

        # Original should be unchanged
        assert original.retry_count == 1

        # New instance should have incremented retry count
        assert incremented.retry_count == 2
        assert incremented is not original


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestHelperMethods:
    """Tests for helper methods on typed payload models."""

    def test_reducer_intent_payload_get_data_as_dict(self) -> None:
        """Test get_data_as_dict() helper method."""
        payload = ModelReducerIntentPayload(
            data=(("key1", "value1"), ("key2", 42), ("key3", True)),
        )

        result = payload.get_data_as_dict()

        assert result == {"key1": "value1", "key2": 42, "key3": True}
        assert isinstance(result, dict)

    def test_reducer_intent_payload_is_retryable(self) -> None:
        """Test is_retryable() helper method."""
        # Retryable case
        retryable = ModelReducerIntentPayload(retry_count=2, max_retries=5)
        assert retryable.is_retryable() is True

        # Not retryable case (at max)
        exhausted = ModelReducerIntentPayload(retry_count=5, max_retries=5)
        assert exhausted.is_retryable() is False

        # Not retryable case (over max)
        over_max = ModelReducerIntentPayload(retry_count=6, max_retries=5)
        assert over_max.is_retryable() is False

    def test_reducer_intent_payload_with_incremented_retry(self) -> None:
        """Test with_incremented_retry() helper method."""
        original = ModelReducerIntentPayload(
            target_state="processing",
            entity_type="task",
            retry_count=1,
            max_retries=5,
        )

        incremented = original.with_incremented_retry()

        # Verify retry count incremented
        assert incremented.retry_count == 2

        # Verify other fields preserved
        assert incremented.target_state == "processing"
        assert incremented.entity_type == "task"
        assert incremented.max_retries == 5
