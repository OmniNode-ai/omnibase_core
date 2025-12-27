"""
Unit tests for ModelEventPayloadUnion and runtime event types.

Tests comprehensive functionality of the typed event payload system including:
- All 9 runtime event types instantiation and validation
- Serialization/deserialization round-trip
- Union type resolution
- Factory methods
- Model validators
- Edge cases and error conditions
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.errors import ModelOnexError
from omnibase_core.models.events.model_node_graph_info import ModelNodeGraphInfo
from omnibase_core.models.events.model_wiring_error_info import ModelWiringErrorInfo
from omnibase_core.models.events.payloads import (
    ModelEventPayloadUnion,
    ModelNodeGraphReadyEvent,
    ModelNodeRegisteredEvent,
    ModelNodeUnregisteredEvent,
    ModelRuntimeEventPayloadUnion,
    ModelRuntimeReadyEvent,
    ModelSubscriptionCreatedEvent,
    ModelSubscriptionFailedEvent,
    ModelSubscriptionRemovedEvent,
    ModelWiringErrorEvent,
    ModelWiringResultEvent,
)

# ============================================================================
# ModelNodeRegisteredEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelNodeRegisteredEvent:
    """Test cases for ModelNodeRegisteredEvent."""

    def test_instantiation_required_fields(self):
        """Test event creation with required fields only."""
        node_id = uuid4()
        event = ModelNodeRegisteredEvent(
            node_id=node_id,
            node_name="test-node",
            node_type=EnumNodeKind.COMPUTE,
        )

        assert event.node_id == node_id
        assert event.node_name == "test-node"
        assert event.node_type == EnumNodeKind.COMPUTE
        assert event.event_type == "onex.runtime.node.registered"
        assert event.contract_path is None
        assert event.declared_subscriptions == []
        assert isinstance(event.event_id, UUID)
        assert isinstance(event.timestamp, datetime)

    def test_instantiation_all_fields(self):
        """Test event creation with all fields provided."""
        node_id = uuid4()
        correlation_id = uuid4()
        event = ModelNodeRegisteredEvent(
            node_id=node_id,
            node_name="full-node",
            node_type=EnumNodeKind.ORCHESTRATOR,
            correlation_id=correlation_id,
            contract_path="/path/to/contract.yaml",
            declared_subscriptions=["topic.a", "topic.b"],
        )

        assert event.node_id == node_id
        assert event.node_name == "full-node"
        assert event.node_type == EnumNodeKind.ORCHESTRATOR
        assert event.correlation_id == correlation_id
        assert event.contract_path == "/path/to/contract.yaml"
        assert event.declared_subscriptions == ["topic.a", "topic.b"]

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        node_id = uuid4()
        correlation_id = uuid4()
        event = ModelNodeRegisteredEvent.create(
            node_id=node_id,
            node_name="factory-node",
            node_type=EnumNodeKind.EFFECT,
            correlation_id=correlation_id,
            contract_path="/path/contract.yaml",
            declared_subscriptions=["events.*"],
        )

        assert event.node_id == node_id
        assert event.node_name == "factory-node"
        assert event.node_type == EnumNodeKind.EFFECT
        assert event.correlation_id == correlation_id
        assert event.contract_path == "/path/contract.yaml"
        assert event.declared_subscriptions == ["events.*"]

    def test_factory_method_defaults(self):
        """Test factory method with default values."""
        node_id = uuid4()
        event = ModelNodeRegisteredEvent.create(
            node_id=node_id,
            node_name="minimal-node",
            node_type=EnumNodeKind.REDUCER,
        )

        assert event.correlation_id is None
        assert event.contract_path is None
        assert event.declared_subscriptions == []

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        node_id = uuid4()
        original = ModelNodeRegisteredEvent.create(
            node_id=node_id,
            node_name="serialized-node",
            node_type=EnumNodeKind.COMPUTE,
            declared_subscriptions=["topic.x"],
        )

        json_str = original.model_dump_json()
        restored = ModelNodeRegisteredEvent.model_validate_json(json_str)

        assert restored.node_id == original.node_id
        assert restored.node_name == original.node_name
        assert restored.node_type == original.node_type
        assert restored.declared_subscriptions == original.declared_subscriptions

    def test_all_node_kinds(self):
        """Test event creation with all EnumNodeKind values."""
        node_id = uuid4()
        for node_kind in EnumNodeKind:
            event = ModelNodeRegisteredEvent(
                node_id=node_id,
                node_name=f"{node_kind.value}-node",
                node_type=node_kind,
            )
            assert event.node_type == node_kind


# ============================================================================
# ModelNodeUnregisteredEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelNodeUnregisteredEvent:
    """Test cases for ModelNodeUnregisteredEvent."""

    def test_instantiation_required_fields(self):
        """Test event creation with required fields only."""
        node_id = uuid4()
        event = ModelNodeUnregisteredEvent(
            node_id=node_id,
            node_name="unregistered-node",
        )

        assert event.node_id == node_id
        assert event.node_name == "unregistered-node"
        assert event.event_type == "onex.runtime.node.unregistered"
        assert event.reason == "unregistered"
        assert event.active_subscriptions == []

    def test_instantiation_all_fields(self):
        """Test event creation with all fields provided."""
        node_id = uuid4()
        correlation_id = uuid4()
        event = ModelNodeUnregisteredEvent(
            node_id=node_id,
            node_name="full-unregistered",
            reason="graceful_shutdown",
            correlation_id=correlation_id,
            active_subscriptions=["topic.1", "topic.2"],
        )

        assert event.node_id == node_id
        assert event.reason == "graceful_shutdown"
        assert event.active_subscriptions == ["topic.1", "topic.2"]

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        node_id = uuid4()
        event = ModelNodeUnregisteredEvent.create(
            node_id=node_id,
            node_name="factory-unregistered",
            reason="error",
            active_subscriptions=["cleanup.topic"],
        )

        assert event.node_id == node_id
        assert event.reason == "error"
        assert event.active_subscriptions == ["cleanup.topic"]

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        node_id = uuid4()
        original = ModelNodeUnregisteredEvent.create(
            node_id=node_id,
            node_name="serialized-unregistered",
            reason="forced",
        )

        json_str = original.model_dump_json()
        restored = ModelNodeUnregisteredEvent.model_validate_json(json_str)

        assert restored.node_id == original.node_id
        assert restored.reason == original.reason


# ============================================================================
# ModelSubscriptionCreatedEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelSubscriptionCreatedEvent:
    """Test cases for ModelSubscriptionCreatedEvent."""

    def test_instantiation_required_fields(self):
        """Test event creation with required fields only."""
        node_id = uuid4()
        event = ModelSubscriptionCreatedEvent(
            node_id=node_id,
            topic="events.test",
        )

        assert event.node_id == node_id
        assert event.topic == "events.test"
        assert event.event_type == "onex.runtime.subscription.created"
        assert isinstance(event.subscription_id, UUID)
        assert event.handler_name is None
        assert isinstance(event.subscribed_at, datetime)
        assert event.event_bus_type == "inmemory"

    def test_instantiation_all_fields(self):
        """Test event creation with all fields provided."""
        node_id = uuid4()
        subscription_id = uuid4()
        correlation_id = uuid4()
        event = ModelSubscriptionCreatedEvent(
            subscription_id=subscription_id,
            node_id=node_id,
            topic="events.full",
            handler_name="on_event_received",
            correlation_id=correlation_id,
            event_bus_type="kafka",
        )

        assert event.subscription_id == subscription_id
        assert event.handler_name == "on_event_received"
        assert event.event_bus_type == "kafka"

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        node_id = uuid4()
        subscription_id = uuid4()
        event = ModelSubscriptionCreatedEvent.create(
            node_id=node_id,
            topic="factory.topic",
            subscription_id=subscription_id,
            handler_name="handler_method",
            event_bus_type="redis",
        )

        assert event.subscription_id == subscription_id
        assert event.topic == "factory.topic"
        assert event.handler_name == "handler_method"
        assert event.event_bus_type == "redis"

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        node_id = uuid4()
        original = ModelSubscriptionCreatedEvent.create(
            node_id=node_id,
            topic="serialized.topic",
        )

        json_str = original.model_dump_json()
        restored = ModelSubscriptionCreatedEvent.model_validate_json(json_str)

        assert restored.node_id == original.node_id
        assert restored.topic == original.topic


# ============================================================================
# ModelSubscriptionFailedEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelSubscriptionFailedEvent:
    """Test cases for ModelSubscriptionFailedEvent."""

    def test_instantiation_required_fields(self):
        """Test event creation with required fields only."""
        node_id = uuid4()
        event = ModelSubscriptionFailedEvent(
            node_id=node_id,
            topic="events.failed",
            error_code="CONNECTION_ERROR",
            error_message="Unable to connect to event bus",
        )

        assert event.node_id == node_id
        assert event.topic == "events.failed"
        assert event.error_code == "CONNECTION_ERROR"
        assert event.error_message == "Unable to connect to event bus"
        assert event.event_type == "onex.runtime.subscription.failed"
        assert event.retry_count == 0
        assert event.retryable is True
        assert isinstance(event.failed_at, datetime)

    def test_instantiation_all_fields(self):
        """Test event creation with all fields provided."""
        node_id = uuid4()
        event = ModelSubscriptionFailedEvent(
            node_id=node_id,
            topic="events.critical",
            error_code="AUTH_FAILED",
            error_message="Authentication failed",
            retry_count=3,
            retryable=False,
        )

        assert event.retry_count == 3
        assert event.retryable is False

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        node_id = uuid4()
        event = ModelSubscriptionFailedEvent.create(
            node_id=node_id,
            topic="factory.failed",
            error_code="TIMEOUT",
            error_message="Connection timeout",
            retry_count=5,
            retryable=True,
        )

        assert event.error_code == "TIMEOUT"
        assert event.retry_count == 5
        assert event.retryable is True

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        node_id = uuid4()
        original = ModelSubscriptionFailedEvent.create(
            node_id=node_id,
            topic="serialized.failed",
            error_code="PARSE_ERROR",
            error_message="Invalid message format",
        )

        json_str = original.model_dump_json()
        restored = ModelSubscriptionFailedEvent.model_validate_json(json_str)

        assert restored.node_id == original.node_id
        assert restored.error_code == original.error_code


# ============================================================================
# ModelSubscriptionRemovedEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelSubscriptionRemovedEvent:
    """Test cases for ModelSubscriptionRemovedEvent."""

    def test_instantiation_required_fields(self):
        """Test event creation with required fields only."""
        subscription_id = uuid4()
        node_id = uuid4()
        event = ModelSubscriptionRemovedEvent(
            subscription_id=subscription_id,
            node_id=node_id,
            topic="events.removed",
        )

        assert event.subscription_id == subscription_id
        assert event.node_id == node_id
        assert event.topic == "events.removed"
        assert event.event_type == "onex.runtime.subscription.removed"
        assert event.reason == "unsubscribed"
        assert isinstance(event.removed_at, datetime)

    def test_instantiation_all_fields(self):
        """Test event creation with all fields provided."""
        subscription_id = uuid4()
        node_id = uuid4()
        event = ModelSubscriptionRemovedEvent(
            subscription_id=subscription_id,
            node_id=node_id,
            topic="events.full",
            reason="node_shutdown",
        )

        assert event.reason == "node_shutdown"

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        subscription_id = uuid4()
        node_id = uuid4()
        event = ModelSubscriptionRemovedEvent.create(
            subscription_id=subscription_id,
            node_id=node_id,
            topic="factory.removed",
            reason="error",
        )

        assert event.topic == "factory.removed"
        assert event.reason == "error"

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        subscription_id = uuid4()
        node_id = uuid4()
        original = ModelSubscriptionRemovedEvent.create(
            subscription_id=subscription_id,
            node_id=node_id,
            topic="serialized.removed",
        )

        json_str = original.model_dump_json()
        restored = ModelSubscriptionRemovedEvent.model_validate_json(json_str)

        assert restored.subscription_id == original.subscription_id
        assert restored.topic == original.topic


# ============================================================================
# ModelRuntimeReadyEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelRuntimeReadyEvent:
    """Test cases for ModelRuntimeReadyEvent."""

    def test_instantiation_defaults(self):
        """Test event creation with default values."""
        event = ModelRuntimeReadyEvent()

        assert event.event_type == "onex.runtime.ready"
        assert isinstance(event.runtime_id, UUID)
        assert event.node_count == 0
        assert event.subscription_count == 0
        assert isinstance(event.ready_at, datetime)
        assert event.initialization_duration_ms is None
        assert event.event_bus_type == "inmemory"
        assert event.nodes_wired == []

    def test_instantiation_all_fields(self):
        """Test event creation with all fields provided."""
        runtime_id = uuid4()
        event = ModelRuntimeReadyEvent(
            runtime_id=runtime_id,
            node_count=3,
            subscription_count=5,
            initialization_duration_ms=150.5,
            event_bus_type="kafka",
            nodes_wired=["node-a", "node-b", "node-c"],
        )

        assert event.runtime_id == runtime_id
        assert event.node_count == 3
        assert event.subscription_count == 5
        assert event.initialization_duration_ms == 150.5
        assert event.event_bus_type == "kafka"
        assert event.nodes_wired == ["node-a", "node-b", "node-c"]

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        event = ModelRuntimeReadyEvent.create(
            subscription_count=10,
            initialization_duration_ms=200.0,
            event_bus_type="redis",
            nodes_wired=["node-1", "node-2"],
        )

        # node_count should be derived from nodes_wired
        assert event.node_count == 2
        assert event.subscription_count == 10
        assert event.initialization_duration_ms == 200.0

    def test_factory_method_explicit_node_count(self):
        """Test factory method with explicit node_count."""
        event = ModelRuntimeReadyEvent.create(
            node_count=3,
            nodes_wired=["a", "b", "c"],
        )

        assert event.node_count == 3

    def test_model_validator_node_count_consistency_valid(self):
        """Test validator passes when node_count matches nodes_wired length."""
        event = ModelRuntimeReadyEvent(
            node_count=2,
            nodes_wired=["node-a", "node-b"],
        )
        assert event.node_count == 2

    def test_model_validator_node_count_consistency_invalid(self):
        """Test validator fails when node_count doesn't match nodes_wired length."""
        with pytest.raises(ValueError) as exc_info:
            ModelRuntimeReadyEvent(
                node_count=5,
                nodes_wired=["node-a", "node-b"],
            )
        assert "does not match" in str(exc_info.value)

    def test_model_validator_empty_nodes_allowed(self):
        """Test validator allows node_count=0 with empty nodes_wired."""
        event = ModelRuntimeReadyEvent(
            node_count=0,
            nodes_wired=[],
        )
        assert event.node_count == 0
        assert event.nodes_wired == []

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        original = ModelRuntimeReadyEvent.create(
            subscription_count=15,
            nodes_wired=["node-x", "node-y"],
        )

        json_str = original.model_dump_json()
        restored = ModelRuntimeReadyEvent.model_validate_json(json_str)

        assert restored.node_count == original.node_count
        assert restored.subscription_count == original.subscription_count
        assert restored.nodes_wired == original.nodes_wired


# ============================================================================
# ModelNodeGraphReadyEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelNodeGraphReadyEvent:
    """Test cases for ModelNodeGraphReadyEvent."""

    def test_instantiation_defaults(self):
        """Test event creation with default values."""
        event = ModelNodeGraphReadyEvent()

        assert event.event_type == "onex.runtime.node_graph.ready"
        assert isinstance(event.graph_id, UUID)
        assert event.node_count == 0
        assert event.nodes == []
        assert event.instantiation_duration_ms is None

    def test_instantiation_with_nodes(self):
        """Test event creation with node graph info."""
        node_info = ModelNodeGraphInfo(
            node_id=uuid4(),
            node_name="compute-node",
            node_type="COMPUTE",
            declared_subscriptions=["events.*"],
        )
        event = ModelNodeGraphReadyEvent(
            node_count=1,
            nodes=[node_info],
            instantiation_duration_ms=50.0,
        )

        assert event.node_count == 1
        assert len(event.nodes) == 1
        assert event.nodes[0].node_name == "compute-node"
        assert event.instantiation_duration_ms == 50.0

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        node_infos = [
            ModelNodeGraphInfo(
                node_id=uuid4(),
                node_name=f"node-{i}",
                node_type="EFFECT",
            )
            for i in range(3)
        ]
        event = ModelNodeGraphReadyEvent.create(
            nodes=node_infos,
            instantiation_duration_ms=100.0,
        )

        # node_count should be derived from nodes
        assert event.node_count == 3
        assert len(event.nodes) == 3

    def test_factory_method_explicit_node_count(self):
        """Test factory method with explicit node_count."""
        nodes = [
            ModelNodeGraphInfo(
                node_id=uuid4(),
                node_name="test",
                node_type="REDUCER",
            )
        ]
        event = ModelNodeGraphReadyEvent.create(
            node_count=1,
            nodes=nodes,
        )

        assert event.node_count == 1

    def test_model_validator_node_count_consistency_valid(self):
        """Test validator passes when node_count matches nodes length."""
        nodes = [
            ModelNodeGraphInfo(
                node_id=uuid4(),
                node_name="node-a",
                node_type="COMPUTE",
            ),
            ModelNodeGraphInfo(
                node_id=uuid4(),
                node_name="node-b",
                node_type="EFFECT",
            ),
        ]
        event = ModelNodeGraphReadyEvent(
            node_count=2,
            nodes=nodes,
        )
        assert event.node_count == 2

    def test_model_validator_node_count_consistency_invalid(self):
        """Test validator fails when node_count doesn't match nodes length."""
        nodes = [
            ModelNodeGraphInfo(
                node_id=uuid4(),
                node_name="single",
                node_type="COMPUTE",
            )
        ]
        with pytest.raises(ModelOnexError) as exc_info:
            ModelNodeGraphReadyEvent(
                node_count=5,
                nodes=nodes,
            )
        assert "does not match" in str(exc_info.value)

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        nodes = [
            ModelNodeGraphInfo(
                node_id=uuid4(),
                node_name="serialized-node",
                node_type="ORCHESTRATOR",
            )
        ]
        original = ModelNodeGraphReadyEvent.create(
            nodes=nodes,
        )

        json_str = original.model_dump_json()
        restored = ModelNodeGraphReadyEvent.model_validate_json(json_str)

        assert restored.node_count == original.node_count
        assert len(restored.nodes) == len(original.nodes)
        assert restored.nodes[0].node_name == "serialized-node"


# ============================================================================
# ModelWiringResultEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelWiringResultEvent:
    """Test cases for ModelWiringResultEvent."""

    def test_instantiation_defaults(self):
        """Test event creation with default values."""
        event = ModelWiringResultEvent()

        assert event.event_type == "onex.runtime.wiring.result"
        assert event.success is False
        assert event.total_nodes == 0
        assert event.successful_nodes == 0
        assert event.failed_nodes == 0
        assert event.total_subscriptions == 0
        assert event.successful_subscriptions == 0
        assert event.failed_subscriptions == 0
        assert event.wiring_duration_ms is None
        assert event.errors == []

    def test_instantiation_success_case(self):
        """Test event creation for successful wiring."""
        event = ModelWiringResultEvent(
            success=True,
            total_nodes=5,
            successful_nodes=5,
            failed_nodes=0,
            total_subscriptions=10,
            successful_subscriptions=10,
            failed_subscriptions=0,
            wiring_duration_ms=250.5,
        )

        assert event.success is True
        assert event.total_nodes == 5
        assert event.successful_nodes == 5
        assert event.total_subscriptions == 10

    def test_instantiation_with_errors(self):
        """Test event creation with wiring errors."""
        error_info = ModelWiringErrorInfo(
            node_id=uuid4(),
            topic="events.failed",
            error_code="TIMEOUT",
            error_message="Connection timeout",
            retryable=True,
        )
        event = ModelWiringResultEvent(
            success=False,
            total_nodes=3,
            successful_nodes=2,
            failed_nodes=1,
            errors=[error_info],
        )

        assert event.success is False
        assert event.failed_nodes == 1
        assert len(event.errors) == 1
        assert event.errors[0].error_code == "TIMEOUT"

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        event = ModelWiringResultEvent.create(
            success=True,
            total_nodes=10,
            successful_nodes=10,
            total_subscriptions=20,
            successful_subscriptions=20,
            wiring_duration_ms=500.0,
        )

        assert event.success is True
        assert event.total_nodes == 10
        assert event.wiring_duration_ms == 500.0

    def test_validation_non_negative_counts(self):
        """Test validation of non-negative count fields."""
        with pytest.raises(ValidationError):
            ModelWiringResultEvent(total_nodes=-1)

        with pytest.raises(ValidationError):
            ModelWiringResultEvent(failed_subscriptions=-1)

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        errors = [
            ModelWiringErrorInfo(
                error_code="TEST_ERROR",
                error_message="Test error message",
            )
        ]
        original = ModelWiringResultEvent.create(
            success=False,
            total_nodes=5,
            failed_nodes=1,
            errors=errors,
        )

        json_str = original.model_dump_json()
        restored = ModelWiringResultEvent.model_validate_json(json_str)

        assert restored.success == original.success
        assert restored.total_nodes == original.total_nodes
        assert len(restored.errors) == 1


# ============================================================================
# ModelWiringErrorEvent Tests
# ============================================================================


@pytest.mark.unit
class TestModelWiringErrorEvent:
    """Test cases for ModelWiringErrorEvent."""

    def test_instantiation_required_fields(self):
        """Test event creation with required fields only."""
        event = ModelWiringErrorEvent(
            error_code="CRITICAL_ERROR",
            error_message="Unable to complete wiring",
        )

        assert event.event_type == "onex.runtime.wiring.error"
        assert event.error_code == "CRITICAL_ERROR"
        assert event.error_message == "Unable to complete wiring"
        assert event.affected_nodes == []
        assert event.partial_success is False
        assert event.successful_subscriptions == 0
        assert event.failed_subscriptions == 0
        assert event.stack_trace is None

    def test_instantiation_all_fields(self):
        """Test event creation with all fields provided."""
        event = ModelWiringErrorEvent(
            error_code="EVENT_BUS_FAILURE",
            error_message="Event bus connection lost",
            affected_nodes=["node-a", "node-b"],
            partial_success=True,
            successful_subscriptions=5,
            failed_subscriptions=3,
            stack_trace="Traceback (most recent call last):\n...",
        )

        assert event.affected_nodes == ["node-a", "node-b"]
        assert event.partial_success is True
        assert event.successful_subscriptions == 5
        assert event.stack_trace is not None

    def test_factory_method_create(self):
        """Test factory method for creating events."""
        event = ModelWiringErrorEvent.create(
            error_code="CONFIG_ERROR",
            error_message="Invalid configuration",
            affected_nodes=["config-node"],
            partial_success=False,
        )

        assert event.error_code == "CONFIG_ERROR"
        assert event.affected_nodes == ["config-node"]

    def test_validation_non_negative_counts(self):
        """Test validation of non-negative count fields."""
        with pytest.raises(ValidationError):
            ModelWiringErrorEvent(
                error_code="TEST",
                error_message="Test",
                successful_subscriptions=-1,
            )

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        original = ModelWiringErrorEvent.create(
            error_code="SERIALIZATION_TEST",
            error_message="Testing serialization",
            affected_nodes=["test-node"],
        )

        json_str = original.model_dump_json()
        restored = ModelWiringErrorEvent.model_validate_json(json_str)

        assert restored.error_code == original.error_code
        assert restored.affected_nodes == original.affected_nodes


# ============================================================================
# Union Type Tests
# ============================================================================


@pytest.mark.unit
class TestModelEventPayloadUnion:
    """Test cases for ModelEventPayloadUnion type alias."""

    def test_union_includes_all_runtime_events(self):
        """Test that union type accepts all 9 runtime event types."""
        events: list[ModelEventPayloadUnion] = [
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
                topic="test",
            ),
            ModelSubscriptionFailedEvent(
                node_id=uuid4(),
                topic="test",
                error_code="ERROR",
                error_message="message",
            ),
            ModelSubscriptionRemovedEvent(
                subscription_id=uuid4(),
                node_id=uuid4(),
                topic="test",
            ),
            ModelRuntimeReadyEvent(),
            ModelNodeGraphReadyEvent(),
            ModelWiringResultEvent(),
            ModelWiringErrorEvent(
                error_code="ERROR",
                error_message="message",
            ),
        ]

        assert len(events) == 9

        for event in events:
            # All events should have event_type field
            assert hasattr(event, "event_type")
            # All events should be serializable
            json_str = event.model_dump_json()
            assert json_str is not None

    def test_union_type_discrimination_by_event_type(self):
        """Test that events can be discriminated by event_type field."""
        events = [
            ModelNodeRegisteredEvent(
                node_id=uuid4(),
                node_name="test",
                node_type=EnumNodeKind.COMPUTE,
            ),
            ModelWiringResultEvent(success=True),
            ModelRuntimeReadyEvent(),
        ]

        event_types = [event.event_type for event in events]

        assert "onex.runtime.node.registered" in event_types
        assert "onex.runtime.wiring.result" in event_types
        assert "onex.runtime.ready" in event_types

    def test_isinstance_checks(self):
        """Test isinstance checks for union types."""
        event: ModelEventPayloadUnion = ModelNodeRegisteredEvent(
            node_id=uuid4(),
            node_name="test",
            node_type=EnumNodeKind.COMPUTE,
        )

        assert isinstance(event, ModelNodeRegisteredEvent)
        assert not isinstance(event, ModelWiringResultEvent)

    def test_runtime_event_union_matches_main_union(self):
        """Test that ModelRuntimeEventPayloadUnion equals ModelEventPayloadUnion."""
        # Currently they're the same (discovery events excluded)
        # This test documents the current behavior
        registered = ModelNodeRegisteredEvent(
            node_id=uuid4(),
            node_name="test",
            node_type=EnumNodeKind.COMPUTE,
        )

        # Both type aliases should accept the same events
        runtime_typed: ModelRuntimeEventPayloadUnion = registered
        main_typed: ModelEventPayloadUnion = registered

        assert runtime_typed == main_typed


# ============================================================================
# Module Exports Tests
# ============================================================================


@pytest.mark.unit
class TestModuleExports:
    """Test cases for module __all__ exports."""

    def test_all_exports_importable(self):
        """Test that all exported names are importable."""
        from omnibase_core.models.events.payloads import (
            ModelEventPayloadUnion,
            ModelNodeGraphReadyEvent,
            ModelNodeRegisteredEvent,
            ModelNodeUnregisteredEvent,
            ModelRuntimeEventPayloadUnion,
            ModelRuntimeReadyEvent,
            ModelSubscriptionCreatedEvent,
            ModelSubscriptionFailedEvent,
            ModelSubscriptionRemovedEvent,
            ModelWiringErrorEvent,
            ModelWiringResultEvent,
        )

        # All should be classes or type aliases
        assert ModelEventPayloadUnion is not None
        assert ModelRuntimeEventPayloadUnion is not None
        assert ModelNodeRegisteredEvent is not None
        assert ModelNodeUnregisteredEvent is not None
        assert ModelSubscriptionCreatedEvent is not None
        assert ModelSubscriptionFailedEvent is not None
        assert ModelSubscriptionRemovedEvent is not None
        assert ModelRuntimeReadyEvent is not None
        assert ModelNodeGraphReadyEvent is not None
        assert ModelWiringResultEvent is not None
        assert ModelWiringErrorEvent is not None

    def test_event_type_constants_exist(self):
        """Test that event type constants are accessible."""
        from omnibase_core.models.events.model_node_graph_ready_event import (
            NODE_GRAPH_READY_EVENT,
        )
        from omnibase_core.models.events.model_node_registered_event import (
            NODE_REGISTERED_EVENT,
        )
        from omnibase_core.models.events.model_node_unregistered_event import (
            NODE_UNREGISTERED_EVENT,
        )
        from omnibase_core.models.events.model_runtime_ready_event import (
            RUNTIME_READY_EVENT,
        )
        from omnibase_core.models.events.model_subscription_created_event import (
            SUBSCRIPTION_CREATED_EVENT,
        )
        from omnibase_core.models.events.model_subscription_failed_event import (
            SUBSCRIPTION_FAILED_EVENT,
        )
        from omnibase_core.models.events.model_subscription_removed_event import (
            SUBSCRIPTION_REMOVED_EVENT,
        )
        from omnibase_core.models.events.model_wiring_error_event import (
            WIRING_ERROR_EVENT,
        )
        from omnibase_core.models.events.model_wiring_result_event import (
            WIRING_RESULT_EVENT,
        )

        assert NODE_REGISTERED_EVENT == "onex.runtime.node.registered"
        assert NODE_UNREGISTERED_EVENT == "onex.runtime.node.unregistered"
        assert SUBSCRIPTION_CREATED_EVENT == "onex.runtime.subscription.created"
        assert SUBSCRIPTION_FAILED_EVENT == "onex.runtime.subscription.failed"
        assert SUBSCRIPTION_REMOVED_EVENT == "onex.runtime.subscription.removed"
        assert RUNTIME_READY_EVENT == "onex.runtime.ready"
        assert NODE_GRAPH_READY_EVENT == "onex.runtime.node_graph.ready"
        assert WIRING_RESULT_EVENT == "onex.runtime.wiring.result"
        assert WIRING_ERROR_EVENT == "onex.runtime.wiring.error"


# ============================================================================
# Edge Cases and Error Conditions
# ============================================================================


@pytest.mark.unit
class TestEdgeCasesAndErrors:
    """Test edge cases and error conditions for event payloads."""

    def test_extra_fields_forbidden(self):
        """Test that extra fields are rejected (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            ModelNodeRegisteredEvent(
                node_id=uuid4(),
                node_name="test",
                node_type=EnumNodeKind.COMPUTE,
                unknown_field="should_fail",  # type: ignore[call-arg]
            )
        assert "Extra inputs are not permitted" in str(exc_info.value)

    def test_required_fields_missing(self):
        """Test that missing required fields raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeRegisteredEvent(
                node_name="test",
                node_type=EnumNodeKind.COMPUTE,
                # Missing required node_id
            )

    def test_invalid_uuid_field(self):
        """Test that invalid UUID values raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeRegisteredEvent(
                node_id="not-a-uuid",  # type: ignore[arg-type]
                node_name="test",
                node_type=EnumNodeKind.COMPUTE,
            )

    def test_invalid_enum_value(self):
        """Test that invalid enum values raise ValidationError."""
        with pytest.raises(ValidationError):
            ModelNodeRegisteredEvent(
                node_id=uuid4(),
                node_name="test",
                node_type="INVALID_TYPE",  # type: ignore[arg-type]
            )

    def test_validate_assignment_enabled(self):
        """Test that field assignment is validated."""
        event = ModelWiringResultEvent(success=True)

        with pytest.raises(ValidationError):
            event.total_nodes = -1  # type: ignore[misc]  # Should fail ge=0 constraint

    def test_from_attributes_enabled(self):
        """Test that from_attributes=True allows attribute-based construction."""

        class MockEvent:
            """Mock class with matching attributes."""

            event_type = "onex.runtime.wiring.result"
            success = True
            total_nodes = 5
            successful_nodes = 5
            failed_nodes = 0
            total_subscriptions = 10
            successful_subscriptions = 10
            failed_subscriptions = 0
            wiring_duration_ms = None
            errors: list = []
            event_id = uuid4()
            correlation_id = None
            timestamp = datetime.now(UTC)
            source_node_id = None

        mock = MockEvent()
        event = ModelWiringResultEvent.model_validate(mock)

        assert event.success is True
        assert event.total_nodes == 5

    def test_unicode_in_string_fields(self):
        """Test that unicode characters are handled correctly."""
        event = ModelNodeRegisteredEvent(
            node_id=uuid4(),
            node_name="test-node-",
            node_type=EnumNodeKind.COMPUTE,
            contract_path="/path/to/contract.yaml",
        )

        assert "" in event.node_name

        json_str = event.model_dump_json()
        restored = ModelNodeRegisteredEvent.model_validate_json(json_str)
        assert "" in restored.node_name

    def test_empty_lists_allowed(self):
        """Test that empty lists are valid for list fields."""
        event = ModelNodeRegisteredEvent(
            node_id=uuid4(),
            node_name="test",
            node_type=EnumNodeKind.COMPUTE,
            declared_subscriptions=[],
        )

        assert event.declared_subscriptions == []

    def test_large_subscription_lists(self):
        """Test handling of large subscription lists."""
        topics = [f"topic.{i}" for i in range(1000)]
        event = ModelNodeRegisteredEvent(
            node_id=uuid4(),
            node_name="high-volume-node",
            node_type=EnumNodeKind.ORCHESTRATOR,
            declared_subscriptions=topics,
        )

        assert len(event.declared_subscriptions) == 1000

        # Verify serialization works
        json_str = event.model_dump_json()
        restored = ModelNodeRegisteredEvent.model_validate_json(json_str)
        assert len(restored.declared_subscriptions) == 1000


# ============================================================================
# Helper Model Tests
# ============================================================================


@pytest.mark.unit
class TestModelWiringErrorInfo:
    """Test cases for ModelWiringErrorInfo helper model."""

    def test_instantiation_required_fields(self):
        """Test creation with required fields only."""
        error = ModelWiringErrorInfo(
            error_code="CONNECTION_ERROR",
            error_message="Unable to connect",
        )

        assert error.error_code == "CONNECTION_ERROR"
        assert error.error_message == "Unable to connect"
        assert error.node_id is None
        assert error.topic is None
        assert error.retryable is False

    def test_instantiation_all_fields(self):
        """Test creation with all fields."""
        node_id = uuid4()
        error = ModelWiringErrorInfo(
            node_id=node_id,
            topic="events.failed",
            error_code="TIMEOUT",
            error_message="Connection timeout",
            retryable=True,
        )

        assert error.node_id == node_id
        assert error.topic == "events.failed"
        assert error.retryable is True

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        original = ModelWiringErrorInfo(
            error_code="TEST",
            error_message="Test error",
            retryable=True,
        )

        json_str = original.model_dump_json()
        restored = ModelWiringErrorInfo.model_validate_json(json_str)

        assert restored.error_code == original.error_code
        assert restored.retryable == original.retryable


@pytest.mark.unit
class TestModelNodeGraphInfo:
    """Test cases for ModelNodeGraphInfo helper model."""

    def test_instantiation_required_fields(self):
        """Test creation with required fields only."""
        node_id = uuid4()
        info = ModelNodeGraphInfo(
            node_id=node_id,
            node_name="compute-node",
            node_type="COMPUTE",
        )

        assert info.node_id == node_id
        assert info.node_name == "compute-node"
        assert info.node_type == "COMPUTE"
        assert info.declared_subscriptions == []
        assert info.contract_path is None

    def test_instantiation_all_fields(self):
        """Test creation with all fields."""
        node_id = uuid4()
        info = ModelNodeGraphInfo(
            node_id=node_id,
            node_name="full-node",
            node_type="ORCHESTRATOR",
            declared_subscriptions=["events.*", "commands.*"],
            contract_path="/path/to/contract.yaml",
        )

        assert info.declared_subscriptions == ["events.*", "commands.*"]
        assert info.contract_path == "/path/to/contract.yaml"

    def test_serialization_round_trip(self):
        """Test JSON serialization and deserialization."""
        node_id = uuid4()
        original = ModelNodeGraphInfo(
            node_id=node_id,
            node_name="serialized",
            node_type="REDUCER",
        )

        json_str = original.model_dump_json()
        restored = ModelNodeGraphInfo.model_validate_json(json_str)

        assert restored.node_id == original.node_id
        assert restored.node_name == original.node_name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
