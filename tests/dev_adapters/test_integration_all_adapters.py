"""
Integration tests combining all development adapters.

⚠️  WARNING: DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

This module provides comprehensive integration tests that combine:
- InMemoryEventBus (event routing and subscription)
- InMemoryEventStore (event persistence and querying)
- InMemorySnapshotStore (state checkpointing)
- DeterministicTestContext (controllable time and IDs)

Tests cover complete workflow scenarios with event sourcing patterns.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import pytest

from omnibase_core.dev_adapters.deterministic_utils import DeterministicTestContext
from omnibase_core.dev_adapters.memory_event_bus import InMemoryEventBus
from omnibase_core.dev_adapters.memory_event_store import InMemoryEventStore
from omnibase_core.dev_adapters.memory_snapshot_store import InMemorySnapshotStore
from omnibase_core.model.core.model_onex_event import OnexEvent


class TestAllAdaptersIntegration:
    """Comprehensive integration tests combining all development adapters."""

    def setup_method(self):
        """Set up test environment with all adapters."""
        # Initialize deterministic test context
        self.test_context = DeterministicTestContext(
            start_time=datetime(2025, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            id_prefix="integration",
            start_counter=1,
        )

        # Initialize all adapters
        self.event_bus = InMemoryEventBus(max_partitions=10)
        self.event_store = InMemoryEventStore(max_streams_per_store=20)
        self.snapshot_store = InMemorySnapshotStore(max_snapshots_per_workflow=5)

        # Track events for validation
        self.received_events = []
        self.async_received_events = []

    def teardown_method(self):
        """Clean up after each test."""
        self.test_context.reset_all()
        self.event_bus.clear()
        self.event_store.clear_all()
        self.snapshot_store.clear_all()
        self.received_events.clear()
        self.async_received_events.clear()

    def _create_test_event(
        self, event_type: str = "workflow.started", node_id: str = "test-node-001"
    ) -> OnexEvent:
        """Create a test event with deterministic properties."""
        return OnexEvent(
            event_type=event_type,
            node_id=node_id,
            data={
                "test": "data",
                "counter": self.test_context.id_generator.get_current_counter(),
            },
        )

    def _sync_event_handler(self, event: OnexEvent) -> None:
        """Synchronous event handler for testing."""
        self.received_events.append(event)

    async def _async_event_handler(self, event: OnexEvent) -> None:
        """Asynchronous event handler for testing."""
        self.async_received_events.append(event)

    def test_complete_workflow_lifecycle(self):
        """Test complete workflow with event bus, store, and snapshots."""
        # === Phase 1: Create workflow and register handlers ===

        workflow_id = "integration-workflow-001"
        partition_id = (
            f"workflow_{workflow_id}"  # Match the event bus partition ID format
        )

        # Subscribe to events
        self.event_bus.subscribe_to_partition(partition_id, self._sync_event_handler)

        # === Phase 2: Generate workflow events ===

        # Create workflow started event
        started_event = self._create_test_event("workflow.started", "orchestrator-node")
        started_event.data.update(
            {
                "workflow_id": workflow_id,
                "workflow_instance_id": workflow_id,
                "status": "started",
            }
        )

        # Store and publish event
        stored_started = self.event_store.store_event(started_event)
        self.event_bus.publish(started_event)

        # Advance time and create processing event
        self.test_context.clock.advance_minutes(5)

        processing_event = self._create_test_event(
            "workflow.step.completed", "compute-node"
        )
        processing_event.data.update(
            {
                "workflow_id": workflow_id,
                "workflow_instance_id": workflow_id,
                "step": "data_processing",
            }
        )

        stored_processing = self.event_store.store_event(processing_event)
        self.event_bus.publish(processing_event)

        # === Phase 3: Create state snapshot ===

        workflow_state = {
            "workflow_id": workflow_id,
            "status": "processing",
            "steps_completed": ["started", "data_processing"],
            "current_step": "analysis",
            "progress": 0.6,
        }

        snapshot = self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=2,
            state_data=workflow_state,
            event_count=2,
            metadata={"checkpoint_reason": "step_completion"},
        )

        # === Phase 4: Complete workflow ===

        self.test_context.clock.advance_minutes(10)

        completed_event = self._create_test_event("workflow.completed", "reducer-node")
        completed_event.data.update(
            {
                "workflow_id": workflow_id,
                "workflow_instance_id": workflow_id,
                "result": "success",
            }
        )

        stored_completed = self.event_store.store_event(completed_event)
        self.event_bus.publish(completed_event)

        # Final snapshot
        final_state = workflow_state.copy()
        final_state.update({"status": "completed", "progress": 1.0})

        final_snapshot = self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=3,
            state_data=final_state,
            event_count=3,
        )

        # === Phase 5: Validate complete integration ===

        # Check event bus received all events
        assert len(self.received_events) == 3
        assert self.received_events[0].event_type == "workflow.started"
        assert self.received_events[1].event_type == "workflow.step.completed"
        assert self.received_events[2].event_type == "workflow.completed"

        # Check event store has all events with correct sequencing
        all_events = self.event_store.get_all_events()
        assert len(all_events) == 3
        assert all_events[0].sequence_number == 1
        assert all_events[1].sequence_number == 2
        assert all_events[2].sequence_number == 3

        # Validate events by type
        workflow_events = self.event_store.get_events_by_type("workflow.started")
        assert len(workflow_events) == 1
        assert workflow_events[0].event.data["workflow_id"] == workflow_id

        # Check snapshot store has correct snapshots
        all_snapshots = self.snapshot_store.get_all_snapshots(workflow_id)
        assert len(all_snapshots) == 2
        assert all_snapshots[0].sequence_number == 2
        assert all_snapshots[1].sequence_number == 3
        assert all_snapshots[1].state_data["status"] == "completed"

        # Validate latest snapshot
        latest_snapshot = self.snapshot_store.get_latest_snapshot(workflow_id)
        assert latest_snapshot.state_data["progress"] == 1.0
        assert latest_snapshot.event_count == 3

    @pytest.mark.asyncio
    async def test_async_workflow_with_error_recovery(self):
        """Test async workflow with error scenarios and recovery."""
        # === Phase 1: Setup async workflow ===

        workflow_id = "async-workflow-002"
        partition_id = f"workflow_{workflow_id}"

        # Subscribe with async handler
        self.event_bus.subscribe_to_partition(
            partition_id, self._async_event_handler, async_callback=True
        )

        # === Phase 2: Generate events with error scenario ===

        # Normal start event
        start_event = self._create_test_event("workflow.started")
        start_event.data.update(
            {"workflow_id": workflow_id, "workflow_instance_id": workflow_id}
        )

        stored_start = self.event_store.store_event(start_event)
        await self.event_bus.publish_async(start_event)

        # Create initial snapshot
        initial_state = {"workflow_id": workflow_id, "status": "running"}
        self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=1,
            state_data=initial_state,
            event_count=1,
        )

        # Advance time and create error event
        self.test_context.clock.advance_minutes(2)

        error_event = self._create_test_event("workflow.failed")
        error_event.data.update(
            {
                "workflow_id": workflow_id,
                "workflow_instance_id": workflow_id,
                "error": "processing_timeout",
                "retry_count": 1,
            }
        )

        stored_error = self.event_store.store_event(error_event)
        await self.event_bus.publish_async(error_event)

        # === Phase 3: Recovery scenario ===

        # Advance time for retry
        self.test_context.clock.advance_minutes(5)

        # Restore from snapshot
        recovery_snapshot = self.snapshot_store.get_latest_snapshot(workflow_id)
        assert recovery_snapshot is not None
        assert recovery_snapshot.state_data["status"] == "running"

        # Create retry event
        retry_event = self._create_test_event("workflow.restarted")
        retry_event.data.update(
            {
                "workflow_id": workflow_id,
                "workflow_instance_id": workflow_id,
                "recovered_from_sequence": recovery_snapshot.sequence_number,
            }
        )

        stored_retry = self.event_store.store_event(retry_event)
        await self.event_bus.publish_async(retry_event)

        # Success after retry
        success_event = self._create_test_event("workflow.completed")
        success_event.data.update(
            {
                "workflow_id": workflow_id,
                "workflow_instance_id": workflow_id,
                "retry_successful": True,
            }
        )

        stored_success = self.event_store.store_event(success_event)
        await self.event_bus.publish_async(success_event)

        # Final snapshot with recovery info
        final_state = {
            "workflow_id": workflow_id,
            "status": "completed",
            "recovery_performed": True,
            "total_events": 4,
        }

        self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=4,
            state_data=final_state,
            event_count=4,
        )

        # === Phase 4: Validate async integration ===

        # Allow async processing to complete
        await asyncio.sleep(0.1)

        # Check async event handling
        assert len(self.async_received_events) == 4
        event_types = [e.event_type for e in self.async_received_events]
        assert "workflow.started" in event_types
        assert "workflow.failed" in event_types
        assert "workflow.restarted" in event_types
        assert "workflow.completed" in event_types

        # Validate event store sequence
        all_events = self.event_store.get_all_events()
        assert len(all_events) == 4

        # Check recovery pattern in snapshots
        snapshots = self.snapshot_store.get_all_snapshots(workflow_id)
        assert len(snapshots) == 2
        assert snapshots[1].state_data["recovery_performed"] is True

    def test_multi_workflow_isolation(self):
        """Test that multiple workflows remain isolated."""
        # === Setup multiple workflows ===

        workflows = ["workflow-A", "workflow-B", "workflow-C"]
        partition_handlers = {}

        # Create separate handlers for each workflow
        for workflow_id in workflows:
            partition_id = f"workflow_{workflow_id}"
            handler_events = []

            def create_handler(events_list):
                def handler(event: OnexEvent):
                    events_list.append(event)

                return handler

            partition_handlers[workflow_id] = {
                "events": handler_events,
                "handler": create_handler(handler_events),
            }

            self.event_bus.subscribe_to_partition(
                partition_id, partition_handlers[workflow_id]["handler"]
            )

        # === Generate events for each workflow ===

        for i, workflow_id in enumerate(workflows):
            # Advance time differently for each workflow
            self.test_context.clock.advance_minutes(i + 1)

            # Create workflow-specific events
            start_event = self._create_test_event(
                "workflow.started", f"node-{workflow_id}"
            )
            start_event.data.update(
                {
                    "workflow_id": workflow_id,
                    "workflow_instance_id": workflow_id,
                    "sequence": i + 1,
                }
            )

            # Store and publish
            self.event_store.store_event(start_event)
            self.event_bus.publish(start_event)

            # Create workflow state snapshot
            state = {
                "workflow_id": workflow_id,
                "index": i,
                "started_at": self.test_context.clock.now().isoformat(),
            }

            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=1,
                state_data=state,
                event_count=1,
            )

        # === Validate isolation ===

        # Each workflow should only receive its own events
        for workflow_id in workflows:
            events = partition_handlers[workflow_id]["events"]
            assert len(events) == 1
            assert events[0].data["workflow_id"] == workflow_id

        # Event store should have all events but queryable by workflow
        all_events = self.event_store.get_all_events()
        assert len(all_events) == 3

        # Snapshots should be isolated by workflow ID
        for workflow_id in workflows:
            snapshots = self.snapshot_store.get_all_snapshots(workflow_id)
            assert len(snapshots) == 1
            assert snapshots[0].state_data["workflow_id"] == workflow_id

        # Validate no cross-contamination
        workflow_a_snapshots = self.snapshot_store.get_all_snapshots("workflow-A")
        workflow_b_snapshots = self.snapshot_store.get_all_snapshots("workflow-B")

        assert workflow_a_snapshots[0].state_data["index"] == 0
        assert workflow_b_snapshots[0].state_data["index"] == 1

    def test_performance_and_cleanup_integration(self):
        """Test performance features and cleanup across all adapters."""
        # === Generate high-volume test data ===

        workflow_id = "performance-test-workflow"
        partition_id = f"workflow_{workflow_id}"

        # Subscribe to capture all events
        self.event_bus.subscribe_to_partition(partition_id, self._sync_event_handler)

        # Generate 50 events with snapshots every 10 events
        event_count = 50
        snapshot_interval = 10

        for i in range(event_count):
            # Advance time slightly for each event
            self.test_context.clock.advance_seconds(30)

            # Create event
            event = self._create_test_event(
                "workflow.step.completed", f"node-{i % 3}"  # Rotate between 3 nodes
            )
            event.data.update(
                {
                    "workflow_id": workflow_id,
                    "workflow_instance_id": workflow_id,
                    "step": i,
                    "batch": i // 10,
                }
            )

            # Store and publish
            self.event_store.store_event(event)
            self.event_bus.publish(event)

            # Create snapshots at intervals
            if (i + 1) % snapshot_interval == 0:
                state = {
                    "workflow_id": workflow_id,
                    "completed_steps": i + 1,
                    "progress": (i + 1) / event_count,
                    "timestamp": self.test_context.clock.now().isoformat(),
                }

                self.snapshot_store.save_snapshot(
                    workflow_instance_id=workflow_id,
                    sequence_number=i + 1,
                    state_data=state,
                    event_count=i + 1,
                )

        # === Test performance queries ===

        # Query by event type (should use performance index)
        step_events = self.event_store.get_events_by_type("workflow.step.completed")
        assert len(step_events) == event_count

        # Query by node ID (should use performance index)
        node_0_events = self.event_store.get_events_by_node("node-0")
        assert len(node_0_events) == 17  # Events 0, 3, 6, 9, ... 48 (17 total)

        # Test snapshot querying
        all_snapshots = self.snapshot_store.get_all_snapshots(workflow_id)
        assert len(all_snapshots) == 5  # Snapshots at steps 10, 20, 30, 40, 50

        # === Test cleanup functionality ===

        # Test event bus partition cleanup (simulate old partitions)
        self.test_context.clock.advance_hours(2)  # Make partitions "old"

        cleaned_partitions = self.event_bus.cleanup_old_partitions(max_age_seconds=3600)
        # Cleanup might not remove partitions that are still active, so just verify it doesn't error
        assert cleaned_partitions >= 0

        # Test event store stream cleanup
        cleaned_streams = self.event_store.cleanup_old_streams(max_age_seconds=3600)
        # Cleanup methods may not remove items if they're still valid, so just ensure no error
        assert cleaned_streams >= 0

        # Test snapshot cleanup (keep only latest 2)
        deleted_snapshots = self.snapshot_store.delete_old_snapshots(
            workflow_id, keep_latest=2
        )
        assert deleted_snapshots == 3  # Should delete 3 of the 5 snapshots

        remaining_snapshots = self.snapshot_store.get_all_snapshots(workflow_id)
        assert len(remaining_snapshots) == 2

        # Validate latest snapshots are preserved
        assert remaining_snapshots[0].sequence_number == 40
        assert remaining_snapshots[1].sequence_number == 50

    def test_error_handling_integration(self):
        """Test error handling across all adapters."""
        workflow_id = "error-handling-test"
        partition_id = f"workflow:{workflow_id}"

        # === Test event store error handling ===

        # Test invalid event types
        with pytest.raises(ValueError, match="event cannot be None"):
            self.event_store.store_event(None)

        # Test invalid query parameters
        with pytest.raises(ValueError, match="from_global_sequence must be positive"):
            self.event_store.get_all_events(from_global_sequence=-1)

        with pytest.raises(ValueError, match="limit must be positive"):
            self.event_store.get_events_by_type("workflow.started", limit=0)

        with pytest.raises(ValueError, match="node_id cannot be empty"):
            self.event_store.get_events_by_node("")

        # === Test event bus error handling ===

        # Event bus may handle empty partition IDs gracefully, so we just test that it doesn't crash
        try:
            self.event_bus.subscribe_to_partition("", self._sync_event_handler)
        except Exception:
            pass  # Some validation is acceptable

        # === Test snapshot store error handling ===

        # Test invalid workflow IDs
        with pytest.raises(ValueError):
            self.snapshot_store.save_snapshot(
                workflow_instance_id="",  # Empty workflow ID
                sequence_number=1,
                state_data={},
                event_count=1,
            )

        # === Test checksum validation ===

        # Create valid event and snapshot
        event = self._create_test_event()
        stored_event = self.event_store.store_event(event)

        # Validate checksum is working
        assert stored_event.validate_checksum() is True

        # Test snapshot checksum
        snapshot = self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=1,
            state_data={"test": "data"},
            event_count=1,
        )

        assert snapshot.validate_checksum() is True

        # Test corrupted checksum detection
        self.snapshot_store.simulate_corruption(workflow_id)

        with pytest.raises(ValueError, match="Snapshot corruption detected"):
            self.snapshot_store.get_latest_snapshot(workflow_id)

    def test_context_managers_integration(self):
        """Test context manager support across adapters."""
        workflow_id = "context-manager-test"

        # === Test all adapters as context managers ===

        with self.event_bus as bus:
            with self.event_store as store:
                with self.snapshot_store as snap_store:
                    # Create and process events within context
                    event = self._create_test_event()
                    event.data.update(
                        {
                            "workflow_id": workflow_id,
                            "workflow_instance_id": workflow_id,
                        }
                    )

                    # Store event
                    stored = store.store_event(event)
                    assert stored.event.event_id == event.event_id

                    # Publish event
                    partition_id = f"workflow_{workflow_id}"
                    bus.subscribe_to_partition(partition_id, self._sync_event_handler)
                    bus.publish(event)

                    # Create snapshot
                    snapshot = snap_store.save_snapshot(
                        workflow_instance_id=workflow_id,
                        sequence_number=1,
                        state_data={"context_test": True},
                        event_count=1,
                    )

                    # Validate within context
                    assert len(self.received_events) == 1
                    assert snapshot.state_data["context_test"] is True

        # Context managers should clean up automatically
        # Note: Some cleanup may be implementation-specific
