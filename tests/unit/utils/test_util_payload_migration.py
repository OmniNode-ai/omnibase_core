"""
Unit tests for migration helpers and dict payload rejection.

Tests comprehensive functionality of:
- Dict payload rejection in ModelEventPublishIntent
- Migration helper functions for converting dict payloads to typed payloads
- Error message content verification
- Edge cases and error conditions
"""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.events.model_event_publish_intent import (
    ModelEventPublishIntent,
)
from omnibase_core.models.events.payloads import (
    ModelNodeRegisteredEvent,
    ModelNodeUnregisteredEvent,
    ModelRuntimeReadyEvent,
    ModelSubscriptionCreatedEvent,
    ModelWiringErrorEvent,
    ModelWiringResultEvent,
    convert_dict_to_typed_payload,
    get_migration_example,
    get_supported_event_types,
    infer_payload_type_from_dict,
)

# ============================================================================
# Dict Payload Rejection Tests
# ============================================================================


@pytest.mark.unit
class TestDictPayloadRejection:
    """Test cases for dict payload rejection in ModelEventPublishIntent."""

    def test_dict_payload_rejected_with_error(self):
        """Test that dict payloads are rejected with a ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventPublishIntent(
                correlation_id=uuid4(),
                created_by="test_node",
                target_topic="test.topic",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload={"node_id": str(uuid4()), "node_name": "test"},
            )

        # The validation error should contain our custom error message
        error_str = str(exc_info.value)
        assert "dict[str, Any] payloads are no longer supported" in error_str

    def test_error_message_mentions_version(self):
        """Test that error message mentions the version where this changed."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventPublishIntent(
                correlation_id=uuid4(),
                created_by="test_node",
                target_topic="test.topic",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload={"key": "value"},
            )

        error_str = str(exc_info.value)
        assert "v0.4.0" in error_str

    def test_error_message_contains_migration_example(self):
        """Test that error message contains migration example."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventPublishIntent(
                correlation_id=uuid4(),
                created_by="test_node",
                target_topic="test.topic",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload={"key": "value"},
            )

        error_str = str(exc_info.value)
        # Check for migration example markers
        assert "Before (no longer works)" in error_str
        assert "After (required)" in error_str
        assert "ModelNodeRegisteredEvent" in error_str

    def test_error_message_lists_available_payload_types(self):
        """Test that error message lists available payload types."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventPublishIntent(
                correlation_id=uuid4(),
                created_by="test_node",
                target_topic="test.topic",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload={},
            )

        error_str = str(exc_info.value)
        # Check for list of available types
        assert "Available payload types:" in error_str
        assert "ModelNodeRegisteredEvent" in error_str
        assert "ModelNodeUnregisteredEvent" in error_str
        assert "ModelWiringResultEvent" in error_str

    def test_error_message_contains_documentation_link(self):
        """Test that error message contains link to documentation."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventPublishIntent(
                correlation_id=uuid4(),
                created_by="test_node",
                target_topic="test.topic",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload={"any": "dict"},
            )

        error_str = str(exc_info.value)
        assert "PAYLOAD_TYPE_ARCHITECTURE.md" in error_str

    def test_error_message_contains_import_statement(self):
        """Test that error message contains import statement."""
        with pytest.raises(ValidationError) as exc_info:
            ModelEventPublishIntent(
                correlation_id=uuid4(),
                created_by="test_node",
                target_topic="test.topic",
                target_key="test-key",
                target_event_type="NODE_REGISTERED",
                target_event_payload={"some": "data"},
            )

        error_str = str(exc_info.value)
        assert "from omnibase_core.models.events.payloads import" in error_str
        assert "ModelEventPayloadUnion" in error_str

    def test_typed_payload_accepted(self):
        """Test that typed payloads are accepted without error."""
        node_id = uuid4()
        payload = ModelNodeRegisteredEvent(
            node_id=node_id,
            node_name="test-node",
            node_type=EnumNodeKind.COMPUTE,
        )

        intent = ModelEventPublishIntent(
            correlation_id=uuid4(),
            created_by="test_node",
            target_topic="test.topic",
            target_key="test-key",
            target_event_type="NODE_REGISTERED",
            target_event_payload=payload,
        )

        assert intent.target_event_payload.node_id == node_id
        assert intent.target_event_payload.node_name == "test-node"

    def test_all_typed_payloads_accepted(self):
        """Test that all typed payload types are accepted."""
        payloads = [
            ModelNodeRegisteredEvent(
                node_id=uuid4(),
                node_name="test",
                node_type=EnumNodeKind.COMPUTE,
            ),
            ModelNodeUnregisteredEvent(
                node_id=uuid4(),
                node_name="test",
            ),
            ModelSubscriptionCreatedEvent(
                node_id=uuid4(),
                topic="test.topic",
            ),
            ModelRuntimeReadyEvent(),
            ModelWiringResultEvent(),
            ModelWiringErrorEvent(
                error_code="TEST",
                error_message="Test error",
            ),
        ]

        for payload in payloads:
            intent = ModelEventPublishIntent(
                correlation_id=uuid4(),
                created_by="test_node",
                target_topic="test.topic",
                target_key="test-key",
                target_event_type="TEST",
                target_event_payload=payload,
            )
            assert intent.target_event_payload is not None


# ============================================================================
# Migration Helper Tests
# ============================================================================


@pytest.mark.unit
class TestInferPayloadTypeFromDict:
    """Test cases for infer_payload_type_from_dict function."""

    def test_infer_node_registered(self):
        """Test inference of NODE_REGISTERED from field structure."""
        data = {
            "node_id": str(uuid4()),
            "node_name": "test-node",
            "node_type": "COMPUTE",
        }
        result = infer_payload_type_from_dict(data)
        assert result == "NODE_REGISTERED"

    def test_infer_node_unregistered(self):
        """Test inference of NODE_UNREGISTERED from field structure."""
        data = {
            "node_id": str(uuid4()),
            "node_name": "test-node",
            "reason": "shutdown",
        }
        result = infer_payload_type_from_dict(data)
        assert result == "NODE_UNREGISTERED"

    def test_infer_subscription_created(self):
        """Test inference of SUBSCRIPTION_CREATED from field structure."""
        # SUBSCRIPTION_CREATED is identified by handler_name or subscribed_at
        data = {
            "node_id": str(uuid4()),
            "topic": "events.test",
            "handler_name": "on_event_received",
        }
        result = infer_payload_type_from_dict(data)
        assert result == "SUBSCRIPTION_CREATED"

    def test_infer_subscription_created_with_subscribed_at(self):
        """Test inference of SUBSCRIPTION_CREATED from subscribed_at field."""
        data = {
            "node_id": str(uuid4()),
            "topic": "events.test",
            "subscribed_at": "2025-01-01T00:00:00Z",
        }
        result = infer_payload_type_from_dict(data)
        assert result == "SUBSCRIPTION_CREATED"

    def test_infer_subscription_removed(self):
        """Test inference of SUBSCRIPTION_REMOVED from field structure."""
        data = {
            "subscription_id": str(uuid4()),
            "node_id": str(uuid4()),
            "topic": "events.test",
            "removed_at": "2025-01-01T00:00:00Z",
        }
        result = infer_payload_type_from_dict(data)
        assert result == "SUBSCRIPTION_REMOVED"

    def test_infer_wiring_result(self):
        """Test inference of WIRING_RESULT from field structure."""
        data = {
            "success": True,
            "total_nodes": 5,
            "successful_nodes": 5,
        }
        result = infer_payload_type_from_dict(data)
        assert result == "WIRING_RESULT"

    def test_infer_returns_none_for_unknown(self):
        """Test that inference returns None for unknown field structures."""
        data = {"unknown_field": "value", "another_unknown": 123}
        result = infer_payload_type_from_dict(data)
        assert result is None

    def test_infer_handles_empty_dict(self):
        """Test that inference handles empty dict gracefully."""
        result = infer_payload_type_from_dict({})
        assert result is None

    def test_infer_with_extra_fields(self):
        """Test that inference works with additional fields present."""
        data = {
            "node_id": str(uuid4()),
            "node_name": "test-node",
            "node_type": "COMPUTE",
            "extra_field": "should be ignored",
            "another_extra": 123,
        }
        result = infer_payload_type_from_dict(data)
        assert result == "NODE_REGISTERED"


@pytest.mark.unit
class TestConvertDictToTypedPayload:
    """Test cases for convert_dict_to_typed_payload function."""

    def test_convert_node_registered_with_explicit_type(self):
        """Test conversion with explicit event type."""
        node_id = uuid4()
        data = {
            "node_id": str(node_id),
            "node_name": "test-node",
            "node_type": "COMPUTE",
        }

        result = convert_dict_to_typed_payload(data, "NODE_REGISTERED")

        assert isinstance(result, ModelNodeRegisteredEvent)
        assert result.node_id == node_id
        assert result.node_name == "test-node"
        assert result.node_type == EnumNodeKind.COMPUTE

    def test_convert_with_inferred_type(self):
        """Test conversion with inferred event type."""
        node_id = uuid4()
        data = {
            "node_id": str(node_id),
            "node_name": "test-node",
            "node_type": "COMPUTE",
        }

        result = convert_dict_to_typed_payload(data)  # No explicit type

        assert isinstance(result, ModelNodeRegisteredEvent)
        assert result.node_id == node_id

    def test_convert_node_unregistered(self):
        """Test conversion of node unregistered event."""
        node_id = uuid4()
        data = {
            "node_id": str(node_id),
            "node_name": "test-node",
            "reason": "graceful_shutdown",
        }

        result = convert_dict_to_typed_payload(data, "NODE_UNREGISTERED")

        assert isinstance(result, ModelNodeUnregisteredEvent)
        assert result.reason == "graceful_shutdown"

    def test_convert_subscription_created(self):
        """Test conversion of subscription created event."""
        node_id = uuid4()
        data = {
            "node_id": str(node_id),
            "topic": "events.test",
        }

        result = convert_dict_to_typed_payload(data, "SUBSCRIPTION_CREATED")

        assert isinstance(result, ModelSubscriptionCreatedEvent)
        assert result.topic == "events.test"

    def test_convert_runtime_ready(self):
        """Test conversion of runtime ready event."""
        data = {
            "node_count": 5,
            "subscription_count": 10,
        }

        result = convert_dict_to_typed_payload(data, "RUNTIME_READY")

        assert isinstance(result, ModelRuntimeReadyEvent)
        assert result.node_count == 5
        assert result.subscription_count == 10

    def test_convert_wiring_result(self):
        """Test conversion of wiring result event."""
        data = {
            "success": True,
            "total_nodes": 3,
            "successful_nodes": 3,
        }

        result = convert_dict_to_typed_payload(data, "WIRING_RESULT")

        assert isinstance(result, ModelWiringResultEvent)
        assert result.success is True
        assert result.total_nodes == 3

    def test_convert_wiring_error(self):
        """Test conversion of wiring error event."""
        data = {
            "error_code": "TIMEOUT",
            "error_message": "Connection timeout",
        }

        result = convert_dict_to_typed_payload(data, "WIRING_ERROR")

        assert isinstance(result, ModelWiringErrorEvent)
        assert result.error_code == "TIMEOUT"
        assert result.error_message == "Connection timeout"

    def test_convert_with_full_event_type_name(self):
        """Test conversion using full event type name."""
        data = {
            "node_count": 2,
            "subscription_count": 4,
        }

        result = convert_dict_to_typed_payload(data, "onex.runtime.ready")

        assert isinstance(result, ModelRuntimeReadyEvent)

    def test_convert_handles_uuid_strings(self):
        """Test that UUID strings are automatically converted."""
        node_id = uuid4()
        data = {
            "node_id": str(node_id),  # String, not UUID
            "node_name": "test-node",
            "node_type": "COMPUTE",
        }

        result = convert_dict_to_typed_payload(data, "NODE_REGISTERED")

        assert result.node_id == node_id  # Should be UUID object

    def test_convert_handles_enum_strings(self):
        """Test that enum strings are automatically converted."""
        data = {
            "node_id": str(uuid4()),
            "node_name": "test-node",
            "node_type": "COMPUTE",  # String, not EnumNodeKind
        }

        result = convert_dict_to_typed_payload(data, "NODE_REGISTERED")

        assert result.node_type == EnumNodeKind.COMPUTE

    def test_convert_raises_on_unknown_type(self):
        """Test that unknown event types raise ModelOnexError."""
        data = {"some": "data"}

        with pytest.raises(ModelOnexError) as exc_info:
            convert_dict_to_typed_payload(data, "UNKNOWN_TYPE")

        assert "Unknown event type" in str(exc_info.value)
        assert "UNKNOWN_TYPE" in str(exc_info.value)

    def test_convert_raises_on_uninferrable_type(self):
        """Test that uninferrable types raise ModelOnexError."""
        data = {"random_field": "random_value"}

        with pytest.raises(ModelOnexError) as exc_info:
            convert_dict_to_typed_payload(data)  # No explicit type

        assert "Cannot infer event type" in str(exc_info.value)
        assert "target_event_type" in str(exc_info.value)

    def test_convert_raises_on_invalid_data(self):
        """Test that invalid data raises ModelOnexError."""
        data = {
            "node_id": "not-a-valid-uuid",  # Invalid UUID
            "node_name": "test",
            "node_type": "COMPUTE",
        }

        with pytest.raises(ModelOnexError) as exc_info:
            convert_dict_to_typed_payload(data, "NODE_REGISTERED")

        assert "Failed to convert dict" in str(exc_info.value)
        assert "ModelNodeRegisteredEvent" in str(exc_info.value)


@pytest.mark.unit
class TestGetSupportedEventTypes:
    """Test cases for get_supported_event_types function."""

    def test_returns_list_of_strings(self):
        """Test that function returns a list of strings."""
        result = get_supported_event_types()
        assert isinstance(result, list)
        assert all(isinstance(t, str) for t in result)

    def test_contains_common_event_types(self):
        """Test that common event types are included."""
        result = get_supported_event_types()
        assert "NODE_REGISTERED" in result
        assert "NODE_UNREGISTERED" in result
        assert "RUNTIME_READY" in result
        assert "WIRING_RESULT" in result

    def test_list_is_sorted(self):
        """Test that the list is sorted alphabetically."""
        result = get_supported_event_types()
        assert result == sorted(result)


@pytest.mark.unit
class TestGetMigrationExample:
    """Test cases for get_migration_example function."""

    def test_get_node_registered_example(self):
        """Test getting migration example for NODE_REGISTERED."""
        example = get_migration_example("NODE_REGISTERED")
        assert "Before (no longer works)" in example
        assert "After (required)" in example
        assert "ModelNodeRegisteredEvent" in example
        assert "EnumNodeKind.COMPUTE" in example

    def test_get_node_unregistered_example(self):
        """Test getting migration example for NODE_UNREGISTERED."""
        example = get_migration_example("NODE_UNREGISTERED")
        assert "ModelNodeUnregisteredEvent" in example

    def test_get_runtime_ready_example(self):
        """Test getting migration example for RUNTIME_READY."""
        example = get_migration_example("RUNTIME_READY")
        assert "ModelRuntimeReadyEvent" in example

    def test_get_wiring_result_example(self):
        """Test getting migration example for WIRING_RESULT."""
        example = get_migration_example("WIRING_RESULT")
        assert "ModelWiringResultEvent" in example

    def test_get_wiring_error_example(self):
        """Test getting migration example for WIRING_ERROR."""
        example = get_migration_example("WIRING_ERROR")
        assert "ModelWiringErrorEvent" in example

    def test_fallback_for_other_types(self):
        """Test fallback example for types without explicit examples."""
        example = get_migration_example("onex.runtime.node.registered")
        assert "ModelNodeRegisteredEvent" in example

    def test_raises_for_unknown_type(self):
        """Test that unknown types raise ModelOnexError."""
        with pytest.raises(ModelOnexError) as exc_info:
            get_migration_example("COMPLETELY_UNKNOWN")

        assert "No migration example available" in str(exc_info.value)


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
class TestMigrationWorkflow:
    """Integration tests for the complete migration workflow."""

    def test_full_migration_workflow(self):
        """Test complete migration from dict to typed payload."""
        # Simulate legacy code pattern
        legacy_data = {
            "node_id": str(uuid4()),
            "node_name": "my_compute_node",
            "node_type": "COMPUTE",
        }

        # Use migration helper to convert
        typed_payload = convert_dict_to_typed_payload(legacy_data, "NODE_REGISTERED")

        # Now create the intent with typed payload
        intent = ModelEventPublishIntent(
            correlation_id=uuid4(),
            created_by="migrated_code",
            target_topic="test.topic",
            target_key="test-key",
            target_event_type="NODE_REGISTERED",
            target_event_payload=typed_payload,
        )

        assert isinstance(intent.target_event_payload, ModelNodeRegisteredEvent)
        assert intent.target_event_payload.node_name == "my_compute_node"

    def test_migration_preserves_all_fields(self):
        """Test that migration preserves all provided fields."""
        node_id = uuid4()
        correlation_id = uuid4()
        legacy_data = {
            "node_id": str(node_id),
            "node_name": "full_node",
            "node_type": "ORCHESTRATOR",
            "correlation_id": str(correlation_id),
            "contract_path": "/path/to/contract.yaml",
            "declared_subscriptions": ["topic.a", "topic.b"],
        }

        typed_payload = convert_dict_to_typed_payload(legacy_data, "NODE_REGISTERED")

        assert typed_payload.node_id == node_id
        assert typed_payload.node_name == "full_node"
        assert typed_payload.node_type == EnumNodeKind.ORCHESTRATOR
        assert typed_payload.contract_path == "/path/to/contract.yaml"
        assert typed_payload.declared_subscriptions == ["topic.a", "topic.b"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
