"""
Integration tests for MixinIntentPublisher.

Tests the complete workflow of intent publishing to Kafka, including:
- End-to-end intent publishing and validation
- Intent consumption and execution workflow simulation
- Intent payload delivery to executor
- Correlation ID tracking through full workflow
- Error scenarios (Kafka unavailable, malformed intents)
- Integration with actual Node classes using the mixin

This test suite uses mocked Kafka client to avoid external dependencies
while maintaining realistic integration testing patterns.
"""

import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from pydantic import BaseModel, Field

from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.mixins.mixin_intent_publisher import MixinIntentPublisher
from omnibase_core.models.container.model_onex_container import ModelONEXContainer
from omnibase_core.models.events.model_intent_events import (
    TOPIC_EVENT_PUBLISH_INTENT,
    ModelEventPublishIntent,
    ModelIntentExecutionResult,
)
from omnibase_core.models.model_intent_publish_result import ModelIntentPublishResult

# ============================================================================
# Test Event Models
# ============================================================================


class TestMetricsEvent(BaseModel):
    """Sample domain event for testing."""

    metrics_id: UUID = Field(default_factory=uuid4)
    operation_name: str
    duration_ms: float
    success: bool
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TestTaskCompletedEvent(BaseModel):
    """Another sample domain event for testing."""

    task_id: UUID = Field(default_factory=uuid4)
    task_type: str
    result: dict[str, Any]
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ============================================================================
# Test Node Classes
# ============================================================================


class TestReducerWithIntentPublisher(MixinIntentPublisher):
    """Test reducer node that uses intent publishing."""

    def __init__(self, container: ModelONEXContainer):
        """Initialize test reducer."""
        self.container = container
        self._init_intent_publisher(container)

    async def execute_reduction(self, events: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Execute reduction logic and publish intent.

        This simulates a reducer that aggregates events and publishes
        an intent to emit a metrics event.
        """
        # Pure aggregation logic
        total_duration = sum(e.get("duration_ms", 0) for e in events)
        success_count = sum(1 for e in events if e.get("success", False))

        # Build metrics event
        metrics_event = TestMetricsEvent(
            operation_name="batch_processing",
            duration_ms=total_duration,
            success=success_count == len(events),
        )

        # Publish intent instead of direct Kafka publish
        result = await self.publish_event_intent(
            target_topic="dev.omninode.metrics.v1",
            target_key=str(metrics_event.metrics_id),
            event=metrics_event,
        )

        return {
            "total_duration": total_duration,
            "success_count": success_count,
            "intent_id": str(result.intent_id),
        }


class TestOrchestratorWithIntentPublisher(MixinIntentPublisher):
    """Test orchestrator node that uses intent publishing."""

    def __init__(self, container: ModelONEXContainer):
        """Initialize test orchestrator."""
        self.container = container
        self._init_intent_publisher(container)

    async def execute_workflow(
        self, workflow_id: UUID, correlation_id: UUID
    ) -> dict[str, Any]:
        """
        Execute workflow and publish completion intent.

        This simulates an orchestrator that coordinates workflow steps
        and publishes completion events via intents.
        """
        # Workflow execution logic
        workflow_result = {"steps_completed": 3, "total_steps": 3}

        # Build completion event
        completion_event = TestTaskCompletedEvent(
            task_id=workflow_id,
            task_type="workflow_execution",
            result=workflow_result,
        )

        # Publish intent with correlation tracking
        result = await self.publish_event_intent(
            target_topic="dev.omninode.tasks.completed.v1",
            target_key=str(workflow_id),
            event=completion_event,
            correlation_id=correlation_id,
            priority=8,  # High priority
        )

        return {
            "workflow_id": str(workflow_id),
            "intent_id": str(result.intent_id),
            "correlation_id": str(result.correlation_id),
        }


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntentPublisherIntegration:
    """Integration tests for intent publisher pattern."""

    @staticmethod
    def extract_intent_from_message(message_value: str) -> dict[str, Any]:
        """
        Extract intent from Kafka message, handling both wrapped and unwrapped formats.

        The mixin tries to wrap intents in ModelOnexEnvelopeV1, but falls back to raw JSON
        if the envelope class is not available.

        Args:
            message_value: JSON string from Kafka message

        Returns:
            Intent dictionary
        """
        data = json.loads(message_value)

        # Check if wrapped in ModelOnexEnvelopeV1
        if "payload" in data and "envelope_version" in data:
            return data["payload"]

        # Raw intent (fallback)
        return data

    @pytest.fixture
    def mock_kafka_client(self):
        """
        Create mock Kafka client with realistic behavior.

        Tracks all published messages for verification.
        """
        client = AsyncMock()
        client.published_messages = []

        async def mock_publish(topic: str, key: str, value: str):
            """Mock publish that records messages."""
            client.published_messages.append(
                {
                    "topic": topic,
                    "key": key,
                    "value": value,
                    "timestamp": datetime.now(UTC),
                }
            )

        client.publish = mock_publish
        return client

    @pytest.fixture
    def container_with_kafka(self, mock_kafka_client):
        """Create container with mocked Kafka client."""
        container = ModelONEXContainer()

        # Register kafka_client service
        original_get_service = container.get_service

        def mock_get_service(service_name: str):
            if service_name == "kafka_client":
                return mock_kafka_client
            return original_get_service(service_name)

        container.get_service = mock_get_service
        return container

    # ========================================================================
    # Basic Intent Publishing Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_basic_intent_publishing(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test basic intent publishing workflow."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        # Execute reduction that publishes intent
        events = [
            {"duration_ms": 100, "success": True},
            {"duration_ms": 200, "success": True},
        ]

        result = await reducer.execute_reduction(events)

        # Verify intent was published to Kafka
        assert len(mock_kafka_client.published_messages) == 1

        message = mock_kafka_client.published_messages[0]
        assert message["topic"] == TOPIC_EVENT_PUBLISH_INTENT

        # Extract intent from message (handles both wrapped and unwrapped)
        intent = self.extract_intent_from_message(message["value"])

        # Verify intent payload
        assert intent["target_topic"] == "dev.omninode.metrics.v1"
        assert intent["target_event_type"] == "TestMetricsEvent"
        assert intent["created_by"] == "TestReducerWithIntentPublisher"
        assert "target_event_payload" in intent

        # Verify result includes intent_id
        assert "intent_id" in result
        assert UUID(result["intent_id"])

    @pytest.mark.asyncio
    async def test_intent_publish_result_validation(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test that ModelIntentPublishResult is properly populated."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        # Create test event
        metrics_event = TestMetricsEvent(
            operation_name="test_operation", duration_ms=150.5, success=True
        )

        # Publish intent directly
        result = await reducer.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=metrics_event,
        )

        # Validate result model
        assert isinstance(result, ModelIntentPublishResult)
        assert isinstance(result.intent_id, UUID)
        assert isinstance(result.published_at, datetime)
        assert result.target_topic == "dev.omninode.test.v1"
        assert isinstance(result.correlation_id, UUID)

        # Verify result can be serialized
        result_dict = result.model_dump()
        assert "intent_id" in result_dict
        assert "published_at" in result_dict
        assert "target_topic" in result_dict
        assert "correlation_id" in result_dict

    # ========================================================================
    # Correlation ID Tracking Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_correlation_id_tracking_through_workflow(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test correlation ID preservation through entire workflow."""
        orchestrator = TestOrchestratorWithIntentPublisher(container_with_kafka)

        workflow_id = uuid4()
        correlation_id = uuid4()

        # Execute workflow with specific correlation ID
        result = await orchestrator.execute_workflow(workflow_id, correlation_id)

        # Verify correlation ID in result
        assert result["correlation_id"] == str(correlation_id)

        # Verify correlation ID in published intent
        message = mock_kafka_client.published_messages[0]
        intent = self.extract_intent_from_message(message["value"])

        assert intent["correlation_id"] == str(correlation_id)

    @pytest.mark.asyncio
    async def test_auto_generated_correlation_id(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test that correlation ID is auto-generated when not provided."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        metrics_event = TestMetricsEvent(
            operation_name="test", duration_ms=100, success=True
        )

        # Publish without explicit correlation_id
        result = await reducer.publish_event_intent(
            target_topic="dev.omninode.test.v1",
            target_key="test-key",
            event=metrics_event,
        )

        # Verify correlation_id was generated
        assert result.correlation_id is not None
        assert isinstance(result.correlation_id, UUID)

        # Verify same correlation_id in published message
        message = mock_kafka_client.published_messages[0]
        intent = self.extract_intent_from_message(message["value"])
        assert intent["correlation_id"] == str(result.correlation_id)

    @pytest.mark.asyncio
    async def test_correlation_id_propagates_to_executor(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test correlation ID propagation for intent executor tracing."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)
        correlation_id = uuid4()

        metrics_event = TestMetricsEvent(
            operation_name="traced_operation", duration_ms=200, success=True
        )

        result = await reducer.publish_event_intent(
            target_topic="dev.omninode.metrics.v1",
            target_key="trace-test",
            event=metrics_event,
            correlation_id=correlation_id,
        )

        # Verify correlation_id matches
        assert result.correlation_id == correlation_id

        # Parse published intent
        message = mock_kafka_client.published_messages[0]
        intent_payload = self.extract_intent_from_message(message["value"])

        # Verify executor would receive correlation_id
        assert intent_payload["correlation_id"] == str(correlation_id)

        # Simulate intent executor creating execution result
        execution_result = ModelIntentExecutionResult(
            intent_id=UUID(intent_payload["intent_id"]),
            correlation_id=correlation_id,
            success=True,
            execution_duration_ms=50.0,
        )

        # Verify correlation_id preserved in execution result
        assert execution_result.correlation_id == correlation_id

    # ========================================================================
    # Intent Payload Delivery Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_intent_payload_complete_delivery(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test that complete event payload is delivered in intent."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        # Create event with detailed payload
        metrics_event = TestMetricsEvent(
            metrics_id=uuid4(),
            operation_name="complex_operation",
            duration_ms=350.75,
            success=True,
        )

        await reducer.publish_event_intent(
            target_topic="dev.omninode.metrics.v1",
            target_key=str(metrics_event.metrics_id),
            event=metrics_event,
        )

        # Extract intent payload
        message = mock_kafka_client.published_messages[0]
        intent = self.extract_intent_from_message(message["value"])

        # Verify all event fields present in payload
        event_payload = intent["target_event_payload"]
        assert event_payload["metrics_id"] == str(metrics_event.metrics_id)
        assert event_payload["operation_name"] == "complex_operation"
        assert event_payload["duration_ms"] == 350.75
        assert event_payload["success"] is True
        assert "timestamp" in event_payload

    @pytest.mark.asyncio
    async def test_intent_metadata_fields(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test that intent includes all required metadata fields."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        metrics_event = TestMetricsEvent(
            operation_name="metadata_test", duration_ms=100, success=True
        )

        result = await reducer.publish_event_intent(
            target_topic="dev.omninode.metrics.v1",
            target_key="metadata-key",
            event=metrics_event,
            priority=7,
        )

        # Parse intent
        message = mock_kafka_client.published_messages[0]
        intent = self.extract_intent_from_message(message["value"])

        # Verify required metadata
        assert "intent_id" in intent
        assert "correlation_id" in intent
        assert "created_at" in intent
        assert intent["created_by"] == "TestReducerWithIntentPublisher"
        assert intent["target_topic"] == "dev.omninode.metrics.v1"
        assert intent["target_key"] == "metadata-key"
        assert intent["target_event_type"] == "TestMetricsEvent"
        assert intent["priority"] == 7

        # Verify intent_id matches result
        assert intent["intent_id"] == str(result.intent_id)

    # ========================================================================
    # Priority Handling Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_priority_handling(self, container_with_kafka, mock_kafka_client):
        """Test that priority is properly set and validated."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        event = TestMetricsEvent(
            operation_name="priority_test", duration_ms=100, success=True
        )

        # Test different priority levels
        for priority in [1, 5, 10]:
            await reducer.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key=f"priority-{priority}",
                event=event,
                priority=priority,
            )

        # Verify all priorities recorded correctly
        assert len(mock_kafka_client.published_messages) == 3

        for i, priority in enumerate([1, 5, 10]):
            message = mock_kafka_client.published_messages[i]
            intent = self.extract_intent_from_message(message["value"])
            assert intent["priority"] == priority

    @pytest.mark.asyncio
    async def test_invalid_priority_rejected(self, container_with_kafka):
        """Test that invalid priority values are rejected."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        event = TestMetricsEvent(operation_name="test", duration_ms=100, success=True)

        # Test priority < 1
        with pytest.raises(ModelOnexError, match="Priority must be 1-10"):
            await reducer.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test",
                event=event,
                priority=0,
            )

        # Test priority > 10
        with pytest.raises(ModelOnexError, match="Priority must be 1-10"):
            await reducer.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test",
                event=event,
                priority=11,
            )

    # ========================================================================
    # Error Scenario Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_kafka_unavailable_error(self, container_with_kafka):
        """Test handling when Kafka client is unavailable."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        # Make Kafka publish fail
        kafka_client = container_with_kafka.get_service("kafka_client")

        async def failing_publish(*args, **kwargs):
            raise ConnectionError("Kafka broker unavailable")

        kafka_client.publish = failing_publish

        event = TestMetricsEvent(operation_name="test", duration_ms=100, success=True)

        # Should propagate Kafka error
        with pytest.raises(ConnectionError, match="Kafka broker unavailable"):
            await reducer.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test",
                event=event,
            )

    @pytest.mark.asyncio
    async def test_malformed_event_rejected(self, container_with_kafka):
        """Test that non-Pydantic events are rejected."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        # Create object without model_dump method
        invalid_event = {"not": "a pydantic model"}

        with pytest.raises(
            ModelOnexError, match="Event must be a Pydantic model with model_dump"
        ):
            await reducer.publish_event_intent(
                target_topic="dev.omninode.test.v1",
                target_key="test",
                event=invalid_event,  # type: ignore
            )

    def test_kafka_client_missing_from_container(self):
        """Test error when kafka_client service is not registered."""
        container = ModelONEXContainer()

        # Mock get_service to return None for kafka_client
        # Note: We don't call original_get_service to avoid asyncio.run() in running event loop
        def mock_get_service(service_name):
            if service_name == "kafka_client":
                return None
            # Return None for any other service (this test only needs kafka_client)
            return None

        container.get_service = mock_get_service

        with pytest.raises(
            ModelOnexError, match="MixinIntentPublisher requires 'kafka_client' service"
        ):
            TestReducerWithIntentPublisher(container)

    # ========================================================================
    # Multi-Node Integration Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_multiple_nodes_share_kafka_client(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test that multiple nodes can share the same Kafka client."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)
        orchestrator = TestOrchestratorWithIntentPublisher(container_with_kafka)

        # Both nodes publish intents
        metrics_event = TestMetricsEvent(
            operation_name="shared_test", duration_ms=100, success=True
        )
        await reducer.publish_event_intent(
            target_topic="dev.omninode.metrics.v1",
            target_key="test",
            event=metrics_event,
        )

        task_event = TestTaskCompletedEvent(
            task_type="shared_test", result={"status": "ok"}
        )
        await orchestrator.publish_event_intent(
            target_topic="dev.omninode.tasks.v1",
            target_key="test",
            event=task_event,
        )

        # Verify both intents published
        assert len(mock_kafka_client.published_messages) == 2

        # Verify different source nodes
        intent1 = self.extract_intent_from_message(
            mock_kafka_client.published_messages[0]["value"]
        )
        intent2 = self.extract_intent_from_message(
            mock_kafka_client.published_messages[1]["value"]
        )

        assert intent1["created_by"] == "TestReducerWithIntentPublisher"
        assert intent2["created_by"] == "TestOrchestratorWithIntentPublisher"

    @pytest.mark.asyncio
    async def test_concurrent_intent_publishing(
        self, container_with_kafka, mock_kafka_client
    ):
        """Test concurrent intent publishing from multiple nodes."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        # Publish multiple intents concurrently
        events = [
            TestMetricsEvent(
                operation_name=f"concurrent_{i}", duration_ms=100 + i, success=True
            )
            for i in range(10)
        ]

        tasks = [
            reducer.publish_event_intent(
                target_topic="dev.omninode.metrics.v1",
                target_key=str(event.metrics_id),
                event=event,
            )
            for event in events
        ]

        results = await asyncio.gather(*tasks)

        # Verify all intents published
        assert len(results) == 10
        assert len(mock_kafka_client.published_messages) == 10

        # Verify all have unique intent_ids
        intent_ids = [r.intent_id for r in results]
        assert len(set(intent_ids)) == 10

    # ========================================================================
    # End-to-End Workflow Simulation
    # ========================================================================

    @pytest.mark.asyncio
    async def test_complete_workflow_simulation(
        self, container_with_kafka, mock_kafka_client
    ):
        """
        Test complete end-to-end workflow:
        1. Reducer publishes intent
        2. Simulate intent executor consuming intent
        3. Executor publishes execution result
        4. Validate correlation throughout
        """
        reducer = TestReducerWithIntentPublisher(container_with_kafka)
        correlation_id = uuid4()

        # Step 1: Reducer publishes intent
        metrics_event = TestMetricsEvent(
            operation_name="workflow_test", duration_ms=250, success=True
        )

        result = await reducer.publish_event_intent(
            target_topic="dev.omninode.metrics.v1",
            target_key="workflow-key",
            event=metrics_event,
            correlation_id=correlation_id,
        )

        # Step 2: Simulate intent executor consuming intent
        message = mock_kafka_client.published_messages[0]
        intent_data = self.extract_intent_from_message(message["value"])
        intent = ModelEventPublishIntent(**intent_data)

        # Verify executor receives complete intent
        assert intent.correlation_id == correlation_id
        assert intent.target_topic == "dev.omninode.metrics.v1"
        assert intent.target_key == "workflow-key"
        assert intent.target_event_type == "TestMetricsEvent"

        # Step 3: Simulate executor publishing to target topic
        # (In real system, executor would call Effect node)
        executor_message = {
            "topic": intent.target_topic,
            "key": intent.target_key,
            "payload": intent.target_event_payload,
            "correlation_id": str(intent.correlation_id),
        }

        # Step 4: Validate correlation preserved throughout
        assert executor_message["correlation_id"] == str(correlation_id)
        assert executor_message["payload"]["operation_name"] == "workflow_test"

        # Step 5: Simulate execution result
        execution_result = ModelIntentExecutionResult(
            intent_id=intent.intent_id,
            correlation_id=intent.correlation_id,
            success=True,
            execution_duration_ms=15.5,
        )

        assert execution_result.correlation_id == correlation_id
        assert execution_result.intent_id == result.intent_id

    @pytest.mark.asyncio
    async def test_intent_retry_scenario(self, container_with_kafka, mock_kafka_client):
        """Test intent publishing with retry configuration."""
        reducer = TestReducerWithIntentPublisher(container_with_kafka)

        event = TestMetricsEvent(
            operation_name="retry_test", duration_ms=100, success=False
        )

        # Publish intent (first attempt)
        result1 = await reducer.publish_event_intent(
            target_topic="dev.omninode.metrics.v1",
            target_key="retry-test",
            event=event,
            priority=8,  # High priority for retry
        )

        # Simulate executor detecting failure and retrying
        # (same correlation_id, different intent_id)
        result2 = await reducer.publish_event_intent(
            target_topic="dev.omninode.metrics.v1",
            target_key="retry-test",
            event=event,
            correlation_id=result1.correlation_id,  # Preserve correlation
            priority=9,  # Even higher priority
        )

        # Verify both intents share correlation but different intent_ids
        assert result1.correlation_id == result2.correlation_id
        assert result1.intent_id != result2.intent_id

        # Verify both published
        assert len(mock_kafka_client.published_messages) == 2

        intent1 = self.extract_intent_from_message(
            mock_kafka_client.published_messages[0]["value"]
        )
        intent2 = self.extract_intent_from_message(
            mock_kafka_client.published_messages[1]["value"]
        )

        assert intent1["priority"] == 8
        assert intent2["priority"] == 9
        assert intent1["correlation_id"] == intent2["correlation_id"]
