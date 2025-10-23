"""
Test fixtures for intent publisher testing.

This module provides fast test fixtures for testing nodes using MixinIntentPublisher.
Uses Pydantic bypass patterns for performance (test-only, see fixtures/README.md).

Fixtures:
    - IntentPublisherFixtures: Intent event models
    - IntentResultFixtures: Intent execution results
    - MockKafkaClient: Test double for Kafka client

Usage:
    from tests.fixtures.fixture_intent_publisher import IntentPublisherFixtures

    def test_intent_publishing():
        intent = IntentPublisherFixtures.event_publish_intent(
            target_topic="my.topic.v1",
            target_key="test-key"
        )
        assert intent.target_topic == "my.topic.v1"
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel

from omnibase_core.models.events.model_intent_events import (
    ModelEventPublishIntent,
    ModelIntentExecutionResult,
)
from omnibase_core.models.model_intent_publish_result import ModelIntentPublishResult
from tests.fixtures.fixture_base import TestFixtureBase


class IntentPublisherFixtures(TestFixtureBase):
    """Fast test fixtures for intent publisher models."""

    @staticmethod
    def event_publish_intent(
        correlation_id: UUID | None = None,
        created_by: str = "test_node",
        target_topic: str = "dev.test.events.v1",
        target_key: str = "test-key",
        target_event_type: str = "TEST_EVENT",
        target_event_payload: dict[str, Any] | None = None,
        priority: int = 5,
        **overrides,
    ) -> ModelEventPublishIntent:
        """
        Create a test event publish intent.

        Args:
            correlation_id: Correlation ID (auto-generated if not provided)
            created_by: Service/node that created intent
            target_topic: Target Kafka topic
            target_key: Target Kafka key
            target_event_type: Event type name
            target_event_payload: Event payload dict
            priority: Intent priority (1-10)
            **overrides: Additional field overrides

        Returns:
            ModelEventPublishIntent instance
        """
        return TestFixtureBase.construct(
            ModelEventPublishIntent,
            intent_id=uuid4(),
            correlation_id=correlation_id or uuid4(),
            created_at=datetime.now(UTC),
            created_by=created_by,
            target_topic=target_topic,
            target_key=target_key,
            target_event_type=target_event_type,
            target_event_payload=target_event_payload or {"test": "data"},
            priority=priority,
            retry_policy=None,
            **overrides,
        )

    @staticmethod
    def intent_execution_result(
        intent_id: UUID | None = None,
        correlation_id: UUID | None = None,
        success: bool = True,
        error_message: str | None = None,
        execution_duration_ms: float = 10.5,
        **overrides,
    ) -> ModelIntentExecutionResult:
        """
        Create a test intent execution result.

        Args:
            intent_id: Intent ID (auto-generated if not provided)
            correlation_id: Correlation ID (auto-generated if not provided)
            success: Whether execution succeeded
            error_message: Error message if failed
            execution_duration_ms: Execution duration
            **overrides: Additional field overrides

        Returns:
            ModelIntentExecutionResult instance
        """
        return TestFixtureBase.construct(
            ModelIntentExecutionResult,
            intent_id=intent_id or uuid4(),
            correlation_id=correlation_id or uuid4(),
            executed_at=datetime.now(UTC),
            success=success,
            error_message=error_message,
            execution_duration_ms=execution_duration_ms,
            **overrides,
        )


class IntentResultFixtures(TestFixtureBase):
    """Fast test fixtures for intent publish results."""

    @staticmethod
    def success(
        intent_id: UUID | None = None,
        correlation_id: UUID | None = None,
        target_topic: str = "dev.test.events.v1",
        **overrides,
    ) -> ModelIntentPublishResult:
        """
        Create a successful intent publish result.

        Args:
            intent_id: Intent ID (auto-generated if not provided)
            correlation_id: Correlation ID (auto-generated if not provided)
            target_topic: Target Kafka topic
            **overrides: Additional field overrides

        Returns:
            ModelIntentPublishResult instance
        """
        return TestFixtureBase.construct(
            ModelIntentPublishResult,
            intent_id=intent_id or uuid4(),
            published_at=datetime.now(UTC),
            target_topic=target_topic,
            correlation_id=correlation_id or uuid4(),
            **overrides,
        )


class MockKafkaClient:
    """
    Mock Kafka client for testing intent publishing.

    This mock captures published intents for assertion in tests
    without requiring a real Kafka instance.

    Usage:
        mock_kafka = MockKafkaClient()
        container = create_container(kafka_client=mock_kafka)
        node = MyNode(container)

        await node.publish_event_intent(...)

        # Assert on captured intents
        assert len(mock_kafka.published_messages) == 1
        assert mock_kafka.published_messages[0]["topic"] == "intent.topic.v1"
    """

    def __init__(self):
        """Initialize mock Kafka client with empty message store."""
        self.published_messages: list[dict[str, Any]] = []
        self.publish_error: Exception | None = None

    async def publish(self, topic: str, key: str, value: str) -> None:
        """
        Mock publish method that captures messages.

        Args:
            topic: Kafka topic
            key: Message key
            value: Message value (JSON string)

        Raises:
            Exception: If publish_error is set (for testing error handling)
        """
        if self.publish_error:
            raise self.publish_error

        self.published_messages.append(
            {
                "topic": topic,
                "key": key,
                "value": value,
            }
        )

    def reset(self) -> None:
        """Reset captured messages (useful between tests)."""
        self.published_messages = []
        self.publish_error = None

    def get_messages_for_topic(self, topic: str) -> list[dict[str, Any]]:
        """
        Get all messages published to a specific topic.

        Args:
            topic: Kafka topic to filter by

        Returns:
            List of messages published to topic
        """
        return [msg for msg in self.published_messages if msg["topic"] == topic]

    def get_message_count(self, topic: str | None = None) -> int:
        """
        Get count of published messages, optionally filtered by topic.

        Args:
            topic: Optional topic to filter by

        Returns:
            Count of messages
        """
        if topic is None:
            return len(self.published_messages)
        return len(self.get_messages_for_topic(topic))

    def set_publish_error(self, error: Exception) -> None:
        """
        Set an error to be raised on next publish (for testing error handling).

        Args:
            error: Exception to raise
        """
        self.publish_error = error


# Convenience functions for test setup
def create_mock_kafka_client() -> MockKafkaClient:
    """Create a new mock Kafka client for testing."""
    return MockKafkaClient()


def create_test_event(event_type: str = "TEST_EVENT", **data) -> BaseModel:
    """
    Create a simple test event model.

    Args:
        event_type: Event type name
        **data: Event data fields

    Returns:
        Pydantic model instance
    """

    class TestEvent(BaseModel):
        """Simple test event model."""

        event_type: str
        data: dict[str, Any]

    return TestEvent(event_type=event_type, data=data)
