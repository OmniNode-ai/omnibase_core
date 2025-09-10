"""
Comprehensive test harness for InMemoryEventStore.

⚠️  DEV/TEST ONLY - Tests for development event store ⚠️
"""

import os
import tempfile
from datetime import datetime
from uuid import uuid4

import pytest

from omnibase_core.dev_adapters.memory_event_store import (
    InMemoryEventStore,
    StoredEvent,
    get_dev_event_store,
)
from omnibase_core.model.core.model_onex_event import OnexEvent


class TestInMemoryEventStore:
    """Test suite for InMemoryEventStore development adapter."""

    def setup_method(self):
        """Setup fresh event store for each test."""
        self.event_store = InMemoryEventStore()
        self.test_events = []

    def create_test_event(
        self,
        event_type: str = "test.event",
        node_id: str = "test-node",
        correlation_id: str | None = None,
        data: dict | None = None,
    ) -> OnexEvent:
        """Create a test event."""
        if data is None:
            data = {"test": "data"}

        if correlation_id:
            correlation_uuid = uuid4()
        else:
            correlation_uuid = None

        event = OnexEvent(
            event_type=event_type,
            node_id=node_id,
            data=data,
            correlation_id=correlation_uuid,
        )
        self.test_events.append(event)
        return event

    # === Basic Functionality Tests ===

    def test_initialization(self):
        """Test event store initialization."""
        assert self.event_store is not None
        assert len(self.event_store.get_all_events()) == 0
        assert len(self.event_store.get_stream_ids()) == 0

    def test_store_single_event(self):
        """Test storing a single event."""
        event = self.create_test_event()

        stored_event = self.event_store.store_event(event)

        assert isinstance(stored_event, StoredEvent)
        assert stored_event.event == event
        assert stored_event.sequence_number == 1
        assert stored_event.stream_sequence == 1
        assert stored_event.checksum != ""

    def test_store_multiple_events(self):
        """Test storing multiple events with sequence ordering."""
        events = [
            self.create_test_event(event_type=f"test.event.{i}") for i in range(3)
        ]

        stored_events = []
        for event in events:
            stored_events.append(self.event_store.store_event(event))

        # Verify global sequence numbers
        assert stored_events[0].sequence_number == 1
        assert stored_events[1].sequence_number == 2
        assert stored_events[2].sequence_number == 3

        # Verify all events retrievable
        all_events = self.event_store.get_all_events()
        assert len(all_events) == 3

    def test_idempotency_violation(self):
        """Test idempotency enforcement - duplicate event IDs should fail."""
        event = self.create_test_event()

        # Store first time - should succeed
        self.event_store.store_event(event)

        # Store same event again - should fail
        with pytest.raises(ValueError, match="already exists"):
            self.event_store.store_event(event)

    def test_event_exists_check(self):
        """Test event existence checking."""
        event = self.create_test_event()

        assert not self.event_store.event_exists(event.event_id)

        self.event_store.store_event(event)

        assert self.event_store.event_exists(event.event_id)

    # === Stream Organization Tests ===

    def test_stream_organization(self):
        """Test events are organized into streams."""
        # Create events for different streams
        event1 = OnexEvent(
            event_type="test.event",
            node_id="node-1",
            data={"workflow_instance_id": "workflow-a"},
        )

        event2 = OnexEvent(
            event_type="test.event",
            node_id="node-2",
            data={"workflow_instance_id": "workflow-b"},
        )

        event3 = OnexEvent(
            event_type="test.event",
            node_id="node-1",
            data={"workflow_instance_id": "workflow-a"},
        )

        # Store events
        stored1 = self.event_store.store_event(event1)
        stored2 = self.event_store.store_event(event2)
        stored3 = self.event_store.store_event(event3)

        # Verify stream sequences
        assert stored1.stream_sequence == 1
        assert stored2.stream_sequence == 1  # New stream
        assert stored3.stream_sequence == 2  # Same stream as event1

        # Verify streams exist
        stream_ids = self.event_store.get_stream_ids()
        assert len(stream_ids) == 2

    def test_get_events_by_stream(self):
        """Test retrieving events by stream."""
        # Create events for specific stream
        correlation_id = uuid4()
        events = []
        for i in range(3):
            event = OnexEvent(
                event_type=f"test.event.{i}",
                node_id="test-node",
                correlation_id=correlation_id,
                data={"sequence": i},
            )
            events.append(event)
            self.event_store.store_event(event)

        # Get events from stream
        stream_id = f"correlation_{correlation_id}"
        stream_events = self.event_store.get_events_by_stream(stream_id)

        assert len(stream_events) == 3
        for i, stored_event in enumerate(stream_events):
            assert stored_event.event.data["sequence"] == i

    def test_get_events_from_sequence(self):
        """Test retrieving events from specific sequence number."""
        correlation_id = uuid4()
        events = []
        for i in range(5):
            event = OnexEvent(
                event_type=f"test.event.{i}",
                node_id="test-node",
                correlation_id=correlation_id,
                data={"sequence": i},
            )
            events.append(event)
            self.event_store.store_event(event)

        # Get events from sequence 3
        stream_id = f"correlation_{correlation_id}"
        stream_events = self.event_store.get_events_by_stream(
            stream_id, from_sequence=3
        )

        assert len(stream_events) == 3  # Sequences 3, 4, 5
        assert stream_events[0].stream_sequence == 3
        assert stream_events[1].stream_sequence == 4
        assert stream_events[2].stream_sequence == 5

    def test_stream_info(self):
        """Test getting stream information."""
        correlation_id = uuid4()
        stream_id = f"correlation_{correlation_id}"

        # Initially no stream info
        info = self.event_store.get_stream_info(stream_id)
        assert info is None

        # Create events in stream
        for i in range(3):
            event = OnexEvent(
                event_type=f"test.event.{i}",
                node_id="test-node",
                correlation_id=correlation_id,
                data={"sequence": i},
            )
            self.event_store.store_event(event)

        # Get stream info
        info = self.event_store.get_stream_info(stream_id)
        assert info is not None
        assert info["stream_id"] == stream_id
        assert info["event_count"] == 3
        assert info["last_sequence"] == 3
        assert info["first_event"] is not None
        assert info["last_event"] is not None

    # === Event Retrieval Tests ===

    def test_get_all_events_ordering(self):
        """Test global event ordering."""
        # Create events in different streams
        events_data = [
            ("stream-a", 1),
            ("stream-b", 1),
            ("stream-a", 2),
            ("stream-c", 1),
            ("stream-b", 2),
        ]

        for stream_suffix, sequence in events_data:
            event = OnexEvent(
                event_type="test.event",
                node_id=stream_suffix,
                data={"stream": stream_suffix, "seq": sequence},
            )
            self.event_store.store_event(event)

        # Get all events - should be in global sequence order
        all_events = self.event_store.get_all_events()
        assert len(all_events) == 5

        for i, stored_event in enumerate(all_events):
            assert stored_event.sequence_number == i + 1

    def test_get_all_events_with_limits(self):
        """Test getting all events with sequence and limit filters."""
        # Store 10 events
        for i in range(10):
            event = self.create_test_event(event_type=f"test.event.{i}")
            self.event_store.store_event(event)

        # Get events from sequence 5 with limit 3
        events = self.event_store.get_all_events(from_global_sequence=5, limit=3)

        assert len(events) == 3
        assert events[0].sequence_number == 5
        assert events[1].sequence_number == 6
        assert events[2].sequence_number == 7

    def test_get_event_by_id(self):
        """Test retrieving specific event by ID."""
        events = [
            self.create_test_event(event_type=f"test.event.{i}") for i in range(3)
        ]

        for event in events:
            self.event_store.store_event(event)

        # Find specific event
        target_event = events[1]
        found_event = self.event_store.get_event_by_id(target_event.event_id)

        assert found_event is not None
        assert found_event.event == target_event

        # Search for non-existent event
        fake_id = uuid4()
        not_found = self.event_store.get_event_by_id(fake_id)
        assert not_found is None

    # === Limits and Cleanup Tests ===

    def test_stream_size_limits(self):
        """Test stream size limit enforcement."""
        # Create event store with small limit
        event_store = InMemoryEventStore(max_events_per_stream=3)

        correlation_id = uuid4()
        events = []

        # Store more events than limit
        for i in range(5):
            event = OnexEvent(
                event_type=f"test.event.{i}",
                node_id="test-node",
                correlation_id=correlation_id,
                data={"sequence": i},
            )
            events.append(event)
            event_store.store_event(event)

        # Should only keep latest events within limit
        stream_id = f"correlation_{correlation_id}"
        stream_events = event_store.get_events_by_stream(stream_id)

        assert len(stream_events) <= 3
        # Should have latest events (2, 3, 4)
        sequences = [e.event.data["sequence"] for e in stream_events]
        assert sequences == [2, 3, 4]

    def test_clear_stream(self):
        """Test clearing specific stream."""
        correlation_id = uuid4()
        stream_id = f"correlation_{correlation_id}"

        # Create events in stream
        for i in range(3):
            event = OnexEvent(
                event_type=f"test.event.{i}",
                node_id="test-node",
                correlation_id=correlation_id,
            )
            self.event_store.store_event(event)

        # Verify stream has events
        assert len(self.event_store.get_events_by_stream(stream_id)) == 3

        # Clear stream
        self.event_store.clear_stream(stream_id)

        # Verify stream is empty
        assert len(self.event_store.get_events_by_stream(stream_id)) == 0

    def test_clear_all(self):
        """Test clearing all events."""
        # Store events in multiple streams
        for i in range(3):
            for j in range(2):
                event = OnexEvent(
                    event_type="test.event",
                    node_id=f"node-{i}",
                    data={"stream": i, "event": j},
                )
                self.event_store.store_event(event)

        assert len(self.event_store.get_all_events()) == 6
        assert len(self.event_store.get_stream_ids()) == 3

        # Clear all
        self.event_store.clear_all()

        assert len(self.event_store.get_all_events()) == 0
        assert len(self.event_store.get_stream_ids()) == 0

    # === Statistics Tests ===

    def test_statistics(self):
        """Test event store statistics."""
        # Create events across multiple streams
        for i in range(3):
            for j in range(2):
                event = OnexEvent(
                    event_type="test.event",
                    node_id=f"node-{i}",
                    data={"stream": i, "event": j},
                )
                self.event_store.store_event(event)

        stats = self.event_store.get_stats()

        assert stats["total_events"] == 6
        assert stats["total_streams"] == 3
        assert stats["global_sequence"] == 6
        assert stats["unique_event_ids"] == 6
        assert len(stats["streams"]) == 3

    # === File Persistence Tests ===

    def test_save_to_jsonl(self):
        """Test saving events to JSONL file."""
        # Create test events
        events = []
        for i in range(3):
            event = OnexEvent(
                event_type=f"test.event.{i}",
                node_id="test-node",
                data={"sequence": i, "test": "data"},
            )
            events.append(event)
            self.event_store.store_event(event)

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            filepath = f.name

        try:
            self.event_store.save_to_jsonl(filepath)

            # Verify file exists and has content
            assert os.path.exists(filepath)

            with open(filepath, "r") as f:
                lines = f.readlines()
                assert len(lines) == 3

                # Verify first line contains event data
                import json

                first_record = json.loads(lines[0])
                assert "event" in first_record
                assert "sequence_number" in first_record
                assert "checksum" in first_record

        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_from_jsonl(self):
        """Test loading events from JSONL file."""
        # Create and save events
        original_events = []
        for i in range(3):
            event = OnexEvent(
                event_type=f"test.event.{i}",
                node_id="test-node",
                data={"sequence": i, "test": "data"},
            )
            original_events.append(event)
            self.event_store.store_event(event)

        # Save to file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            filepath = f.name

        try:
            self.event_store.save_to_jsonl(filepath)

            # Create new event store and load
            new_event_store = InMemoryEventStore()
            new_event_store.load_from_jsonl(filepath)

            # Verify events loaded
            loaded_events = new_event_store.get_all_events()
            assert len(loaded_events) == 3

            # Verify event content (note: new sequence numbers assigned)
            for i, stored_event in enumerate(loaded_events):
                assert stored_event.event.event_type == f"test.event.{i}"
                assert stored_event.event.data["sequence"] == i

        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_load_with_duplicates(self):
        """Test loading JSONL with duplicate events."""
        # Create events
        events = []
        for i in range(2):
            event = OnexEvent(
                event_type=f"test.event.{i}", node_id="test-node", data={"sequence": i}
            )
            events.append(event)
            self.event_store.store_event(event)

        # Save to file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            filepath = f.name

        try:
            self.event_store.save_to_jsonl(filepath)

            # Load into same event store (should skip duplicates)
            self.event_store.load_from_jsonl(filepath)

            # Should still have only original events
            all_events = self.event_store.get_all_events()
            assert len(all_events) == 2

        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    # === Checksum Validation Tests ===

    def test_checksum_calculation(self):
        """Test checksum calculation for stored events."""
        event = self.create_test_event()
        stored_event = self.event_store.store_event(event)

        assert stored_event.checksum != ""

        # Recalculate checksum - should match
        recalculated = stored_event.calculate_checksum()
        assert recalculated == stored_event.checksum

    def test_checksum_consistency(self):
        """Test checksum consistency across identical events."""
        # Create identical events with same content
        event1 = OnexEvent(
            event_type="test.event", node_id="test-node", data={"consistent": "data"}
        )

        event2 = OnexEvent(
            event_type="test.event", node_id="test-node", data={"consistent": "data"}
        )

        # Force same event ID for testing
        event2.event_id = event1.event_id

        stored1 = self.event_store.store_event(event1)

        # Can't store duplicate, but we can calculate checksum
        stored2 = StoredEvent(
            event=event2, sequence_number=999, stream_sequence=999, checksum=""
        )
        stored2.checksum = stored2.calculate_checksum()

        # Checksums should match for identical content
        assert stored1.checksum == stored2.checksum


class TestGlobalEventStore:
    """Test global event store instance management."""

    def test_global_instance_creation(self):
        """Test global event store instance creation."""
        store1 = get_dev_event_store()
        store2 = get_dev_event_store()

        # Should return same instance
        assert store1 is store2
        assert isinstance(store1, InMemoryEventStore)

    def test_global_instance_functionality(self):
        """Test global instance basic functionality."""
        store = get_dev_event_store()

        # Clear to clean state
        store.clear_all()

        # Test basic functionality
        event = OnexEvent(
            event_type="test.global", node_id="global-test", data={"test": "global"}
        )

        stored_event = store.store_event(event)

        assert stored_event.event == event
        assert len(store.get_all_events()) == 1


class TestEventStoreIntegration:
    """Integration tests combining multiple event store features."""

    def setup_method(self):
        """Setup for integration tests."""
        self.event_store = InMemoryEventStore()

    def test_multi_stream_workflow(self):
        """Test complex multi-stream workflow scenario."""
        # Simulate workflow with multiple correlated streams
        workflows = ["order-123", "order-456", "order-789"]

        stored_events = []

        # Create events for each workflow
        for workflow_id in workflows:
            correlation_id = uuid4()

            # Each workflow has multiple events
            for step in ["started", "processing", "completed"]:
                event = OnexEvent(
                    event_type=f"workflow.{step}",
                    node_id=f"worker-{workflow_id}",
                    correlation_id=correlation_id,
                    data={
                        "workflow_id": workflow_id,
                        "step": step,
                        "timestamp": datetime.now().isoformat(),
                    },
                )
                stored_event = self.event_store.store_event(event)
                stored_events.append(stored_event)

        # Verify total events
        assert len(stored_events) == 9  # 3 workflows × 3 steps

        # Verify streams created
        stream_ids = self.event_store.get_stream_ids()
        assert len(stream_ids) == 3  # One stream per correlation_id

        # Verify each stream has 3 events
        for stream_id in stream_ids:
            stream_events = self.event_store.get_events_by_stream(stream_id)
            assert len(stream_events) == 3

            # Verify event ordering within stream
            steps = [e.event.data["step"] for e in stream_events]
            assert steps == ["started", "processing", "completed"]

    def test_event_replay_scenario(self):
        """Test event replay scenario for workflow recovery."""
        correlation_id = uuid4()
        stream_id = f"correlation_{correlation_id}"

        # Store initial events
        initial_events = []
        for i in range(5):
            event = OnexEvent(
                event_type=f"workflow.step.{i}",
                node_id="workflow-node",
                correlation_id=correlation_id,
                data={"step": i, "data": f"step_{i}_data"},
            )
            stored_event = self.event_store.store_event(event)
            initial_events.append(stored_event)

        # Simulate replay from sequence 3
        replay_events = self.event_store.get_events_by_stream(
            stream_id, from_sequence=3
        )

        assert len(replay_events) == 3  # Events with stream_sequence 3, 4, 5
        assert (
            replay_events[0].event.data["step"] == 2
        )  # 0-indexed step, but stream_sequence 3
        assert replay_events[1].event.data["step"] == 3
        assert replay_events[2].event.data["step"] == 4

    def test_concurrent_stream_operations(self):
        """Test concurrent operations across multiple streams."""
        # Create events interleaved across multiple streams
        stream_correlations = [uuid4() for _ in range(3)]

        # Interleave events across streams
        for i in range(6):
            correlation_id = stream_correlations[i % 3]
            event = OnexEvent(
                event_type="concurrent.event",
                node_id=f"node-{i}",
                correlation_id=correlation_id,
                data={"global_order": i, "stream": i % 3},
            )
            self.event_store.store_event(event)

        # Verify global ordering maintained
        all_events = self.event_store.get_all_events()
        assert len(all_events) == 6
        for i, stored_event in enumerate(all_events):
            assert stored_event.sequence_number == i + 1
            assert stored_event.event.data["global_order"] == i

        # Verify stream-specific ordering
        for stream_idx, correlation_id in enumerate(stream_correlations):
            stream_id = f"correlation_{correlation_id}"
            stream_events = self.event_store.get_events_by_stream(stream_id)

            assert len(stream_events) == 2  # 6 events / 3 streams = 2 each

            # Verify stream sequences
            assert stream_events[0].stream_sequence == 1
            assert stream_events[1].stream_sequence == 2
