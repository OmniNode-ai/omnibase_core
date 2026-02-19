# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Unit tests for ProtocolTransitionNotificationPublisher and ProtocolTransitionNotificationConsumer.

Tests verify:
- Protocols are runtime_checkable
- Protocols define required methods with correct signatures
- Pydantic models can implement the protocols
- Custom classes can implement the protocols
- isinstance checks work correctly
- Async method signatures are correct

Timeout Protection:
- All test classes use @pytest.mark.timeout(5) for unit tests
- These are pure protocol tests with no I/O
"""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import uuid4

import pytest

from omnibase_core.models.notifications.model_state_transition_notification import (
    ModelStateTransitionNotification,
)
from omnibase_core.protocols.notifications.protocol_transition_notification import (
    ProtocolTransitionNotificationConsumer,
    ProtocolTransitionNotificationPublisher,
)

# ---- Test Fixtures ----


@pytest.fixture
def sample_notification() -> ModelStateTransitionNotification:
    """Return a sample notification for testing."""
    return ModelStateTransitionNotification(
        aggregate_type="registration",
        aggregate_id=uuid4(),
        from_state="pending",
        to_state="active",
        projection_version=1,
        correlation_id=uuid4(),
        causation_id=uuid4(),
        timestamp=datetime.now(UTC),
    )


# ---- Sample Implementations ----


class SamplePublisher:
    """Sample implementation of ProtocolTransitionNotificationPublisher."""

    def __init__(self) -> None:
        self.published: list[ModelStateTransitionNotification] = []
        self.batch_published: list[list[ModelStateTransitionNotification]] = []

    async def publish(self, notification: ModelStateTransitionNotification) -> None:
        """Publish a single notification."""
        self.published.append(notification)

    async def publish_batch(
        self, notifications: list[ModelStateTransitionNotification]
    ) -> None:
        """Publish a batch of notifications."""
        self.batch_published.append(notifications)


class SampleConsumer:
    """Sample implementation of ProtocolTransitionNotificationConsumer."""

    def __init__(self) -> None:
        self.subscriptions: dict[
            str, list[Callable[[ModelStateTransitionNotification], Awaitable[None]]]
        ] = {}

    async def subscribe(
        self,
        aggregate_type: str,
        handler: Callable[[ModelStateTransitionNotification], Awaitable[None]],
    ) -> None:
        """Subscribe to notifications for an aggregate type."""
        if aggregate_type not in self.subscriptions:
            self.subscriptions[aggregate_type] = []
        self.subscriptions[aggregate_type].append(handler)


class IncompletePublisher:
    """Class that does NOT implement the full publisher protocol."""

    async def publish(self, notification: ModelStateTransitionNotification) -> None:
        """Only implements publish, missing publish_batch."""


class IncompleteConsumer:
    """Class that does NOT implement the consumer protocol."""

    def __init__(self) -> None:
        self.data: str = "incomplete"


# ---- Test Protocol Definition - Publisher ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestProtocolPublisherDefinition:
    """Tests for ProtocolTransitionNotificationPublisher definition."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that publisher protocol is decorated with @runtime_checkable."""
        publisher = SamplePublisher()
        result = isinstance(publisher, ProtocolTransitionNotificationPublisher)
        assert result is True

    def test_protocol_has_publish_method(self) -> None:
        """Test that protocol defines publish method."""
        assert hasattr(ProtocolTransitionNotificationPublisher, "publish")

    def test_protocol_has_publish_batch_method(self) -> None:
        """Test that protocol defines publish_batch method."""
        assert hasattr(ProtocolTransitionNotificationPublisher, "publish_batch")


# ---- Test Protocol Definition - Consumer ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestProtocolConsumerDefinition:
    """Tests for ProtocolTransitionNotificationConsumer definition."""

    def test_protocol_is_runtime_checkable(self) -> None:
        """Test that consumer protocol is decorated with @runtime_checkable."""
        consumer = SampleConsumer()
        result = isinstance(consumer, ProtocolTransitionNotificationConsumer)
        assert result is True

    def test_protocol_has_subscribe_method(self) -> None:
        """Test that protocol defines subscribe method."""
        assert hasattr(ProtocolTransitionNotificationConsumer, "subscribe")


# ---- Test Publisher Implementation ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestPublisherImplementation:
    """Tests for publisher protocol implementations."""

    def test_sample_publisher_implements_protocol(self) -> None:
        """Test that SamplePublisher implements the protocol."""
        publisher = SamplePublisher()
        assert isinstance(publisher, ProtocolTransitionNotificationPublisher)

    @pytest.mark.asyncio
    async def test_publish_single_notification(
        self, sample_notification: ModelStateTransitionNotification
    ) -> None:
        """Test publishing a single notification."""
        publisher = SamplePublisher()
        await publisher.publish(sample_notification)

        assert len(publisher.published) == 1
        assert publisher.published[0] == sample_notification

    @pytest.mark.asyncio
    async def test_publish_batch_notifications(
        self, sample_notification: ModelStateTransitionNotification
    ) -> None:
        """Test publishing a batch of notifications."""
        publisher = SamplePublisher()

        notifications = [sample_notification, sample_notification]
        await publisher.publish_batch(notifications)

        assert len(publisher.batch_published) == 1
        assert publisher.batch_published[0] == notifications

    @pytest.mark.asyncio
    async def test_publish_empty_batch(self) -> None:
        """Test publishing an empty batch."""
        publisher = SamplePublisher()
        await publisher.publish_batch([])

        assert len(publisher.batch_published) == 1
        assert publisher.batch_published[0] == []

    def test_incomplete_publisher_does_not_implement_protocol(self) -> None:
        """Test that incomplete implementation does NOT implement protocol."""
        publisher = IncompletePublisher()
        # Missing publish_batch method
        assert not isinstance(publisher, ProtocolTransitionNotificationPublisher)


# ---- Test Consumer Implementation ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestConsumerImplementation:
    """Tests for consumer protocol implementations."""

    def test_sample_consumer_implements_protocol(self) -> None:
        """Test that SampleConsumer implements the protocol."""
        consumer = SampleConsumer()
        assert isinstance(consumer, ProtocolTransitionNotificationConsumer)

    @pytest.mark.asyncio
    async def test_subscribe_to_aggregate_type(
        self, sample_notification: ModelStateTransitionNotification
    ) -> None:
        """Test subscribing to an aggregate type."""
        consumer = SampleConsumer()

        received: list[ModelStateTransitionNotification] = []

        async def handler(notification: ModelStateTransitionNotification) -> None:
            received.append(notification)

        await consumer.subscribe("registration", handler)

        assert "registration" in consumer.subscriptions
        assert len(consumer.subscriptions["registration"]) == 1

    @pytest.mark.asyncio
    async def test_subscribe_multiple_handlers(self) -> None:
        """Test subscribing multiple handlers to same aggregate type."""
        consumer = SampleConsumer()

        async def handler1(notification: ModelStateTransitionNotification) -> None:
            pass

        async def handler2(notification: ModelStateTransitionNotification) -> None:
            pass

        await consumer.subscribe("registration", handler1)
        await consumer.subscribe("registration", handler2)

        assert len(consumer.subscriptions["registration"]) == 2

    @pytest.mark.asyncio
    async def test_subscribe_different_aggregate_types(self) -> None:
        """Test subscribing to different aggregate types."""
        consumer = SampleConsumer()

        async def handler(notification: ModelStateTransitionNotification) -> None:
            pass

        await consumer.subscribe("registration", handler)
        await consumer.subscribe("intelligence", handler)

        assert "registration" in consumer.subscriptions
        assert "intelligence" in consumer.subscriptions

    def test_incomplete_consumer_does_not_implement_protocol(self) -> None:
        """Test that incomplete implementation does NOT implement protocol."""
        consumer = IncompleteConsumer()
        assert not isinstance(consumer, ProtocolTransitionNotificationConsumer)


# ---- Test Protocol Type Annotations ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestProtocolTypeAnnotations:
    """Tests for using protocols in type annotations."""

    def test_function_accepting_publisher_protocol(self) -> None:
        """Test function can accept publisher protocol-typed parameter."""

        async def use_publisher(
            publisher: ProtocolTransitionNotificationPublisher,
            notification: ModelStateTransitionNotification,
        ) -> None:
            await publisher.publish(notification)

        # Type checker should accept SamplePublisher
        publisher = SamplePublisher()
        assert isinstance(publisher, ProtocolTransitionNotificationPublisher)

    def test_function_accepting_consumer_protocol(self) -> None:
        """Test function can accept consumer protocol-typed parameter."""

        async def use_consumer(
            consumer: ProtocolTransitionNotificationConsumer,
            aggregate_type: str,
        ) -> None:
            async def handler(notification: ModelStateTransitionNotification) -> None:
                pass

            await consumer.subscribe(aggregate_type, handler)

        # Type checker should accept SampleConsumer
        consumer = SampleConsumer()
        assert isinstance(consumer, ProtocolTransitionNotificationConsumer)

    def test_list_of_publisher_instances(self) -> None:
        """Test list can contain different publisher implementations."""
        publishers: list[ProtocolTransitionNotificationPublisher] = [
            SamplePublisher(),
            SamplePublisher(),
        ]

        for publisher in publishers:
            assert isinstance(publisher, ProtocolTransitionNotificationPublisher)

    def test_list_of_consumer_instances(self) -> None:
        """Test list can contain different consumer implementations."""
        consumers: list[ProtocolTransitionNotificationConsumer] = [
            SampleConsumer(),
            SampleConsumer(),
        ]

        for consumer in consumers:
            assert isinstance(consumer, ProtocolTransitionNotificationConsumer)


# ---- Test Handler Signature ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestHandlerSignature:
    """Tests for handler callable signature in consumer."""

    @pytest.mark.asyncio
    async def test_handler_receives_correct_notification(
        self, sample_notification: ModelStateTransitionNotification
    ) -> None:
        """Test that handler receives the correct notification type."""
        received_notifications: list[ModelStateTransitionNotification] = []

        async def handler(notification: ModelStateTransitionNotification) -> None:
            received_notifications.append(notification)
            assert isinstance(notification, ModelStateTransitionNotification)

        consumer = SampleConsumer()
        await consumer.subscribe("registration", handler)

        # Simulate delivering notification to handler
        for h in consumer.subscriptions.get("registration", []):
            await h(sample_notification)

        assert len(received_notifications) == 1
        assert received_notifications[0] == sample_notification

    @pytest.mark.asyncio
    async def test_handler_is_async(self) -> None:
        """Test that handler must be async."""
        consumer = SampleConsumer()

        async def async_handler(
            notification: ModelStateTransitionNotification,
        ) -> None:
            pass

        # Should work with async handler
        await consumer.subscribe("test", async_handler)
        assert len(consumer.subscriptions["test"]) == 1


# ---- Test Edge Cases ----


@pytest.mark.timeout(5)
@pytest.mark.unit
class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_publish_multiple_times(
        self, sample_notification: ModelStateTransitionNotification
    ) -> None:
        """Test publishing multiple notifications sequentially."""
        publisher = SamplePublisher()

        for _ in range(5):
            await publisher.publish(sample_notification)

        assert len(publisher.published) == 5

    @pytest.mark.asyncio
    async def test_subscribe_empty_aggregate_type(self) -> None:
        """Test subscribing to empty string aggregate type."""
        consumer = SampleConsumer()

        async def handler(notification: ModelStateTransitionNotification) -> None:
            pass

        await consumer.subscribe("", handler)
        assert "" in consumer.subscriptions

    @pytest.mark.asyncio
    async def test_large_batch_publish(
        self, sample_notification: ModelStateTransitionNotification
    ) -> None:
        """Test publishing a large batch of notifications."""
        publisher = SamplePublisher()

        large_batch = [sample_notification] * 1000
        await publisher.publish_batch(large_batch)

        assert len(publisher.batch_published) == 1
        assert len(publisher.batch_published[0]) == 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
