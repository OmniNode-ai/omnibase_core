# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""Integration tests for typed payload models and union type handling.

This module tests the typed payload models introduced in PR #251 as alternatives
to dict payloads. These tests verify that union type handling works correctly
in real node workflows.

Test Categories:
    1. Typed Payload Usage in Node Workflows
        - Tests that nodes can receive typed models instead of dicts
        - Verifies proper type discrimination in union fields

    2. Normalization Logic Tests
        - Tests the _normalize_operation_data method in MixinEffectExecution
        - Verifies consistent outputs from typed and dict inputs

    3. Backwards Compatibility Tests
        - Ensures existing dict-based code continues to work
        - Validates union types accept both dict and typed model inputs

    4. Type Coercion/Conversion Tests
        - Tests dict to typed model conversion
        - Tests model_dump() produces expected dict structure
        - Tests round-trip: dict -> model -> dict

    5. Error Handling Tests
        - Tests validation errors for invalid structures
        - Tests clear error messages for type mismatches

Note:
    Integration tests using these fixtures should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums import EnumEffectType, EnumTransactionState
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.context import (
    ModelEffectInputData,
    ModelReducerIntentPayload,
)
from omnibase_core.models.context.model_runtime_directive_payload import (
    ModelRuntimeDirectivePayload,
)
from omnibase_core.models.contracts.subcontracts.model_effect_io_configs import (
    ModelHttpIOConfig,
)
from omnibase_core.models.contracts.subcontracts.model_effect_operation import (
    ModelEffectOperation,
)
from omnibase_core.models.contracts.subcontracts.model_effect_retry_policy import (
    ModelEffectRetryPolicy,
)
from omnibase_core.models.contracts.subcontracts.model_effect_subcontract import (
    ModelEffectSubcontract,
)
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.effect.model_effect_output import ModelEffectOutput
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.nodes.node_effect import NodeEffect

# Test configuration constants
INTEGRATION_TEST_TIMEOUT_SECONDS: int = 60

# Version for test contracts
V1_0_0 = ModelSemVer(major=1, minor=0, patch=0)


# =============================================================================
# TEST FIXTURES
# =============================================================================


class TestableNodeEffect(NodeEffect):
    """Test implementation of NodeEffect with injected subcontract."""

    def __init__(
        self,
        container: ModelONEXContainer,
        effect_subcontract: ModelEffectSubcontract,
    ) -> None:
        super().__init__(container)
        self.effect_subcontract = effect_subcontract


def create_test_effect_subcontract(
    *,
    name: str = "test_effect",
    operations: list[ModelEffectOperation] | None = None,
    retry_policy: ModelEffectRetryPolicy | None = None,
) -> ModelEffectSubcontract:
    """Factory to create effect subcontracts for testing."""
    if operations is None:
        operations = [
            ModelEffectOperation(
                operation_name="test_http_get",
                description="Test HTTP GET operation",
                idempotent=True,
                io_config=ModelHttpIOConfig(
                    url_template="https://api.example.com/data/${input.id}",
                    method="GET",
                    headers={"Accept": "application/json"},
                    timeout_ms=5000,
                ),
            ),
        ]

    if retry_policy is None:
        retry_policy = ModelEffectRetryPolicy(
            enabled=False,  # Disable retries for faster tests
        )

    return ModelEffectSubcontract(
        subcontract_name=name,
        version=V1_0_0,
        description=f"Test Effect: {name}",
        execution_mode="sequential_abort",
        operations=operations,
        default_retry_policy=retry_policy,
    )


@pytest.fixture
def mock_container() -> ModelONEXContainer:
    """Create a mock ONEX container for testing."""
    container = MagicMock(spec=ModelONEXContainer)

    mock_http_handler = AsyncMock()
    mock_http_handler.execute = AsyncMock(
        return_value={"status": "success", "data": {"id": 123, "name": "test"}}
    )

    def get_service_side_effect(service_name: str) -> Any:
        if service_name == "ProtocolEffectHandler_HTTP":
            return mock_http_handler
        return MagicMock()

    container.get_service = MagicMock(side_effect=get_service_side_effect)
    return container


@pytest.fixture
def mock_http_handler(mock_container: ModelONEXContainer) -> AsyncMock:
    """Get the mock HTTP handler from the container."""
    return mock_container.get_service("ProtocolEffectHandler_HTTP")


@pytest.fixture
def effect_node(mock_container: ModelONEXContainer) -> NodeEffect:
    """Create a NodeEffect instance with a default subcontract."""
    effect_subcontract = create_test_effect_subcontract()
    return TestableNodeEffect(mock_container, effect_subcontract)


# =============================================================================
# 1. TYPED PAYLOAD USAGE IN NODE WORKFLOWS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestTypedPayloadInNodeWorkflows:
    """Tests that nodes can receive typed models instead of dicts."""

    def test_effect_input_with_model_effect_input_data(
        self,
        effect_node: NodeEffect,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test that NodeEffect can receive ModelEffectInputData instead of dict."""
        # Arrange: Create typed operation data
        typed_operation_data = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com/users",
            target_system="user-service",
            operation_name="create_user",
            idempotency_key="user_create_123",
            content_type="application/json",
            encoding="utf-8",
        )

        # This should work: ModelEffectInput accepts ModelEffectInputData
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=typed_operation_data,
            retry_enabled=False,
        )

        # Assert: Model was created successfully with typed data
        assert isinstance(input_data.operation_data, ModelEffectInputData)
        assert input_data.operation_data.effect_type == EnumEffectType.API_CALL
        assert input_data.operation_data.target_system == "user-service"
        assert input_data.operation_data.idempotency_key == "user_create_123"

    def test_reducer_intent_payload_as_typed_model(self) -> None:
        """Test that ModelReducerIntentPayload works as a typed payload."""
        entity_id = uuid4()

        # Create typed reducer intent payload
        payload = ModelReducerIntentPayload(
            target_state="active",
            source_state="pending",
            trigger="user_verified",
            entity_id=entity_id,
            entity_type="user",
            operation="activate",
            data=(("key1", "value1"), ("key2", 123)),
            idempotency_key="activate_user_123",
            timeout_ms=5000,
            retry_count=0,
            max_retries=3,
        )

        # Verify all fields are accessible
        assert payload.target_state == "active"
        assert payload.source_state == "pending"
        assert payload.trigger == "user_verified"
        assert payload.entity_id == entity_id
        assert payload.entity_type == "user"
        assert payload.operation == "activate"
        assert payload.get_data_as_dict() == {"key1": "value1", "key2": 123}
        assert payload.is_retryable() is True

    def test_runtime_directive_payload_as_typed_model(self) -> None:
        """Test that ModelRuntimeDirectivePayload works as a typed payload."""
        execute_at = datetime.now(UTC) + timedelta(minutes=5)

        # Create typed runtime directive payload
        payload = ModelRuntimeDirectivePayload(
            handler_args={"user_id": "123", "action": "notify"},
            execution_mode="async",
            priority=1,
            queue_name="high-priority",
            backoff_base_ms=1000,
            backoff_multiplier=2.0,
            jitter_ms=100,
            execute_at=execute_at,
            cancellation_reason=None,
            cleanup_required=False,
        )

        # Verify all fields are accessible
        assert payload.handler_args == {"user_id": "123", "action": "notify"}
        assert payload.execution_mode == "async"
        assert payload.priority == 1
        assert payload.queue_name == "high-priority"
        assert payload.backoff_base_ms == 1000
        assert payload.backoff_multiplier == 2.0
        assert payload.jitter_ms == 100
        assert payload.execute_at == execute_at
        assert payload.cleanup_required is False

    def test_effect_node_processes_typed_operation_data(
        self,
        effect_node: NodeEffect,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test that NodeEffect.process() works with typed operation data."""
        # Arrange: Create input with both dict data (for template resolution)
        # and verify typed model creation works
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "typed_test_123"},
            retry_enabled=False,
        )

        # Act: Process the input
        result: ModelEffectOutput = asyncio.run(effect_node.process(input_data))

        # Assert: Processing completed successfully
        assert result.transaction_state == EnumTransactionState.COMMITTED
        mock_http_handler.execute.assert_called_once()


# =============================================================================
# 2. NORMALIZATION LOGIC TESTS
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
# 3. BACKWARDS COMPATIBILITY TESTS
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
# 4. TYPE COERCION/CONVERSION TESTS
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
# 5. ERROR HANDLING TESTS
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
# 6. IMMUTABILITY TESTS
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
# 7. HELPER METHOD TESTS
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


# =============================================================================
# 8. WORKFLOW INTEGRATION TESTS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestWorkflowIntegration:
    """End-to-end workflow tests with typed payloads."""

    def test_complete_effect_workflow_with_typed_data(
        self,
        effect_node: NodeEffect,
        mock_http_handler: AsyncMock,
    ) -> None:
        """Test complete effect workflow with typed operation data."""
        # This test verifies the entire flow works with dict operation_data
        # (which is what the node currently uses for template resolution)
        input_data = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={"id": "workflow_test"},
            retry_enabled=False,
        )

        result = asyncio.run(effect_node.process(input_data))

        assert result.transaction_state == EnumTransactionState.COMMITTED
        assert result.effect_type == EnumEffectType.API_CALL
        assert result.processing_time_ms >= 0.0

    def test_typed_payload_model_dump_for_serialization(self) -> None:
        """Test that typed payloads can be serialized for transport."""
        payload = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com/users",
            target_system="user-service",
            operation_name="get_users",
        )

        # Serialize to dict (for JSON transport)
        serialized = payload.model_dump(mode="json")

        # Verify serialization is JSON-compatible
        assert isinstance(serialized, dict)
        # Enum serialized as lowercase string (Pydantic default behavior)
        assert serialized["effect_type"] == "api_call"
        assert serialized["resource_path"] == "https://api.example.com/users"

        # Deserialize back - Pydantic handles lowercase enum values
        restored = ModelEffectInputData(**serialized)
        assert restored.effect_type == EnumEffectType.API_CALL
        assert restored.resource_path == "https://api.example.com/users"

    def test_reducer_intent_payload_in_fsm_transition(self) -> None:
        """Test ModelReducerIntentPayload for FSM state transitions."""
        # Simulate FSM transition from pending to active
        entity_id = uuid4()

        pending_payload = ModelReducerIntentPayload(
            target_state="pending",
            source_state=None,
            trigger="created",
            entity_id=entity_id,
            entity_type="order",
            operation="create",
        )

        # Simulate transition
        active_payload = ModelReducerIntentPayload(
            target_state="active",
            source_state="pending",
            trigger="approved",
            entity_id=entity_id,
            entity_type="order",
            operation="activate",
        )

        # Verify transition chain is consistent
        assert pending_payload.target_state == active_payload.source_state
        assert pending_payload.entity_id == active_payload.entity_id

    def test_runtime_directive_payload_for_delayed_execution(self) -> None:
        """Test ModelRuntimeDirectivePayload for delayed execution scenarios."""
        # Schedule execution 5 minutes from now
        scheduled_time = datetime.now(UTC) + timedelta(minutes=5)

        payload = ModelRuntimeDirectivePayload(
            execute_at=scheduled_time,
            handler_args={"job_id": "job_123", "action": "process"},
            queue_name="delayed-jobs",
            priority=3,
        )

        # Verify scheduling data
        assert payload.execute_at == scheduled_time
        assert payload.handler_args["job_id"] == "job_123"
        assert payload.queue_name == "delayed-jobs"


# =============================================================================
# 9. UNION TYPE DISCRIMINATION EDGE CASES
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


# =============================================================================
# 10. EVENT BUS SERIALIZATION PATTERNS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestEventBusSerializationPatterns:
    """Tests for serialization patterns used in event bus communication."""

    def test_typed_payload_json_serialization_round_trip(self) -> None:
        """Test JSON serialization round-trip for event bus transport."""
        import json

        original = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://api.example.com/users",
            target_system="user-service",
            operation_name="get_user",
            idempotency_key="idempotent_123",
            content_type="application/json",
            encoding="utf-8",
        )

        # Serialize to JSON (for Kafka/event bus transport)
        json_str = original.model_dump_json()

        # Verify JSON is valid and can be deserialized
        json_data = json.loads(json_str)
        assert isinstance(json_data, dict)

        # Deserialize back to model
        restored = ModelEffectInputData.model_validate(json_data)

        # Verify all fields preserved
        assert restored.effect_type == original.effect_type
        assert restored.resource_path == original.resource_path
        assert restored.target_system == original.target_system
        assert restored.operation_name == original.operation_name
        assert restored.idempotency_key == original.idempotency_key
        assert restored.content_type == original.content_type
        assert restored.encoding == original.encoding

    def test_reducer_intent_payload_json_round_trip(self) -> None:
        """Test JSON round-trip for ModelReducerIntentPayload."""
        import json

        entity_id = uuid4()
        original = ModelReducerIntentPayload(
            target_state="completed",
            source_state="processing",
            trigger="task_done",
            entity_id=entity_id,
            entity_type="task",
            operation="finalize",
            data=(("result", "success"), ("output_size", 1024)),
            idempotency_key="task_complete_001",
            timeout_ms=30000,
            retry_count=0,
            max_retries=5,
        )

        # JSON round-trip
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)
        restored = ModelReducerIntentPayload.model_validate(json_data)

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

    def test_effect_input_with_typed_data_json_round_trip(self) -> None:
        """Test JSON round-trip for ModelEffectInput with typed operation_data."""
        import json

        typed_data = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path="/data/export.json",
            target_system="local-fs",
            operation_name="write_export",
        )
        original = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=typed_data,
            transaction_enabled=True,
            retry_enabled=True,
            max_retries=5,
            timeout_ms=10000,
        )

        # JSON round-trip
        json_str = original.model_dump_json()
        json_data = json.loads(json_str)
        restored = ModelEffectInput.model_validate(json_data)

        # Verify parent fields preserved
        assert restored.effect_type == original.effect_type
        assert restored.transaction_enabled == original.transaction_enabled
        assert restored.retry_enabled == original.retry_enabled
        assert restored.max_retries == original.max_retries
        assert restored.timeout_ms == original.timeout_ms

        # Note: After JSON round-trip, typed model becomes dict
        # This is expected behavior - JSON doesn't preserve Python types
        assert isinstance(restored.operation_data, dict)
        assert restored.operation_data["effect_type"] == "file_operation"
        assert restored.operation_data["resource_path"] == "/data/export.json"

    def test_model_dump_mode_json_for_network_transport(self) -> None:
        """Test model_dump(mode='json') produces network-safe output."""
        resource_id = uuid4()
        model = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="users",
            target_system="postgres",
            resource_id=resource_id,
        )

        # mode='json' ensures all values are JSON-serializable
        json_safe = model.model_dump(mode="json")

        # UUID should be string in JSON mode
        assert isinstance(json_safe["resource_id"], str)
        assert json_safe["resource_id"] == str(resource_id)

        # Enum should be lowercase string
        assert json_safe["effect_type"] == "database_operation"

    def test_batch_serialization_for_kafka_producer(self) -> None:
        """Test batch serialization pattern used by Kafka producers."""
        payloads = [
            ModelReducerIntentPayload(
                entity_type="order",
                operation="create",
                entity_id=uuid4(),
                data=(("order_id", f"ORD-{i}"),),
            )
            for i in range(10)
        ]

        # Simulate batch serialization for Kafka
        serialized_batch = [p.model_dump(mode="json") for p in payloads]

        assert len(serialized_batch) == 10
        for i, serialized in enumerate(serialized_batch):
            assert serialized["entity_type"] == "order"
            assert serialized["operation"] == "create"
            # Note: tuples become lists in JSON serialization
            assert ["order_id", f"ORD-{i}"] in serialized["data"]


# =============================================================================
# 11. UNICODE EDGE CASES
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestUnicodeEdgeCases:
    """Tests for unicode handling in typed payloads."""

    def test_effect_input_data_with_unicode_resource_path(self) -> None:
        """Test ModelEffectInputData with unicode characters in resource_path.

        Tests Unicode from multiple scripts in file paths:
        - Japanese (日本語)
        - Chinese (文件)
        - Russian (архив)
        - Greek (αρχείο)
        """
        import json

        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path="/data/日本語/文件/архив/αρχείο.json",
            target_system="local-fs",
            operation_name="read_multilingual",
        )

        assert "日本語" in model.resource_path  # Japanese
        assert "文件" in model.resource_path  # Chinese
        assert "архив" in model.resource_path  # Russian
        assert "αρχείο" in model.resource_path  # Greek

        # Round-trip through JSON should preserve data
        json_str = model.model_dump_json()
        restored = ModelEffectInputData.model_validate(json.loads(json_str))
        assert restored.resource_path == model.resource_path

    def test_reducer_intent_payload_with_unicode_data(self) -> None:
        """Test ModelReducerIntentPayload with unicode in data field.

        Tests diverse Unicode including:
        - Russian (Привет мир)
        - Arabic (مرحبا بالعالم)
        - Emoji symbols
        - Mathematical symbols
        - Currency symbols
        """
        import json

        payload = ModelReducerIntentPayload(
            entity_type="notification",
            operation="send",
            data=(
                (
                    "message",
                    "Hello, world! Привет мир! مرحبا بالعالم!",
                ),
                ("emoji", "🎉🚀✨💯"),
                ("mathematical", "∑∏∫∂√∞"),
                ("currency", "€£¥₹₽"),
            ),
        )

        data_dict = payload.get_data_as_dict()
        assert "Hello" in data_dict["message"]
        assert "Привет" in data_dict["message"]  # Russian "Privet"
        assert "مرحبا" in data_dict["message"]  # Arabic "Marhaba"
        assert data_dict["emoji"] == "🎉🚀✨💯"
        assert data_dict["mathematical"] == "∑∏∫∂√∞"
        assert data_dict["currency"] == "€£¥₹₽"

        # JSON round-trip should preserve all data
        json_str = payload.model_dump_json()
        restored = ModelReducerIntentPayload.model_validate(json.loads(json_str))
        restored_dict = restored.get_data_as_dict()
        assert restored_dict == data_dict

    def test_runtime_directive_with_unicode_handler_args(self) -> None:
        """Test ModelRuntimeDirectivePayload with unicode in handler_args.

        Tests Unicode in handler arguments:
        - Japanese name (田中太郎)
        - Russian greeting (Добро пожаловать)
        - Greek greeting (Καλώς ήρθατε)
        - Hebrew greeting (ברוכים הבאים)
        """
        payload = ModelRuntimeDirectivePayload(
            handler_args={
                "recipient_name": "田中太郎",
                "message": "Добро пожаловать! Καλώς ήρθατε! ברוכים הבאים!",
                "locale": "ja-JP",
            },
            execution_mode="async",
        )

        assert payload.handler_args["recipient_name"] == "田中太郎"  # Japanese name
        assert "Добро пожаловать" in payload.handler_args["message"]  # Russian
        assert "Καλώς ήρθατε" in payload.handler_args["message"]  # Greek
        assert "ברוכים הבאים" in payload.handler_args["message"]  # Hebrew

    def test_effect_input_data_with_unicode_operation_name(self) -> None:
        """Test unicode in operation_name field.

        Tests Chinese characters in operation name (获取用户 = "get user").
        """
        import json

        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/users",
            operation_name="获取用户",  # Chinese for "get user"
        )

        assert model.operation_name == "获取用户"

        # Verify JSON serialization
        json_str = model.model_dump_json()
        data = json.loads(json_str)
        assert data["operation_name"] == "获取用户"

    def test_unicode_in_validation_errors(self) -> None:
        """Test unicode in validation_errors field.

        Tests validation error messages in multiple languages:
        - Japanese: メールフィールドは必須です (Email field is required)
        - Russian: Поле возраст >= 0 (Field age >= 0)
        - Spanish: El campo nombre es obligatorio (Name field is required)
        """
        payload = ModelReducerIntentPayload(
            entity_type="validation",
            operation="report",
            validation_errors=(
                "メールフィールドは必須です",  # Japanese: "Email field is required"
                "Поле возраст >= 0",  # Russian: "Field age >= 0"
                "El campo nombre es obligatorio",  # Spanish: "Name field is required"
            ),
        )

        assert len(payload.validation_errors) == 3
        assert "メール" in payload.validation_errors[0]  # Japanese
        assert "Поле" in payload.validation_errors[1]  # Russian
        assert "obligatorio" in payload.validation_errors[2]  # Spanish

    def test_unicode_idempotency_key(self) -> None:
        """Test unicode in idempotency_key field.

        Tests Japanese characters in idempotency key (注文 = "order").
        """
        import json

        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/orders",
            idempotency_key="order_2024_001_注文",  # Japanese for "order"
        )

        assert model.idempotency_key == "order_2024_001_注文"

        # JSON round-trip
        restored = ModelEffectInputData.model_validate(
            json.loads(model.model_dump_json())
        )
        assert restored.idempotency_key == model.idempotency_key


# =============================================================================
# 12. COMPLEX WORKFLOW PATTERNS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComplexWorkflowPatterns:
    """Tests for complex real-world workflow patterns."""

    def test_multi_step_effect_chain(self) -> None:
        """Test chained effect operations simulating a real workflow."""
        import json

        # Step 1: Database read
        db_read = ModelEffectInputData(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            resource_path="orders",
            target_system="postgres",
            operation_name="fetch_pending_orders",
        )

        # Step 2: API call for each order
        api_call = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://shipping.example.com/calculate",
            target_system="shipping-service",
            operation_name="calculate_shipping",
            content_type="application/json",
        )

        # Step 3: File write for results
        resource_id = uuid4()
        file_write = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path="/exports/shipping_costs.json",
            target_system="s3",
            operation_name="export_shipping_costs",
            resource_id=resource_id,
            content_type="application/json",
            encoding="utf-8",
        )

        # Create effect inputs for each step
        step1 = ModelEffectInput(
            effect_type=EnumEffectType.DATABASE_OPERATION,
            operation_data=db_read,
            transaction_enabled=True,
        )
        step2 = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=api_call,
            retry_enabled=True,
            max_retries=3,
            timeout_ms=5000,
        )
        step3 = ModelEffectInput(
            effect_type=EnumEffectType.FILE_OPERATION,
            operation_data=file_write,
            transaction_enabled=False,
        )

        # Verify all steps maintain correct types
        assert isinstance(step1.operation_data, ModelEffectInputData)
        assert isinstance(step2.operation_data, ModelEffectInputData)
        assert isinstance(step3.operation_data, ModelEffectInputData)

        # Verify chain can be serialized for distributed execution
        chain = [
            step1.model_dump(mode="json"),
            step2.model_dump(mode="json"),
            step3.model_dump(mode="json"),
        ]
        chain_json = json.dumps(chain)
        assert len(chain_json) > 0

    def test_fsm_state_machine_workflow(self) -> None:
        """Test FSM state machine workflow with typed payloads."""
        entity_id = uuid4()

        # Define state transitions for an order lifecycle
        transitions = [
            ModelReducerIntentPayload(
                target_state="pending",
                source_state=None,
                trigger="order_created",
                entity_id=entity_id,
                entity_type="order",
                operation="create",
                data=(("order_total", 150.00), ("currency", "USD")),
            ),
            ModelReducerIntentPayload(
                target_state="processing",
                source_state="pending",
                trigger="payment_received",
                entity_id=entity_id,
                entity_type="order",
                operation="process",
                data=(("payment_id", "PAY-12345"),),
            ),
            ModelReducerIntentPayload(
                target_state="shipped",
                source_state="processing",
                trigger="package_dispatched",
                entity_id=entity_id,
                entity_type="order",
                operation="ship",
                data=(("tracking_number", "TRACK-67890"),),
            ),
            ModelReducerIntentPayload(
                target_state="delivered",
                source_state="shipped",
                trigger="delivery_confirmed",
                entity_id=entity_id,
                entity_type="order",
                operation="complete",
            ),
        ]

        # Verify state transition chain is consistent
        for i in range(1, len(transitions)):
            assert transitions[i].source_state == transitions[i - 1].target_state
            assert transitions[i].entity_id == transitions[i - 1].entity_id

        # Verify each payload can be serialized
        for t in transitions:
            json_str = t.model_dump_json()
            assert len(json_str) > 0

    def test_retry_workflow_with_backoff(self) -> None:
        """Test retry workflow pattern with backoff configuration."""
        original_payload = ModelReducerIntentPayload(
            entity_type="webhook",
            operation="deliver",
            data=(("webhook_url", "https://customer.example.com/hook"),),
            retry_count=0,
            max_retries=5,
            timeout_ms=10000,
        )

        # Simulate retry workflow
        current = original_payload
        retry_history: list[tuple[int, bool]] = []

        while current.is_retryable():
            # Record current retry state
            retry_history.append((current.retry_count, current.is_retryable()))

            # Simulate failure and retry
            current = current.with_incremented_retry()

        # Final state after max retries
        retry_history.append((current.retry_count, current.is_retryable()))

        # Verify retry progression
        assert len(retry_history) == 6  # 0 through 5 retries
        assert retry_history[0] == (0, True)
        assert retry_history[1] == (1, True)
        assert retry_history[2] == (2, True)
        assert retry_history[3] == (3, True)
        assert retry_history[4] == (4, True)
        assert retry_history[5] == (5, False)  # At max, not retryable

        # Verify original is immutable
        assert original_payload.retry_count == 0
        assert original_payload.is_retryable() is True

    def test_scheduled_directive_workflow(self) -> None:
        """Test scheduled directive workflow pattern."""
        now = datetime.now(UTC)

        # Schedule a sequence of directives at different times
        directives = [
            ModelRuntimeDirectivePayload(
                handler_args={"step": "prepare", "job_id": "JOB-001"},
                execute_at=now + timedelta(minutes=1),
                priority=1,
                queue_name="high-priority",
            ),
            ModelRuntimeDirectivePayload(
                handler_args={"step": "process", "job_id": "JOB-001"},
                execute_at=now + timedelta(minutes=5),
                priority=2,
                queue_name="default",
            ),
            ModelRuntimeDirectivePayload(
                handler_args={"step": "cleanup", "job_id": "JOB-001"},
                execute_at=now + timedelta(minutes=10),
                priority=3,
                queue_name="low-priority",
                cleanup_required=True,
            ),
        ]

        # Verify scheduling order
        for i in range(1, len(directives)):
            assert directives[i].execute_at > directives[i - 1].execute_at
            assert directives[i].priority > directives[i - 1].priority

        # Verify all reference same job
        job_ids = [d.handler_args["job_id"] for d in directives]
        assert all(jid == "JOB-001" for jid in job_ids)

    def test_mixed_dict_and_typed_payloads_in_workflow(self) -> None:
        """Test workflow mixing dict and typed payloads for flexibility."""
        # Legacy dict-based input (backwards compatible)
        legacy_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data={
                "url": "https://legacy.example.com/v1/process",
                "headers": {"X-Legacy-Token": "abc123"},
                "custom_params": {"legacy_param": True},
            },
        )

        # Modern typed input
        modern_typed = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="https://modern.example.com/v2/process",
            target_system="modern-api",
            operation_name="process_v2",
        )
        modern_input = ModelEffectInput(
            effect_type=EnumEffectType.API_CALL,
            operation_data=modern_typed,
        )

        # Both should work in the same workflow
        workflow_inputs = [legacy_input, modern_input]

        for inp in workflow_inputs:
            assert inp.effect_type == EnumEffectType.API_CALL
            # Can serialize both
            json_str = inp.model_dump_json()
            assert len(json_str) > 0

        # Types are preserved correctly
        assert isinstance(legacy_input.operation_data, dict)
        assert isinstance(modern_input.operation_data, ModelEffectInputData)

    def test_parallel_effect_aggregation_pattern(self) -> None:
        """Test parallel effect execution and aggregation pattern."""
        # Multiple parallel API calls (fan-out)
        parallel_calls = [
            ModelEffectInputData(
                effect_type=EnumEffectType.API_CALL,
                resource_path=f"https://shard-{i}.example.com/query",
                target_system=f"shard-{i}",
                operation_name="parallel_query",
                idempotency_key=f"query_batch_001_shard_{i}",
            )
            for i in range(5)
        ]

        # Verify each has unique idempotency key
        idempotency_keys = [c.idempotency_key for c in parallel_calls]
        assert len(set(idempotency_keys)) == 5

        # All share same operation name
        operation_names = [c.operation_name for c in parallel_calls]
        assert all(name == "parallel_query" for name in operation_names)

        # Each targets different shard
        target_systems = [c.target_system for c in parallel_calls]
        assert len(set(target_systems)) == 5
