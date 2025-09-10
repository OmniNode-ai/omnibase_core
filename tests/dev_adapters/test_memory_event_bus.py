"""
Comprehensive test harness for InMemoryEventBus.

⚠️  DEV/TEST ONLY - Tests for development event bus ⚠️
"""

import asyncio
from datetime import datetime
from uuid import uuid4

import pytest

from omnibase_core.dev_adapters.memory_event_bus import (
    InMemoryEventBus,
    get_dev_event_bus,
)
from omnibase_core.model.core.model_onex_event import OnexEvent


class TestInMemoryEventBus:
    """Test suite for InMemoryEventBus development adapter."""

    def setup_method(self):
        """Setup fresh event bus for each test."""
        self.event_bus = InMemoryEventBus()
        self.test_events = []
        self.callback_events = []

    def create_test_event(
        self,
        event_type: str = "test.event",
        node_id: str = "test-node",
        data: dict | None = None,
    ) -> OnexEvent:
        """Create a test event."""
        if data is None:
            data = {"test": "data"}

        event = OnexEvent(
            event_type=event_type, node_id=node_id, data=data, correlation_id=uuid4()
        )
        self.test_events.append(event)
        return event

    def sync_callback(self, event: OnexEvent) -> None:
        """Synchronous test callback."""
        self.callback_events.append(("sync", event))

    async def async_callback(self, event: OnexEvent) -> None:
        """Asynchronous test callback."""
        self.callback_events.append(("async", event))

    # === Basic Functionality Tests ===

    def test_initialization(self):
        """Test event bus initialization."""
        assert self.event_bus is not None
        assert self.event_bus.get_subscriber_count() == 0
        assert len(self.event_bus.get_event_history()) == 0

    def test_synchronous_publish_subscribe(self):
        """Test synchronous publish/subscribe functionality."""
        # Subscribe to events
        self.event_bus.subscribe(self.sync_callback)
        assert self.event_bus.get_subscriber_count() == 1

        # Publish event
        event = self.create_test_event()
        self.event_bus.publish(event)

        # Verify callback was called
        assert len(self.callback_events) == 1
        assert self.callback_events[0][0] == "sync"
        assert self.callback_events[0][1] == event

        # Verify event history
        history = self.event_bus.get_event_history()
        assert len(history) == 1
        assert history[0] == event

    @pytest.mark.asyncio
    async def test_asynchronous_publish_subscribe(self):
        """Test asynchronous publish/subscribe functionality."""
        # Subscribe to events
        await self.event_bus.subscribe_async(self.async_callback)
        assert self.event_bus.get_subscriber_count() == 1

        # Publish event
        event = self.create_test_event()
        await self.event_bus.publish_async(event)

        # Verify callback was called
        assert len(self.callback_events) == 1
        assert self.callback_events[0][0] == "async"
        assert self.callback_events[0][1] == event

    def test_unsubscribe(self):
        """Test unsubscribe functionality."""
        # Subscribe and verify
        self.event_bus.subscribe(self.sync_callback)
        assert self.event_bus.get_subscriber_count() == 1

        # Unsubscribe and verify
        self.event_bus.unsubscribe(self.sync_callback)
        assert self.event_bus.get_subscriber_count() == 0

        # Publish event - should not trigger callback
        event = self.create_test_event()
        self.event_bus.publish(event)
        assert len(self.callback_events) == 0

    @pytest.mark.asyncio
    async def test_async_unsubscribe(self):
        """Test async unsubscribe functionality."""
        # Subscribe and verify
        await self.event_bus.subscribe_async(self.async_callback)
        assert self.event_bus.get_subscriber_count() == 1

        # Unsubscribe and verify
        await self.event_bus.unsubscribe_async(self.async_callback)
        assert self.event_bus.get_subscriber_count() == 0

    # === Workflow Partition Tests ===

    def test_workflow_partitioning(self):
        """Test workflow isolation via partitioned queues."""
        partition_events = []

        def partition_callback(event: OnexEvent) -> None:
            partition_events.append(event)

        # Subscribe to specific partition
        partition_id = "workflow_test-123"
        self.event_bus.subscribe_to_partition(partition_id, partition_callback)

        # Create events for different workflows
        event1 = self.create_test_event(data={"workflow_instance_id": "test-123"})
        event2 = self.create_test_event(data={"workflow_instance_id": "other-456"})
        event3 = self.create_test_event(data={"workflow_instance_id": "test-123"})

        # Publish events
        self.event_bus.publish(event1)  # Should trigger partition callback
        self.event_bus.publish(event2)  # Should not trigger partition callback
        self.event_bus.publish(event3)  # Should trigger partition callback

        # Verify partition isolation
        assert len(partition_events) == 2
        assert partition_events[0] == event1
        assert partition_events[1] == event3

    def test_partition_event_history(self):
        """Test per-partition event history."""
        # Create events for different partitions
        event1 = self.create_test_event(data={"workflow_instance_id": "test-123"})
        event2 = self.create_test_event(data={"workflow_instance_id": "test-456"})
        event3 = self.create_test_event(data={"workflow_instance_id": "test-123"})

        # Publish events
        self.event_bus.publish(event1)
        self.event_bus.publish(event2)
        self.event_bus.publish(event3)

        # Check partition-specific history
        partition1_history = self.event_bus.get_partition_event_history(
            "workflow_test-123"
        )
        partition2_history = self.event_bus.get_partition_event_history(
            "workflow_test-456"
        )

        assert len(partition1_history) == 2
        assert len(partition2_history) == 1
        assert partition1_history[0] == event1
        assert partition1_history[1] == event3
        assert partition2_history[0] == event2

    def test_partition_management(self):
        """Test partition management operations."""
        # Create partition with events
        event = self.create_test_event(data={"workflow_instance_id": "test-123"})
        self.event_bus.publish(event)

        partition_id = "workflow_test-123"

        # Verify partition exists
        partition_ids = self.event_bus.get_partition_ids()
        assert partition_id in partition_ids

        # Clear partition
        self.event_bus.clear_partition(partition_id)
        history = self.event_bus.get_partition_event_history(partition_id)
        assert len(history) == 0

        # Remove partition
        self.event_bus.remove_partition(partition_id)
        partition_ids = self.event_bus.get_partition_ids()
        assert partition_id not in partition_ids

    # === Error Handling Tests ===

    def test_callback_error_handling(self):
        """Test error handling in event callbacks."""
        error_count = 0

        def failing_callback(event: OnexEvent) -> None:
            nonlocal error_count
            error_count += 1
            raise ValueError("Test error")

        def working_callback(event: OnexEvent) -> None:
            self.callback_events.append(("working", event))

        # Subscribe both callbacks
        self.event_bus.subscribe(failing_callback)
        self.event_bus.subscribe(working_callback)

        # Publish event
        event = self.create_test_event()
        self.event_bus.publish(event)

        # Verify error didn't prevent other callbacks
        assert error_count == 1
        assert len(self.callback_events) == 1
        assert self.callback_events[0][0] == "working"

    @pytest.mark.asyncio
    async def test_async_callback_error_handling(self):
        """Test error handling in async callbacks."""
        error_count = 0

        async def failing_async_callback(event: OnexEvent) -> None:
            nonlocal error_count
            error_count += 1
            raise ValueError("Async test error")

        async def working_async_callback(event: OnexEvent) -> None:
            self.callback_events.append(("async_working", event))

        # Subscribe both callbacks
        await self.event_bus.subscribe_async(failing_async_callback)
        await self.event_bus.subscribe_async(working_async_callback)

        # Publish event
        event = self.create_test_event()
        await self.event_bus.publish_async(event)

        # Verify error didn't prevent other callbacks
        assert error_count == 1
        assert len(self.callback_events) == 1
        assert self.callback_events[0][0] == "async_working"

    # === Performance and Limits Tests ===

    def test_partition_overflow(self):
        """Test partition overflow handling."""
        # Create event bus with low partition limit
        event_bus = InMemoryEventBus(max_partitions=3)

        # Create events that will create more partitions than limit
        for i in range(5):
            event = OnexEvent(
                event_type="test.event",
                node_id=f"node-{i}",
                data={"workflow_instance_id": f"test-{i}"},
            )
            event_bus.publish(event)

        # Should have maximum partitions
        partition_ids = event_bus.get_partition_ids()
        assert len(partition_ids) <= 3

    def test_event_history_limits(self):
        """Test event history size limits."""
        # Create partition and fill with events beyond limit
        partition_id = "workflow_test-123"
        for i in range(1005):  # More than default 1000 limit
            event = OnexEvent(
                event_type="test.event",
                node_id="test-node",
                data={"workflow_instance_id": "test-123", "sequence": i},
            )
            self.event_bus.publish(event)

        # Check history is limited
        history = self.event_bus.get_partition_event_history(partition_id)
        assert len(history) <= 1000

    # === Statistics and Monitoring Tests ===

    def test_statistics(self):
        """Test event bus statistics."""
        # Create events in multiple partitions
        for i in range(3):
            for j in range(2):
                event = OnexEvent(
                    event_type="test.event",
                    node_id=f"node-{i}",
                    data={"workflow_instance_id": f"test-{i}"},
                )
                self.event_bus.publish(event)

        # Add subscribers
        self.event_bus.subscribe(self.sync_callback)
        self.event_bus.subscribe_to_partition("workflow_test-0", self.sync_callback)

        # Get statistics
        stats = self.event_bus.get_stats()

        assert stats.total_events_published == 6
        assert stats.total_partitions == 3
        assert stats.total_sync_subscribers >= 2
        assert len(stats.partition_details) == 3

    # === Cleanup and Resource Management Tests ===

    def test_clear_functionality(self):
        """Test clearing all subscribers."""
        # Add subscribers
        self.event_bus.subscribe(self.sync_callback)
        self.event_bus.subscribe_to_partition("test-partition", self.sync_callback)

        # Clear all
        self.event_bus.clear()

        # Verify all cleared
        assert self.event_bus.get_subscriber_count() == 0

    def test_event_history_management(self):
        """Test event history management."""
        # Publish events
        for i in range(5):
            event = self.create_test_event(data={"sequence": i})
            self.event_bus.publish(event)

        assert len(self.event_bus.get_event_history()) == 5

        # Clear history
        self.event_bus.clear_event_history()
        assert len(self.event_bus.get_event_history()) == 0

    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test graceful shutdown."""
        # Setup event bus with subscribers and events
        await self.event_bus.subscribe_async(self.async_callback)
        event = self.create_test_event()
        await self.event_bus.publish_async(event)

        # Shutdown
        await self.event_bus.shutdown()

        # Verify cleanup
        assert self.event_bus.get_subscriber_count() == 0
        assert len(self.event_bus.get_event_history()) == 0

    # === Testing Utilities Tests ===

    def test_reset_for_testing(self):
        """Test testing utility functions."""
        # Setup state
        self.event_bus.subscribe(self.sync_callback)
        event = self.create_test_event()
        self.event_bus.publish(event)

        assert self.event_bus.get_subscriber_count() > 0
        assert len(self.event_bus.get_event_history()) > 0

        # Reset
        self.event_bus.reset_for_testing()

        # Verify clean state
        assert self.event_bus.get_subscriber_count() == 0
        assert len(self.event_bus.get_event_history()) == 0
        assert len(self.event_bus.get_partition_ids()) == 0

    def test_simulate_partition_overflow(self):
        """Test partition overflow simulation."""
        original_partition_count = len(self.event_bus.get_partition_ids())

        # Simulate overflow
        self.event_bus.simulate_partition_overflow()

        # Should create partitions
        new_partition_count = len(self.event_bus.get_partition_ids())
        assert new_partition_count > original_partition_count

    # === Integration Tests ===

    @pytest.mark.asyncio
    async def test_mixed_sync_async_usage(self):
        """Test mixed synchronous and asynchronous usage."""
        # Subscribe both sync and async
        self.event_bus.subscribe(self.sync_callback)
        await self.event_bus.subscribe_async(self.async_callback)

        # Publish sync
        event1 = self.create_test_event(event_type="sync.event")
        self.event_bus.publish(event1)

        # Publish async
        event2 = self.create_test_event(event_type="async.event")
        await self.event_bus.publish_async(event2)

        # Both callbacks should have been called for both events
        sync_events = [e[1] for e in self.callback_events if e[0] == "sync"]
        async_events = [e[1] for e in self.callback_events if e[0] == "async"]

        # Sync publish only triggers sync callbacks
        assert len(sync_events) == 1
        assert sync_events[0] == event1

        # Async publish only triggers async callbacks
        assert len(async_events) == 1
        assert async_events[0] == event2

    def test_concurrent_partitions(self):
        """Test concurrent operations across multiple partitions."""
        partition_callbacks = {}

        # Create callbacks for different partitions
        for i in range(3):
            partition_id = f"workflow_test-{i}"
            partition_callbacks[partition_id] = []

            def make_callback(pid):
                def callback(event: OnexEvent):
                    partition_callbacks[pid].append(event)

                return callback

            self.event_bus.subscribe_to_partition(
                partition_id, make_callback(partition_id)
            )

        # Publish events to different partitions
        events = []
        for i in range(3):
            for j in range(2):
                event = OnexEvent(
                    event_type="test.concurrent",
                    node_id=f"node-{i}-{j}",
                    data={"workflow_instance_id": f"test-{i}"},
                )
                events.append(event)
                self.event_bus.publish(event)

        # Verify partition isolation
        for i, (partition_id, callback_events) in enumerate(
            partition_callbacks.items()
        ):
            assert len(callback_events) == 2
            for event in callback_events:
                assert event.data["workflow_instance_id"] == f"test-{i}"


class TestGlobalEventBusInstance:
    """Test global event bus instance management."""

    def test_global_instance_creation(self):
        """Test global event bus instance creation."""
        bus1 = get_dev_event_bus()
        bus2 = get_dev_event_bus()

        # Should return same instance
        assert bus1 is bus2
        assert isinstance(bus1, InMemoryEventBus)

    def test_global_instance_functionality(self):
        """Test global instance functionality."""
        bus = get_dev_event_bus()

        # Reset to clean state
        bus.reset_for_testing()

        # Test basic functionality
        callback_events = []

        def test_callback(event: OnexEvent) -> None:
            callback_events.append(event)

        bus.subscribe(test_callback)

        event = OnexEvent(
            event_type="test.global", node_id="global-test", data={"test": "global"}
        )

        bus.publish(event)

        assert len(callback_events) == 1
        assert callback_events[0] == event


# === Golden Event Replay Tests ===


class TestGoldenEventReplay:
    """Test golden event replay functionality for deterministic testing."""

    def setup_method(self):
        """Setup for replay testing."""
        self.event_bus = InMemoryEventBus()
        self.replayed_events = []

    def create_golden_events(self) -> list[OnexEvent]:
        """Create a set of golden events for replay testing."""
        golden_events = []

        # Create deterministic event sequence
        base_time = datetime(2025, 1, 1, 12, 0, 0)
        for i in range(5):
            event = OnexEvent(
                event_type=f"golden.event.{i}",
                node_id=f"golden-node-{i}",
                data={
                    "sequence": i,
                    "timestamp": (base_time.timestamp() + i * 60),  # 1 minute intervals
                    "workflow_instance_id": f"golden-workflow-{i % 2}",
                },
            )
            golden_events.append(event)

        return golden_events

    def test_deterministic_replay(self):
        """Test deterministic event replay."""
        # Create golden events
        golden_events = self.create_golden_events()

        # Setup replay callback
        def replay_callback(event: OnexEvent) -> None:
            self.replayed_events.append(event)

        self.event_bus.subscribe(replay_callback)

        # Replay events
        for event in golden_events:
            self.event_bus.publish(event)

        # Verify deterministic replay
        assert len(self.replayed_events) == len(golden_events)
        for i, (original, replayed) in enumerate(
            zip(golden_events, self.replayed_events)
        ):
            assert replayed.event_type == original.event_type
            assert replayed.node_id == original.node_id
            assert replayed.data["sequence"] == i

    def test_partition_replay_isolation(self):
        """Test replay isolation across partitions."""
        golden_events = self.create_golden_events()

        # Setup partition-specific callbacks
        partition_0_events = []
        partition_1_events = []

        def partition_0_callback(event: OnexEvent) -> None:
            partition_0_events.append(event)

        def partition_1_callback(event: OnexEvent) -> None:
            partition_1_events.append(event)

        # Subscribe to specific partitions
        self.event_bus.subscribe_to_partition(
            "workflow_golden-workflow-0", partition_0_callback
        )
        self.event_bus.subscribe_to_partition(
            "workflow_golden-workflow-1", partition_1_callback
        )

        # Replay events
        for event in golden_events:
            self.event_bus.publish(event)

        # Verify partition isolation during replay
        # Events 0, 2, 4 go to partition 0 (even indices)
        # Events 1, 3 go to partition 1 (odd indices)
        assert len(partition_0_events) == 3
        assert len(partition_1_events) == 2

        for event in partition_0_events:
            assert event.data["sequence"] % 2 == 0

        for event in partition_1_events:
            assert event.data["sequence"] % 2 == 1
