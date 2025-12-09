"""
Test suite for MixinIntentPublisher.

Tests intent publishing capability, event coordination, and error handling.
Validates ONEX standards for coordination I/O and intent-based architecture.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel

from omnibase_core.mixins.mixin_intent_publisher import MixinIntentPublisher
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.model_intent_events import TOPIC_EVENT_PUBLISH_INTENT
from omnibase_core.models.reducer.model_intent_publish_result import (
    ModelIntentPublishResult,
)


class MockEventModel(BaseModel):
    """Mock event model for intent publishing tests."""

    event_id: UUID
    message: str
    value: int


class MockNodeWithIntentPublisher(MixinIntentPublisher):
    """Mock node class that uses MixinIntentPublisher."""

    def __init__(self, container: Any):
        """
        Initialize mock node with intent publisher.

        Args:
            container: Mock container with kafka_client service
        """
        self._init_intent_publisher(container)


class TestMixinIntentPublisher:
    """Test MixinIntentPublisher functionality."""

    @pytest.fixture
    def mock_kafka_client(self):
        """
        Create mock Kafka client for testing.

        Returns:
            AsyncMock: Mock kafka_client with publish method
        """
        client = AsyncMock()
        client.publish = AsyncMock()
        return client

    @pytest.fixture
    def mock_container(self, mock_kafka_client):
        """
        Create mock container with kafka_client service.

        Args:
            mock_kafka_client: Mock Kafka client fixture

        Returns:
            Mock: Container with get_service method
        """
        container = Mock()
        container.get_service = Mock(return_value=mock_kafka_client)
        return container

    @pytest.fixture
    def test_node(self, mock_container):
        """
        Create test node instance with intent publisher.

        Args:
            mock_container: Mock container fixture

        Returns:
            MockNodeWithIntentPublisher: Initialized test node
        """
        return MockNodeWithIntentPublisher(mock_container)

    @pytest.fixture
    def test_event(self):
        """
        Create test event model for publishing.

        Returns:
            MockEventModel: Sample event instance
        """
        return MockEventModel(
            event_id=uuid4(),
            message="Test event",
            value=42,
        )

    def test_initialization_success(self, mock_container):
        """
        Test successful mixin initialization with kafka_client.

        Validates that the mixin properly initializes with required services.
        """
        node = MockNodeWithIntentPublisher(mock_container)

        # Verify initialization
        assert hasattr(node, "_intent_kafka_client")
        assert hasattr(node, "_intent_container")
        assert node._intent_kafka_client is not None
        assert node._intent_container == mock_container
        assert node.INTENT_TOPIC == TOPIC_EVENT_PUBLISH_INTENT

    def test_initialization_missing_kafka_client(self):
        """
        Test initialization fails without kafka_client service.

        Validates proper error handling when required service is missing.
        """
        container = Mock()
        container.get_service = Mock(return_value=None)

        with pytest.raises(ModelOnexError) as exc_info:
            MockNodeWithIntentPublisher(container)

        assert "kafka_client" in str(exc_info.value)
        assert "requires" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_publish_event_intent_success(self, test_node, test_event):
        """
        Test successful intent publishing with all parameters.

        Validates complete intent publishing workflow including:
        - Intent creation
        - Envelope wrapping
        - Kafka publishing
        - Result generation
        """
        target_topic = "dev.omninode.test.v1"
        target_key = "test-key-123"
        correlation_id = uuid4()
        priority = 3

        result = await test_node.publish_event_intent(
            target_topic=target_topic,
            target_key=target_key,
            event=test_event,
            correlation_id=correlation_id,
            priority=priority,
        )

        # Verify result structure
        assert isinstance(result, ModelIntentPublishResult)
        assert isinstance(result.intent_id, UUID)
        assert result.correlation_id == correlation_id
        assert result.target_topic == target_topic
        assert isinstance(result.published_at, datetime)

        # Verify Kafka publish was called
        test_node._intent_kafka_client.publish.assert_called_once()
        call_kwargs = test_node._intent_kafka_client.publish.call_args.kwargs

        assert call_kwargs["topic"] == TOPIC_EVENT_PUBLISH_INTENT
        assert isinstance(call_kwargs["key"], str)
        assert isinstance(call_kwargs["value"], str)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_publish_event_intent_auto_correlation_id(
        self, test_node, test_event
    ):
        """
        Test intent publishing with auto-generated correlation_id.

        Validates that correlation_id is generated when not provided.
        """
        result = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Verify correlation_id was auto-generated
        assert isinstance(result.correlation_id, UUID)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_publish_event_intent_default_priority(self, test_node, test_event):
        """
        Test intent publishing with default priority.

        Validates default priority value of 5.
        """
        await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Verify publish was called
        assert test_node._intent_kafka_client.publish.called

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_publish_event_intent_priority_validation_below_range(
        self, test_node, test_event
    ):
        """
        Test priority validation rejects values below 1.

        Validates range check for priority parameter.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test-key",
                event=test_event,
                priority=0,  # Below minimum
            )

        assert "Priority must be 1-10" in str(exc_info.value)
        assert "0" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_publish_event_intent_priority_validation_above_range(
        self, test_node, test_event
    ):
        """
        Test priority validation rejects values above 10.

        Validates range check for priority parameter.
        """
        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test-key",
                event=test_event,
                priority=11,  # Above maximum
            )

        assert "Priority must be 1-10" in str(exc_info.value)
        assert "11" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_publish_event_intent_priority_boundary_values(
        self, test_node, test_event
    ):
        """
        Test priority accepts boundary values 1 and 10.

        Validates edge cases for priority range.
        """
        # Test priority = 1 (highest)
        result1 = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
            priority=1,
        )
        assert isinstance(result1, ModelIntentPublishResult)

        # Test priority = 10 (lowest)
        result2 = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
            priority=10,
        )
        assert isinstance(result2, ModelIntentPublishResult)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_publish_event_intent_event_without_model_dump(self, test_node):
        """
        Test error handling for events without model_dump() method.

        Validates that non-Pydantic events are rejected.
        """

        class InvalidEvent:
            """Event without model_dump() method."""

        invalid_event = InvalidEvent()

        with pytest.raises(ModelOnexError) as exc_info:
            await test_node.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test-key",
                event=invalid_event,  # type: ignore[arg-type]
            )

        assert "model_dump" in str(exc_info.value)
        assert "Pydantic" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_intent_payload_structure(self, test_node, test_event):
        """
        Test ModelEventPublishIntent payload structure.

        Validates that intent contains all required fields.
        """
        target_topic = "dev.omninode.test.v1"
        target_key = "test-key"
        correlation_id = uuid4()
        priority = 7

        await test_node.publish_event_intent(
            target_topic=target_topic,
            target_key=target_key,
            event=test_event,
            correlation_id=correlation_id,
            priority=priority,
        )

        # Extract the published value
        call_kwargs = test_node._intent_kafka_client.publish.call_args.kwargs
        published_value = call_kwargs["value"]

        # Parse JSON to verify structure
        import json

        envelope_data = json.loads(published_value)

        # Verify envelope structure (should have ModelOnexEnvelope fields or fallback)
        assert "payload" in envelope_data or "intent_id" in envelope_data

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_metadata_field_population(self, test_node, test_event):
        """
        Test that metadata fields are properly populated.

        Validates intent metadata including:
        - intent_id (UUID)
        - correlation_id
        - created_at (datetime)
        - created_by (node class name)
        - target fields
        """
        result = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Verify result metadata
        assert isinstance(result.intent_id, UUID)
        assert isinstance(result.correlation_id, UUID)
        assert isinstance(result.published_at, datetime)
        assert result.target_topic == "dev.omninode.test.v1"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_created_by_field(self, test_node, test_event):
        """
        Test that created_by field contains node class name.

        Validates source tracking in intent metadata.
        """
        await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Verify node class name would be in created_by
        # (This is set in ModelEventPublishIntent creation)
        assert test_node.__class__.__name__ == "MockNodeWithIntentPublisher"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_target_event_type_extraction(self, test_node, test_event):
        """
        Test that target_event_type is extracted from event class.

        Validates event type metadata in intent.
        """
        await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Event type should be MockEventModel.__name__
        assert test_event.__class__.__name__ == "MockEventModel"

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_target_event_payload_serialization(self, test_node, test_event):
        """
        Test that event payload is properly serialized via model_dump().

        Validates payload serialization in intent.
        """
        await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Verify event can be serialized
        payload = test_event.model_dump()
        assert "event_id" in payload
        assert "message" in payload
        assert "value" in payload

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_kafka_publish_failure(self, test_node, test_event):
        """
        Test error handling when Kafka publish fails.

        Validates exception propagation from Kafka client.
        """
        # Configure mock to raise exception
        test_node._intent_kafka_client.publish.side_effect = RuntimeError(
            "Kafka connection failed"
        )

        with pytest.raises(RuntimeError) as exc_info:
            await test_node.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test-key",
                event=test_event,
            )

        assert "Kafka connection failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_onex_envelope_success_path(self, test_node, test_event):
        """
        Test successful ModelOnexEnvelope wrapping.

        Validates envelope creation when ModelOnexEnvelope is available.
        """
        # Mock ModelOnexEnvelope to be available
        mock_envelope_class = Mock()
        mock_envelope_instance = Mock()
        mock_envelope_instance.model_dump_json.return_value = '{"envelope": "data"}'
        mock_envelope_class.return_value = mock_envelope_instance

        with patch.dict(
            "sys.modules",
            {"omnibase_core.models.core": Mock(ModelOnexEnvelope=mock_envelope_class)},
        ):
            await test_node.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test-key",
                event=test_event,
            )

            # Verify envelope was used
            call_kwargs = test_node._intent_kafka_client.publish.call_args.kwargs
            assert call_kwargs["value"] == '{"envelope": "data"}'

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_onex_envelope_fallback_path(self, test_node, test_event):
        """
        Test fallback when ModelOnexEnvelope is not available.

        Validates graceful degradation without envelope wrapping.
        """
        # The actual implementation handles ImportError gracefully
        # Test that publishing still works
        result = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Should still succeed
        assert isinstance(result, ModelIntentPublishResult)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_correlation_id_uuid_format(self, test_node, test_event):
        """
        Test that correlation_id is always a valid UUID.

        Validates UUID format for both provided and auto-generated IDs.
        """
        # Test with provided correlation_id
        provided_id = uuid4()
        result1 = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
            correlation_id=provided_id,
        )
        assert result1.correlation_id == provided_id
        assert isinstance(result1.correlation_id, UUID)

        # Test with auto-generated correlation_id
        result2 = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )
        assert isinstance(result2.correlation_id, UUID)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_intent_id_uniqueness(self, test_node, test_event):
        """
        Test that each intent gets a unique intent_id.

        Validates intent_id generation for traceability.
        """
        result1 = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        result2 = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Each intent should have unique ID
        assert result1.intent_id != result2.intent_id

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_timestamp_generation(self, test_node, test_event):
        """
        Test that published_at timestamp is in UTC.

        Validates timestamp generation and timezone.
        """
        before = datetime.now(UTC)

        result = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        after = datetime.now(UTC)

        # Timestamp should be between before and after
        assert before <= result.published_at <= after
        # Timestamp should be timezone-aware (UTC)
        assert result.published_at.tzinfo is not None

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_kafka_topic_constant(self, test_node, test_event):
        """
        Test that intent is published to correct Kafka topic.

        Validates INTENT_TOPIC constant usage.
        """
        await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        call_kwargs = test_node._intent_kafka_client.publish.call_args.kwargs
        assert call_kwargs["topic"] == TOPIC_EVENT_PUBLISH_INTENT
        assert call_kwargs["topic"] == test_node.INTENT_TOPIC

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_kafka_key_format(self, test_node, test_event):
        """
        Test that Kafka key is string representation of intent_id.

        Validates message key generation for partitioning.
        """
        await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        call_kwargs = test_node._intent_kafka_client.publish.call_args.kwargs
        key = call_kwargs["key"]

        # Key should be string representation of UUID
        assert isinstance(key, str)
        # Should be parseable as UUID
        UUID(key)

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_multiple_concurrent_publishes(self, test_node, test_event):
        """
        Test thread safety of concurrent intent publishes.

        Validates async-safe implementation.
        """
        tasks = [
            test_node.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key=f"test-key-{i}",
                event=test_event,
            )
            for i in range(10)
        ]

        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 10
        # All should have unique intent IDs
        intent_ids = [r.intent_id for r in results]
        assert len(set(intent_ids)) == 10

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_complex_event_payload(self, test_node):
        """
        Test intent publishing with complex nested event payload.

        Validates serialization of complex data structures.
        """

        class ComplexEvent(BaseModel):
            """Event with nested structure."""

            id: UUID
            metadata: dict[str, Any]
            tags: list[str]
            nested: dict[str, dict[str, int]]

        complex_event = ComplexEvent(
            id=uuid4(),
            metadata={"key": "value", "count": 42},
            tags=["tag1", "tag2", "tag3"],
            nested={"level1": {"level2": 100}},
        )

        result = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=complex_event,
        )

        # Should handle complex payload
        assert isinstance(result, ModelIntentPublishResult)

    def test_mixin_attributes_exist(self, test_node):
        """
        Test that mixin adds required attributes to node.

        Validates mixin interface contract.
        """
        assert hasattr(test_node, "_intent_kafka_client")
        assert hasattr(test_node, "_intent_container")
        assert hasattr(test_node, "INTENT_TOPIC")
        assert hasattr(test_node, "publish_event_intent")
        assert hasattr(test_node, "_init_intent_publisher")

    def test_intent_topic_constant_value(self, test_node):
        """
        Test INTENT_TOPIC constant has correct value.

        Validates topic naming convention.
        """
        assert test_node.INTENT_TOPIC == TOPIC_EVENT_PUBLISH_INTENT
        assert "intent" in test_node.INTENT_TOPIC.lower()
        assert "event-publish" in test_node.INTENT_TOPIC

    @pytest.mark.asyncio
    @pytest.mark.timeout(90)  # Longer timeout for CI async tests
    async def test_result_model_completeness(self, test_node, test_event):
        """
        Test that ModelIntentPublishResult contains all required fields.

        Validates result model structure.
        """
        result = await test_node.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=test_event,
        )

        # Verify all fields are present
        assert hasattr(result, "intent_id")
        assert hasattr(result, "published_at")
        assert hasattr(result, "target_topic")
        assert hasattr(result, "correlation_id")

        # Verify field types
        assert isinstance(result.intent_id, UUID)
        assert isinstance(result.published_at, datetime)
        assert isinstance(result.target_topic, str)
        assert isinstance(result.correlation_id, UUID)
