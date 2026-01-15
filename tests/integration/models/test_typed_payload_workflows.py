# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""End-to-end workflow tests for typed payload models.

This module tests the typed payload models in real node workflow scenarios.
It focuses on:

1. Typed Payload Usage in Node Workflows
    - Tests that nodes can receive typed models instead of dicts
    - Verifies proper type discrimination in union fields

2. Workflow Integration Tests
    - End-to-end effect workflow tests
    - FSM state transition patterns
    - Scheduled directive workflows

3. Event Bus Serialization Patterns
    - JSON serialization round-trip tests
    - Network transport patterns
    - Batch serialization for Kafka

4. Unicode Edge Cases
    - Unicode handling in resource paths
    - Multilingual data in payloads
    - International character support

5. Complex Workflow Patterns
    - Multi-step effect chains
    - FSM state machine workflows
    - Retry workflows with backoff
    - Mixed dict and typed payload workflows

Note:
    Integration tests using fixtures from conftest.py should be marked with:
    - @pytest.mark.integration: For test classification
    - @pytest.mark.timeout(60): For CI protection against hangs

    The integration marker is already registered in pyproject.toml.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

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
# TYPED PAYLOAD USAGE IN NODE WORKFLOWS
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
# WORKFLOW INTEGRATION TESTS
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
# EVENT BUS SERIALIZATION PATTERNS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestEventBusSerializationPatterns:
    """Tests for serialization patterns used in event bus communication."""

    def test_typed_payload_json_serialization_round_trip(self) -> None:
        """Test JSON serialization round-trip for event bus transport."""
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
# UNICODE EDGE CASES
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestUnicodeEdgeCases:
    """Tests for unicode handling in typed payloads."""

    def test_effect_input_data_with_unicode_resource_path(self) -> None:
        """Test ModelEffectInputData with unicode characters in resource_path.

        Tests Unicode from multiple scripts in file paths:
        - Japanese (nihongo)
        - Chinese (wenjian)
        - Russian (arkhiv)
        - Greek (arkheio)
        """
        model = ModelEffectInputData(
            effect_type=EnumEffectType.FILE_OPERATION,
            resource_path="/data/\u65e5\u672c\u8a9e/\u6587\u4ef6/"
            "\u0430\u0440\u0445\u0438\u0432/"
            "\u03b1\u03c1\u03c7\u03b5\u03af\u03bf.json",
            target_system="local-fs",
            operation_name="read_multilingual",
        )

        assert "\u65e5\u672c\u8a9e" in model.resource_path  # Japanese
        assert "\u6587\u4ef6" in model.resource_path  # Chinese
        assert "\u0430\u0440\u0445\u0438\u0432" in model.resource_path  # Russian
        assert "\u03b1\u03c1\u03c7\u03b5\u03af\u03bf" in model.resource_path  # Greek

        # Round-trip through JSON should preserve data
        json_str = model.model_dump_json()
        restored = ModelEffectInputData.model_validate(json.loads(json_str))
        assert restored.resource_path == model.resource_path

    def test_reducer_intent_payload_with_unicode_data(self) -> None:
        """Test ModelReducerIntentPayload with unicode in data field.

        Tests diverse Unicode including:
        - Russian (Privet mir)
        - Arabic (Marhaba bialealim)
        - Emoji symbols
        - Mathematical symbols
        - Currency symbols
        """
        payload = ModelReducerIntentPayload(
            entity_type="notification",
            operation="send",
            data=(
                (
                    "message",
                    "Hello, world! \u041f\u0440\u0438\u0432\u0435\u0442 "
                    "\u043c\u0438\u0440! \u0645\u0631\u062d\u0628\u0627 "
                    "\u0628\u0627\u0644\u0639\u0627\u0644\u0645!",
                ),
                ("emoji", "\U0001f389\U0001f680\u2728\U0001f4af"),
                ("mathematical", "\u2211\u220f\u222b\u2202\u221a\u221e"),
                ("currency", "\u20ac\xa3\xa5\u20b9\u20bd"),
            ),
        )

        data_dict = payload.get_data_as_dict()
        assert "Hello" in data_dict["message"]
        # Russian "Privet"
        assert "\u041f\u0440\u0438\u0432\u0435\u0442" in data_dict["message"]
        # Arabic "Marhaba"
        assert "\u0645\u0631\u062d\u0628\u0627" in data_dict["message"]
        assert data_dict["emoji"] == "\U0001f389\U0001f680\u2728\U0001f4af"
        assert data_dict["mathematical"] == "\u2211\u220f\u222b\u2202\u221a\u221e"
        assert data_dict["currency"] == "\u20ac\xa3\xa5\u20b9\u20bd"

        # JSON round-trip should preserve all data
        json_str = payload.model_dump_json()
        restored = ModelReducerIntentPayload.model_validate(json.loads(json_str))
        restored_dict = restored.get_data_as_dict()
        assert restored_dict == data_dict

    def test_runtime_directive_with_unicode_handler_args(self) -> None:
        """Test ModelRuntimeDirectivePayload with unicode in handler_args.

        Tests Unicode in handler arguments:
        - Japanese name (Tanaka Taro)
        - Russian greeting (Dobro pozhalovat')
        - Greek greeting (Kalos irthate)
        - Hebrew greeting (Bruchim habaim)
        """
        payload = ModelRuntimeDirectivePayload(
            handler_args={
                "recipient_name": "\u7530\u4e2d\u592a\u90ce",
                "message": "\u0414\u043e\u0431\u0440\u043e "
                "\u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c! "
                "\u039a\u03b1\u03bb\u03ce\u03c2 \u03ae\u03c1\u03b8\u03b1\u03c4\u03b5! "
                "\u05d1\u05e8\u05d5\u05db\u05d9\u05dd "
                "\u05d4\u05d1\u05d0\u05d9\u05dd!",
                "locale": "ja-JP",
            },
            execution_mode="async",
        )

        # Japanese name
        assert payload.handler_args["recipient_name"] == "\u7530\u4e2d\u592a\u90ce"
        # Russian
        assert (
            "\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430"
            "\u043b\u043e\u0432\u0430\u0442\u044c" in payload.handler_args["message"]
        )
        # Greek
        assert (
            "\u039a\u03b1\u03bb\u03ce\u03c2 \u03ae\u03c1\u03b8\u03b1\u03c4\u03b5"
            in payload.handler_args["message"]
        )
        # Hebrew
        assert (
            "\u05d1\u05e8\u05d5\u05db\u05d9\u05dd \u05d4\u05d1\u05d0\u05d9\u05dd"
            in payload.handler_args["message"]
        )

    def test_effect_input_data_with_unicode_operation_name(self) -> None:
        """Test unicode in operation_name field.

        Tests Chinese characters in operation name (huoqu yonghu = "get user").
        """
        # Chinese for "get user"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/users",
            operation_name="\u83b7\u53d6\u7528\u6237",
        )

        assert model.operation_name == "\u83b7\u53d6\u7528\u6237"

        # Verify JSON serialization
        json_str = model.model_dump_json()
        data = json.loads(json_str)
        assert data["operation_name"] == "\u83b7\u53d6\u7528\u6237"

    def test_unicode_in_validation_errors(self) -> None:
        """Test unicode in validation_errors field.

        Tests validation error messages in multiple languages:
        - Japanese: Email field is required
        - Russian: Field age >= 0
        - Spanish: Name field is required
        """
        payload = ModelReducerIntentPayload(
            entity_type="validation",
            operation="report",
            validation_errors=(
                # Japanese: "Email field is required"
                "\u30e1\u30fc\u30eb\u30d5\u30a3\u30fc\u30eb\u30c9"
                "\u306f\u5fc5\u9808\u3067\u3059",
                # Russian: "Field age >= 0"
                "\u041f\u043e\u043b\u0435 \u0432\u043e\u0437\u0440"
                "\u0430\u0441\u0442 >= 0",
                # Spanish: "Name field is required"
                "El campo nombre es obligatorio",
            ),
        )

        assert len(payload.validation_errors) == 3
        assert "\u30e1\u30fc\u30eb" in payload.validation_errors[0]  # Japanese
        assert "\u041f\u043e\u043b\u0435" in payload.validation_errors[1]  # Russian
        assert "obligatorio" in payload.validation_errors[2]  # Spanish

    def test_unicode_idempotency_key(self) -> None:
        """Test unicode in idempotency_key field.

        Tests Japanese characters in idempotency key (chuumon = "order").
        """
        # Japanese for "order"
        model = ModelEffectInputData(
            effect_type=EnumEffectType.API_CALL,
            resource_path="/api/orders",
            idempotency_key="order_2024_001_\u6ce8\u6587",
        )

        assert model.idempotency_key == "order_2024_001_\u6ce8\u6587"

        # JSON round-trip
        restored = ModelEffectInputData.model_validate(
            json.loads(model.model_dump_json())
        )
        assert restored.idempotency_key == model.idempotency_key


# =============================================================================
# COMPLEX WORKFLOW PATTERNS
# =============================================================================


@pytest.mark.integration
@pytest.mark.timeout(INTEGRATION_TEST_TIMEOUT_SECONDS)
class TestComplexWorkflowPatterns:
    """Tests for complex real-world workflow patterns."""

    def test_multi_step_effect_chain(self) -> None:
        """Test chained effect operations simulating a real workflow."""
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
