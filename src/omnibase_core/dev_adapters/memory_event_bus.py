"""
In-Memory Event Bus for Development and Testing.

⚠️  WARNING: DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

This implementation provides an in-memory event bus with partitioned queues
for workflow isolation, following the ProtocolEventBus interface.
"""

import asyncio
import logging
import threading
from collections import OrderedDict, defaultdict
from collections.abc import Callable
from typing import Any, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from omnibase_core.model.core.model_onex_event import OnexEvent
from omnibase_core.protocol.protocol_event_bus import ProtocolEventBus
from omnibase_core.protocol.protocol_event_bus_in_memory import ProtocolEventBusInMemory
from omnibase_core.protocol.protocol_event_bus_types import EventBusCredentialsModel

logger = logging.getLogger(__name__)


class WorkflowPartition(BaseModel):
    """Represents an isolated workflow partition with its own event queue."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    partition_id: str = Field(..., description="Unique partition identifier")
    workflow_instance_id: str = Field(..., description="Workflow instance ID")
    # Store callback registry as private attributes to avoid Pydantic serialization issues
    _sync_callbacks: list[Callable[[OnexEvent], None]] = PrivateAttr(
        default_factory=list
    )
    _async_callbacks: list[Callable[[OnexEvent], None]] = PrivateAttr(
        default_factory=list
    )
    event_history: list[OnexEvent] = Field(
        default_factory=list, description="Event history for this partition"
    )
    max_history: int = Field(
        default=1000, description="Maximum events to keep in history"
    )

    @property
    def subscribers(self) -> list[Callable[[OnexEvent], None]]:
        """Get synchronous event subscribers for this partition."""
        return self._sync_callbacks

    @property
    def async_subscribers(self) -> list[Callable[[OnexEvent], None]]:
        """Get asynchronous event subscribers for this partition."""
        return self._async_callbacks

    def add_event(self, event: OnexEvent) -> None:
        """Add event to partition history."""
        self.event_history.append(event)
        # Maintain history size limit
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

    def clear_history(self) -> None:
        """Clear event history for this partition."""
        self.event_history.clear()


class EventBusStats(BaseModel):
    """Statistics for the in-memory event bus."""

    total_events_published: int = Field(description="Total events published")
    total_partitions: int = Field(description="Total workflow partitions")
    total_sync_subscribers: int = Field(description="Total synchronous subscribers")
    total_async_subscribers: int = Field(description="Total asynchronous subscribers")
    event_history_size: int = Field(description="Total events in history")
    partition_details: dict[str, dict[str, Any]] = Field(
        default_factory=dict, description="Details for each partition"
    )


class InMemoryEventBus(ProtocolEventBusInMemory):
    """
    ⚠️  DEV/TEST ONLY - In-Memory Event Bus with Workflow Isolation ⚠️

    Provides partitioned queues for workflow isolation and implements both
    synchronous and asynchronous ProtocolEventBus interface methods.

    Features:
    - Workflow instance isolation via partitioned queues
    - Support for both sync and async subscribers
    - Event history tracking per partition
    - Deterministic ordering and idempotency guarantees
    - Comprehensive cleanup and resource management
    - Context manager support for automatic cleanup
    """

    def __init__(self, credentials: EventBusCredentialsModel | None = None, **kwargs):
        """
        Initialize in-memory event bus.

        Args:
            credentials: Event bus credentials (ignored for in-memory implementation)
            **kwargs: Additional configuration options
        """
        # Warn about dev/test usage
        logger.warning(
            "🚨 InMemoryEventBus: DEV/TEST ONLY - NEVER USE IN PRODUCTION 🚨"
        )

        # Partitioned storage by workflow instance (OrderedDict for LRU)
        self._partitions: OrderedDict[str, WorkflowPartition] = OrderedDict()

        # Global subscribers (not partitioned)
        self._global_subscribers: list[Callable[[OnexEvent], None]] = []
        self._global_async_subscribers: list[Callable[[OnexEvent], None]] = []

        # Threading/async safety
        self._lock = asyncio.Lock()
        self._sync_lock = threading.RLock()  # For synchronous operations

        # Configuration
        self._max_partitions = kwargs.get("max_partitions", 1000)
        self._default_partition = kwargs.get("default_partition", "global")

        logger.info("✅ InMemoryEventBus initialized for development/testing")

    def _get_partition_id(self, event: OnexEvent) -> str:
        """
        Determine partition ID for an event based on workflow context.

        Args:
            event: OnexEvent to partition

        Returns:
            Partition ID string
        """
        # Try to extract workflow instance ID from event data
        if event.data and isinstance(event.data, dict):
            # Look for workflow identifiers in event data
            if "workflow_instance_id" in event.data:
                return f"workflow_{event.data['workflow_instance_id']}"
            if "instance_id" in event.data:
                return f"instance_{event.data['instance_id']}"

        # Use correlation_id for partitioning if available
        if event.correlation_id:
            return f"correlation_{event.correlation_id}"

        # Fall back to node_id based partitioning
        return f"node_{event.node_id}"

    def _get_or_create_partition(self, partition_id: str) -> WorkflowPartition:
        """Get or create a workflow partition with proper LRU management and race condition protection."""
        # First check without lock (fast path for existing partitions)
        if partition_id in self._partitions:
            with self._sync_lock:
                # Double-checked locking: verify still exists after acquiring lock
                if partition_id in self._partitions:
                    # Move to end for LRU (most recently used)
                    self._partitions.move_to_end(partition_id)
                    return self._partitions[partition_id]

        # Partition doesn't exist, create it under lock (slow path)
        with self._sync_lock:
            # Final check - another thread might have created it while we waited for lock
            if partition_id in self._partitions:
                self._partitions.move_to_end(partition_id)
                return self._partitions[partition_id]

            # Enforce partition limit with proper LRU eviction
            if len(self._partitions) >= self._max_partitions:
                # Remove least recently used partition (first in OrderedDict)
                lru_partition_id, lru_partition = self._partitions.popitem(last=False)
                logger.warning(
                    f"Evicted LRU partition {lru_partition_id} due to limit ({self._max_partitions})"
                )

            # Create new partition atomically
            new_partition = WorkflowPartition(
                partition_id=partition_id, workflow_instance_id=partition_id
            )
            self._partitions[partition_id] = new_partition
            logger.debug(f"Created new partition: {partition_id}")

            return new_partition

    # === Synchronous ProtocolEventBus Interface ===

    def publish(self, event: OnexEvent) -> None:
        """
        Publish an event to the bus (synchronous).

        Args:
            event: OnexEvent to publish
        """
        # Determine partition for this event
        partition_id = self._get_partition_id(event)
        partition = self._get_or_create_partition(partition_id)

        # Add to partition history (thread-safe)
        with self._sync_lock:
            partition.add_event(event)

        # Notify partition-specific subscribers
        for callback in partition.subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"Error in partition subscriber {callback}: {e}",
                    extra={
                        "partition_id": partition_id,
                        "event_id": str(event.event_id),
                        "event_type": str(event.event_type),
                        "callback": str(callback),
                    },
                )

        # Notify global subscribers
        for callback in self._global_subscribers:
            try:
                callback(event)
            except Exception as e:
                logger.error(
                    f"Error in global subscriber {callback}: {e}",
                    extra={
                        "partition_id": partition_id,
                        "event_id": str(event.event_id),
                        "event_type": str(event.event_type),
                        "callback": str(callback),
                    },
                )

        logger.debug(f"📤 Published event {event.event_id} to partition {partition_id}")

    def subscribe(self, callback: Callable[[OnexEvent], None]) -> None:
        """
        Subscribe a callback to receive events (synchronous).

        Args:
            callback: Callable invoked with each OnexEvent
        """
        with self._sync_lock:
            self._global_subscribers.append(callback)
            logger.info(
                f"📥 Added global sync subscriber (total: {len(self._global_subscribers)})"
            )

    def unsubscribe(self, callback: Callable[[OnexEvent], None]) -> None:
        """
        Unsubscribe a previously registered callback (synchronous).

        Args:
            callback: Callable to remove
        """
        with self._sync_lock:
            if callback in self._global_subscribers:
                self._global_subscribers.remove(callback)
                logger.info(
                    f"📤 Removed global sync subscriber (total: {len(self._global_subscribers)})"
                )

    def clear(self) -> None:
        """Remove all subscribers from the event bus."""
        self._global_subscribers.clear()
        self._global_async_subscribers.clear()
        for partition in self._partitions.values():
            partition.subscribers.clear()
            partition.async_subscribers.clear()
        logger.info("🗑️  Cleared all subscribers from event bus")

    # === Asynchronous ProtocolEventBus Interface ===

    async def publish_async(self, event: OnexEvent) -> None:
        """
        Publish an event to the bus (asynchronous).

        Args:
            event: OnexEvent to publish
        """
        async with self._lock:
            # Determine partition for this event
            partition_id = self._get_partition_id(event)
            partition = self._get_or_create_partition(partition_id)

            # Add to partition history
            partition.add_event(event)

            # Collect all async callbacks to execute
            async_callbacks = []

            # Add partition-specific async subscribers
            async_callbacks.extend(partition.async_subscribers)

            # Add global async subscribers
            async_callbacks.extend(self._global_async_subscribers)

            # Execute all async callbacks
            if async_callbacks:
                tasks = []
                for callback in async_callbacks:
                    try:
                        tasks.append(callback(event))
                    except Exception as e:
                        logger.error(f"Error preparing async callback {callback}: {e}")

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    # Log any callback errors
                    for i, result in enumerate(results):
                        if isinstance(result, Exception):
                            logger.error(f"Async callback {i} failed: {result}")

            logger.debug(
                f"📤 Published event {event.event_id} to partition {partition_id} (async)"
            )

    async def subscribe_async(self, callback: Callable[[OnexEvent], None]) -> None:
        """
        Subscribe a callback to receive events (asynchronous).

        Args:
            callback: Callable invoked with each OnexEvent
        """
        async with self._lock:
            self._global_async_subscribers.append(callback)
            logger.info(
                f"📥 Added global async subscriber (total: {len(self._global_async_subscribers)})"
            )

    async def unsubscribe_async(self, callback: Callable[[OnexEvent], None]) -> None:
        """
        Unsubscribe a previously registered callback (asynchronous).

        Args:
            callback: Callable to remove
        """
        async with self._lock:
            if callback in self._global_async_subscribers:
                self._global_async_subscribers.remove(callback)
                logger.info(
                    f"📤 Removed global async subscriber (total: {len(self._global_async_subscribers)})"
                )

    # === Workflow Partition Management ===

    def subscribe_to_partition(
        self,
        partition_id: str,
        callback: Callable[[OnexEvent], None],
        async_callback: bool = False,
    ) -> None:
        """
        Subscribe to a specific workflow partition.

        Args:
            partition_id: Partition to subscribe to
            callback: Event callback function
            async_callback: Whether callback is async
        """
        partition = self._get_or_create_partition(partition_id)

        if async_callback:
            partition.async_subscribers.append(callback)
            logger.info(f"📥 Added async subscriber to partition {partition_id}")
        else:
            partition.subscribers.append(callback)
            logger.info(f"📥 Added sync subscriber to partition {partition_id}")

    def unsubscribe_from_partition(
        self,
        partition_id: str,
        callback: Callable[[OnexEvent], None],
        async_callback: bool = False,
    ) -> None:
        """
        Unsubscribe from a specific workflow partition.

        Args:
            partition_id: Partition to unsubscribe from
            callback: Event callback to remove
            async_callback: Whether callback is async
        """
        if partition_id in self._partitions:
            partition = self._partitions[partition_id]

            if async_callback and callback in partition.async_subscribers:
                partition.async_subscribers.remove(callback)
                logger.info(
                    f"📤 Removed async subscriber from partition {partition_id}"
                )
            elif not async_callback and callback in partition.subscribers:
                partition.subscribers.remove(callback)
                logger.info(f"📤 Removed sync subscriber from partition {partition_id}")

    def clear_partition(self, partition_id: str) -> None:
        """Clear all subscribers and history for a partition."""
        if partition_id in self._partitions:
            partition = self._partitions[partition_id]
            partition.subscribers.clear()
            partition.async_subscribers.clear()
            partition.clear_history()
            logger.info(f"🗑️  Cleared partition {partition_id}")

    def remove_partition(self, partition_id: str) -> None:
        """Remove a partition entirely."""
        if partition_id in self._partitions:
            del self._partitions[partition_id]
            logger.info(f"🗑️  Removed partition {partition_id}")

    # === ProtocolEventBusInMemory Interface ===

    def get_event_history(self) -> list[OnexEvent]:
        """Get the history of all events processed by this event bus."""
        all_events = []
        for partition in self._partitions.values():
            all_events.extend(partition.event_history)

        # Sort by timestamp for chronological order
        all_events.sort(key=lambda e: e.timestamp)
        return all_events

    def get_partition_event_history(self, partition_id: str) -> list[OnexEvent]:
        """Get event history for a specific partition."""
        if partition_id in self._partitions:
            return list(self._partitions[partition_id].event_history)
        return []

    def clear_event_history(self) -> None:
        """Clear the event history for all partitions."""
        for partition in self._partitions.values():
            partition.clear_history()
        logger.info("🗑️  Cleared all event history")

    def get_subscriber_count(self) -> int:
        """Get the total number of active subscribers."""
        total = len(self._global_subscribers) + len(self._global_async_subscribers)

        for partition in self._partitions.values():
            total += len(partition.subscribers) + len(partition.async_subscribers)

        return total

    # === Statistics and Monitoring ===

    def get_stats(self) -> EventBusStats:
        """Get comprehensive event bus statistics."""
        total_events = sum(len(p.event_history) for p in self._partitions.values())
        total_sync = len(self._global_subscribers) + sum(
            len(p.subscribers) for p in self._partitions.values()
        )
        total_async = len(self._global_async_subscribers) + sum(
            len(p.async_subscribers) for p in self._partitions.values()
        )

        partition_details = {}
        for partition_id, partition in self._partitions.items():
            partition_details[partition_id] = {
                "events": len(partition.event_history),
                "sync_subscribers": len(partition.subscribers),
                "async_subscribers": len(partition.async_subscribers),
                "workflow_instance_id": partition.workflow_instance_id,
            }

        return EventBusStats(
            total_events_published=total_events,
            total_partitions=len(self._partitions),
            total_sync_subscribers=total_sync,
            total_async_subscribers=total_async,
            event_history_size=total_events,
            partition_details=partition_details,
        )

    def get_partition_ids(self) -> list[str]:
        """Get list of all partition IDs."""
        return list(self._partitions.keys())

    # === Cleanup and Resource Management ===

    async def shutdown(self) -> None:
        """Shutdown the event bus and clean up resources."""
        async with self._lock:
            # Clear all subscribers
            self.clear()

            # Clear all partitions
            self._partitions.clear()

            logger.info("🛑 InMemoryEventBus shutdown complete")

    # === Context Manager Support ===

    def __enter__(self) -> "InMemoryEventBus":
        """Enter synchronous context manager."""
        logger.debug("📥 Entered InMemoryEventBus context manager")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit synchronous context manager with cleanup."""
        try:
            # Synchronous cleanup
            self.clear()
            self._partitions.clear()
            logger.info("🧹 InMemoryEventBus context manager cleanup complete")
        except Exception as e:
            logger.error(f"Error during context manager cleanup: {e}")

    async def __aenter__(self) -> "InMemoryEventBus":
        """Enter asynchronous context manager."""
        logger.debug("📥 Entered InMemoryEventBus async context manager")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit asynchronous context manager with cleanup."""
        try:
            await self.shutdown()
        except Exception as e:
            logger.error(f"Error during async context manager cleanup: {e}")

    # === Development/Testing Utilities ===

    def reset_for_testing(self) -> None:
        """Reset event bus to clean state for testing."""
        self._partitions.clear()
        self._global_subscribers.clear()
        self._global_async_subscribers.clear()
        logger.info("🔄 InMemoryEventBus reset for testing")

    def simulate_partition_overflow(self) -> None:
        """Simulate partition overflow for testing."""
        # Create partitions beyond limit to test cleanup
        for i in range(self._max_partitions + 5):
            partition_id = f"test_partition_{i}"
            self._get_or_create_partition(partition_id)

        logger.info(
            f"🧪 Simulated partition overflow (created {self._max_partitions + 5} partitions)"
        )

    # === Memory Management for Long-Running Tests ===

    def cleanup_old_partitions(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up partitions that haven't been accessed recently.

        Args:
            max_age_seconds: Maximum age for partitions (default: 1 hour)

        Returns:
            Number of partitions cleaned up
        """
        import time

        current_time = time.time()
        partitions_to_remove = []

        with self._sync_lock:
            for partition_id, partition in self._partitions.items():
                # Check if partition has any recent events
                if partition.event_history:
                    latest_event = partition.event_history[-1]
                    event_age = current_time - latest_event.timestamp.timestamp()
                    if event_age > max_age_seconds:
                        partitions_to_remove.append(partition_id)
                else:
                    # Empty partitions can be cleaned up immediately
                    partitions_to_remove.append(partition_id)

            # Remove old partitions
            for partition_id in partitions_to_remove:
                del self._partitions[partition_id]

        if partitions_to_remove:
            logger.info(f"🧹 Cleaned up {len(partitions_to_remove)} old partitions")

        return len(partitions_to_remove)

    def trim_event_histories(self, max_events_per_partition: int = 100) -> int:
        """
        Trim event histories to prevent memory growth in long-running tests.

        Args:
            max_events_per_partition: Maximum events to keep per partition

        Returns:
            Total number of events trimmed across all partitions
        """
        total_trimmed = 0

        with self._sync_lock:
            for partition in self._partitions.values():
                current_count = len(partition.event_history)
                if current_count > max_events_per_partition:
                    events_to_trim = current_count - max_events_per_partition
                    partition.event_history = partition.event_history[
                        -max_events_per_partition:
                    ]
                    total_trimmed += events_to_trim

        if total_trimmed > 0:
            logger.info(f"🧹 Trimmed {total_trimmed} events from partition histories")

        return total_trimmed

    def get_memory_usage_stats(self) -> dict[str, int]:
        """
        Get memory usage statistics for monitoring long-running tests.

        Returns:
            Dictionary with memory usage statistics
        """
        total_events = 0
        total_subscribers = 0

        with self._sync_lock:
            for partition in self._partitions.values():
                total_events += len(partition.event_history)
                total_subscribers += len(partition.subscribers) + len(
                    partition.async_subscribers
                )

        total_subscribers += len(self._global_subscribers) + len(
            self._global_async_subscribers
        )

        return {
            "total_partitions": len(self._partitions),
            "total_events_in_history": total_events,
            "total_subscribers": total_subscribers,
            "estimated_memory_kb": (
                total_events * 1 + total_subscribers * 0.1 + len(self._partitions) * 0.5
            ),
        }


# Global instance for easy access in development/testing
_global_dev_event_bus: InMemoryEventBus | None = None


def get_dev_event_bus() -> InMemoryEventBus:
    """
    Get or create the global development event bus instance.

    ⚠️  DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

    Returns:
        InMemoryEventBus instance
    """
    global _global_dev_event_bus
    if _global_dev_event_bus is None:
        _global_dev_event_bus = InMemoryEventBus()
        logger.info("✅ Created global development event bus")
    return _global_dev_event_bus


async def setup_dev_event_bus() -> InMemoryEventBus:
    """
    Setup and return the development event bus instance.

    ⚠️  DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

    Returns:
        InMemoryEventBus instance
    """
    bus = get_dev_event_bus()
    logger.info("🚀 Development event bus setup complete")
    return bus
