"""
Comprehensive test harness for InMemorySnapshotStore.

⚠️  DEV/TEST ONLY - Tests for development snapshot store ⚠️
"""

from datetime import datetime
from uuid import uuid4

import pytest

from omnibase_core.core.errors.core_errors import OnexError
from omnibase_core.dev_adapters.memory_snapshot_store import (
    InMemorySnapshotStore,
    WorkflowSnapshot,
    get_dev_snapshot_store,
)


class TestInMemorySnapshotStore:
    """Test suite for InMemorySnapshotStore development adapter."""

    def setup_method(self):
        """Setup fresh snapshot store for each test."""
        self.snapshot_store = InMemorySnapshotStore()

    def create_test_state(
        self, workflow_id: str = "test-workflow", state_data: dict | None = None
    ) -> dict:
        """Create test state data."""
        if state_data is None:
            state_data = {
                "workflow_id": workflow_id,
                "current_step": "processing",
                "variables": {"counter": 42, "status": "active"},
                "completed_steps": ["init", "validate"],
                "timestamp": datetime.now().isoformat(),
            }
        return state_data

    # === Basic Functionality Tests ===

    def test_initialization(self):
        """Test snapshot store initialization."""
        assert self.snapshot_store is not None
        assert len(self.snapshot_store.get_workflow_ids()) == 0

    def test_save_single_snapshot(self):
        """Test saving a single snapshot."""
        workflow_id = "test-workflow-123"
        state_data = self.create_test_state(workflow_id)

        snapshot = self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=10,
            state_data=state_data,
            event_count=5,
            metadata={"version": "1.0"},
        )

        assert isinstance(snapshot, WorkflowSnapshot)
        assert snapshot.workflow_instance_id == workflow_id
        assert snapshot.sequence_number == 10
        assert snapshot.event_count == 5
        assert snapshot.state_data == state_data
        assert snapshot.metadata["version"] == "1.0"
        assert snapshot.checksum != ""

    def test_save_multiple_snapshots(self):
        """Test saving multiple snapshots with proper ordering."""
        workflow_id = "test-workflow-123"

        snapshots = []
        for i in range(3):
            state_data = self.create_test_state(
                workflow_id, {"step": i, "data": f"state_{i}"}
            )

            snapshot = self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=(i + 1) * 10,
                state_data=state_data,
                event_count=(i + 1) * 5,
            )
            snapshots.append(snapshot)

        # Verify snapshots are ordered by sequence number
        all_snapshots = self.snapshot_store.get_all_snapshots(workflow_id)
        assert len(all_snapshots) == 3

        for i, snapshot in enumerate(all_snapshots):
            assert snapshot.sequence_number == (i + 1) * 10
            assert snapshot.state_data["step"] == i

    def test_get_latest_snapshot(self):
        """Test retrieving the latest snapshot."""
        workflow_id = "test-workflow-123"

        # Save snapshots out of sequence order
        sequences = [30, 10, 20]
        for seq in sequences:
            state_data = self.create_test_state(workflow_id, {"sequence": seq})
            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=seq,
                state_data=state_data,
                event_count=seq,
            )

        # Latest should be sequence 30
        latest = self.snapshot_store.get_latest_snapshot(workflow_id)
        assert latest is not None
        assert latest.sequence_number == 30
        assert latest.state_data["sequence"] == 30

    def test_get_snapshot_at_sequence(self):
        """Test retrieving snapshot at or before specific sequence."""
        workflow_id = "test-workflow-123"

        # Save snapshots at sequences 10, 20, 30
        sequences = [10, 20, 30]
        for seq in sequences:
            state_data = self.create_test_state(workflow_id, {"sequence": seq})
            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=seq,
                state_data=state_data,
                event_count=seq,
            )

        # Test various lookups
        snapshot_15 = self.snapshot_store.get_snapshot_at_sequence(workflow_id, 15)
        assert snapshot_15.sequence_number == 10  # Latest before 15

        snapshot_20 = self.snapshot_store.get_snapshot_at_sequence(workflow_id, 20)
        assert snapshot_20.sequence_number == 20  # Exact match

        snapshot_25 = self.snapshot_store.get_snapshot_at_sequence(workflow_id, 25)
        assert snapshot_25.sequence_number == 20  # Latest before 25

        snapshot_35 = self.snapshot_store.get_snapshot_at_sequence(workflow_id, 35)
        assert snapshot_35.sequence_number == 30  # Latest before 35

        # Before any snapshots
        snapshot_5 = self.snapshot_store.get_snapshot_at_sequence(workflow_id, 5)
        assert snapshot_5 is None

    def test_nonexistent_workflow(self):
        """Test operations on nonexistent workflows."""
        fake_workflow_id = "nonexistent-workflow"

        assert self.snapshot_store.get_latest_snapshot(fake_workflow_id) is None
        assert (
            self.snapshot_store.get_snapshot_at_sequence(fake_workflow_id, 10) is None
        )
        assert self.snapshot_store.get_all_snapshots(fake_workflow_id) == []

    # === Retention Policy Tests ===

    def test_retention_policy(self):
        """Test snapshot retention policy enforcement."""
        # Create store with small retention limit
        snapshot_store = InMemorySnapshotStore(max_snapshots_per_workflow=3)

        workflow_id = "test-workflow-123"

        # Save more snapshots than limit
        for i in range(5):
            state_data = self.create_test_state(workflow_id, {"sequence": i})
            snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=(i + 1) * 10,
                state_data=state_data,
                event_count=i + 1,
            )

        # Should only keep latest 3
        all_snapshots = snapshot_store.get_all_snapshots(workflow_id)
        assert len(all_snapshots) == 3

        # Should have sequences 30, 40, 50 (latest 3)
        sequences = [s.sequence_number for s in all_snapshots]
        assert sequences == [30, 40, 50]

    def test_delete_old_snapshots(self):
        """Test manual deletion of old snapshots."""
        workflow_id = "test-workflow-123"

        # Create 5 snapshots
        for i in range(5):
            state_data = self.create_test_state(workflow_id, {"sequence": i})
            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=(i + 1) * 10,
                state_data=state_data,
                event_count=i + 1,
            )

        assert len(self.snapshot_store.get_all_snapshots(workflow_id)) == 5

        # Delete old snapshots, keeping latest 2
        deleted_count = self.snapshot_store.delete_old_snapshots(
            workflow_id, keep_latest=2
        )
        assert deleted_count == 3

        # Should now have only 2 snapshots
        remaining = self.snapshot_store.get_all_snapshots(workflow_id)
        assert len(remaining) == 2

        # Should be the latest 2 (sequences 40, 50)
        sequences = [s.sequence_number for s in remaining]
        assert sequences == [40, 50]

    def test_delete_all_snapshots(self):
        """Test deleting all snapshots for a workflow."""
        workflow_id = "test-workflow-123"

        # Create snapshots
        for i in range(3):
            state_data = self.create_test_state(workflow_id, {"sequence": i})
            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=(i + 1) * 10,
                state_data=state_data,
                event_count=i + 1,
            )

        assert len(self.snapshot_store.get_all_snapshots(workflow_id)) == 3

        # Delete all snapshots
        deleted_count = self.snapshot_store.delete_snapshots(workflow_id)
        assert deleted_count == 3

        # Should be empty
        assert len(self.snapshot_store.get_all_snapshots(workflow_id)) == 0
        assert workflow_id not in self.snapshot_store.get_workflow_ids()

    def test_clear_all(self):
        """Test clearing all snapshots."""
        # Create snapshots for multiple workflows
        workflows = ["workflow-1", "workflow-2", "workflow-3"]

        for workflow_id in workflows:
            for i in range(2):
                state_data = self.create_test_state(workflow_id, {"sequence": i})
                self.snapshot_store.save_snapshot(
                    workflow_instance_id=workflow_id,
                    sequence_number=(i + 1) * 10,
                    state_data=state_data,
                    event_count=i + 1,
                )

        assert len(self.snapshot_store.get_workflow_ids()) == 3

        # Clear all
        self.snapshot_store.clear_all()

        assert len(self.snapshot_store.get_workflow_ids()) == 0

    # === Checksum Validation Tests ===

    def test_checksum_calculation(self):
        """Test snapshot checksum calculation."""
        workflow_id = "test-workflow-123"
        state_data = self.create_test_state(workflow_id)

        snapshot = self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=10,
            state_data=state_data,
            event_count=5,
        )

        assert snapshot.checksum != ""
        assert snapshot.validate_checksum()

        # Recalculate should match
        recalculated = snapshot.calculate_checksum()
        assert recalculated == snapshot.checksum

    def test_checksum_validation_enabled(self):
        """Test checksum validation when enabled."""
        # Default behavior - validation enabled
        assert self.snapshot_store._enable_checksum_validation

        workflow_id = "test-workflow-123"
        state_data = self.create_test_state(workflow_id)

        self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=10,
            state_data=state_data,
            event_count=5,
        )

        # Getting snapshot should succeed with valid checksum
        snapshot = self.snapshot_store.get_latest_snapshot(workflow_id)
        assert snapshot is not None

    def test_checksum_validation_disabled(self):
        """Test checksum validation when disabled."""
        # Create store with validation disabled
        snapshot_store = InMemorySnapshotStore(enable_checksum_validation=False)

        workflow_id = "test-workflow-123"
        state_data = self.create_test_state(workflow_id)

        snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=10,
            state_data=state_data,
            event_count=5,
        )

        # Should work even if we simulate corruption
        snapshot = snapshot_store.get_latest_snapshot(workflow_id)
        snapshot.checksum = "corrupted"

        # Should still return snapshot without validation error
        retrieved = snapshot_store.get_latest_snapshot(workflow_id)
        assert retrieved is not None

    def test_checksum_corruption_detection(self):
        """Test detection of checksum corruption."""
        workflow_id = "test-workflow-123"
        state_data = self.create_test_state(workflow_id)

        self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=10,
            state_data=state_data,
            event_count=5,
        )

        # Simulate corruption by directly modifying checksum
        self.snapshot_store.simulate_corruption(workflow_id)

        # Should raise error on retrieval
        with pytest.raises(OnexError, match="corruption detected"):
            self.snapshot_store.get_latest_snapshot(workflow_id)

    def test_validate_all_checksums(self):
        """Test validating all checksums."""
        # Create snapshots for multiple workflows
        workflows = ["workflow-1", "workflow-2"]

        for workflow_id in workflows:
            state_data = self.create_test_state(workflow_id)
            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=10,
                state_data=state_data,
                event_count=5,
            )

        # All should be valid initially
        results = self.snapshot_store.validate_all_checksums()
        assert len(results) == 2
        assert all(results.values())

        # Simulate corruption in one workflow
        self.snapshot_store.simulate_corruption("workflow-1")

        # Validation should detect corruption
        results = self.snapshot_store.validate_all_checksums()
        assert len(results) == 2

        # One should be invalid
        invalid_count = sum(1 for valid in results.values() if not valid)
        assert invalid_count == 1

    # === Statistics Tests ===

    def test_statistics(self):
        """Test snapshot store statistics."""
        # Create snapshots for multiple workflows
        workflows = ["workflow-1", "workflow-2", "workflow-3"]

        for i, workflow_id in enumerate(workflows):
            for j in range(i + 1):  # Different numbers of snapshots per workflow
                state_data = self.create_test_state(workflow_id, {"step": j})
                self.snapshot_store.save_snapshot(
                    workflow_instance_id=workflow_id,
                    sequence_number=(j + 1) * 10,
                    state_data=state_data,
                    event_count=(j + 1) * 5,
                )

        stats = self.snapshot_store.get_stats()

        assert stats["total_snapshots"] == 6  # 1 + 2 + 3 = 6
        assert stats["total_workflows"] == 3
        assert stats["checksum_validation_enabled"] is True
        assert len(stats["workflows"]) == 3

        # Check workflow-specific stats
        workflow_1_stats = stats["workflows"]["workflow-1"]
        assert workflow_1_stats["snapshot_count"] == 1
        assert workflow_1_stats["latest_sequence"] == 10
        assert workflow_1_stats["latest_event_count"] == 5

    def test_workflow_id_listing(self):
        """Test listing workflow IDs."""
        workflows = ["workflow-a", "workflow-b", "workflow-c"]

        # Initially no workflows
        assert len(self.snapshot_store.get_workflow_ids()) == 0

        # Create snapshots
        for workflow_id in workflows:
            state_data = self.create_test_state(workflow_id)
            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=10,
                state_data=state_data,
                event_count=5,
            )

        # Should have all workflow IDs
        workflow_ids = self.snapshot_store.get_workflow_ids()
        assert len(workflow_ids) == 3
        assert set(workflow_ids) == set(workflows)

    # === Multiple Workflow Tests ===

    def test_multiple_workflow_isolation(self):
        """Test that workflows are properly isolated."""
        workflow_1 = "workflow-alpha"
        workflow_2 = "workflow-beta"

        # Create snapshots for both workflows
        for i in range(3):
            # Workflow 1
            state_1 = self.create_test_state(
                workflow_1, {"workflow": "alpha", "step": i}
            )
            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_1,
                sequence_number=(i + 1) * 10,
                state_data=state_1,
                event_count=(i + 1) * 5,
            )

            # Workflow 2
            state_2 = self.create_test_state(
                workflow_2, {"workflow": "beta", "step": i}
            )
            self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_2,
                sequence_number=(i + 1) * 10,
                state_data=state_2,
                event_count=(i + 1) * 7,
            )

        # Verify isolation
        snapshots_1 = self.snapshot_store.get_all_snapshots(workflow_1)
        snapshots_2 = self.snapshot_store.get_all_snapshots(workflow_2)

        assert len(snapshots_1) == 3
        assert len(snapshots_2) == 3

        # Verify content isolation
        for snapshot in snapshots_1:
            assert snapshot.state_data["workflow"] == "alpha"

        for snapshot in snapshots_2:
            assert snapshot.state_data["workflow"] == "beta"

    def test_concurrent_workflow_operations(self):
        """Test concurrent operations across multiple workflows."""
        workflows = [f"workflow-{i}" for i in range(5)]

        # Interleave snapshot creation across workflows
        total_snapshots = []
        for round_num in range(3):
            for workflow_id in workflows:
                state_data = self.create_test_state(
                    workflow_id, {"round": round_num, "workflow": workflow_id}
                )

                snapshot = self.snapshot_store.save_snapshot(
                    workflow_instance_id=workflow_id,
                    sequence_number=(round_num + 1) * 10,
                    state_data=state_data,
                    event_count=(round_num + 1) * 2,
                )
                total_snapshots.append(snapshot)

        # Verify all workflows have correct snapshots
        assert len(total_snapshots) == 15  # 5 workflows × 3 rounds

        for workflow_id in workflows:
            workflow_snapshots = self.snapshot_store.get_all_snapshots(workflow_id)
            assert len(workflow_snapshots) == 3

            # Verify ordering within workflow
            for i, snapshot in enumerate(workflow_snapshots):
                assert snapshot.sequence_number == (i + 1) * 10
                assert snapshot.state_data["round"] == i


class TestGlobalSnapshotStore:
    """Test global snapshot store instance management."""

    def test_global_instance_creation(self):
        """Test global snapshot store instance creation."""
        store1 = get_dev_snapshot_store()
        store2 = get_dev_snapshot_store()

        # Should return same instance
        assert store1 is store2
        assert isinstance(store1, InMemorySnapshotStore)

    def test_global_instance_functionality(self):
        """Test global instance basic functionality."""
        store = get_dev_snapshot_store()

        # Clear to clean state
        store.clear_all()

        # Test basic functionality
        workflow_id = "global-test-workflow"
        state_data = {"test": "global", "value": 123}

        snapshot = store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=10,
            state_data=state_data,
            event_count=5,
        )

        assert snapshot.state_data == state_data

        retrieved = store.get_latest_snapshot(workflow_id)
        assert retrieved == snapshot


class TestSnapshotStoreIntegration:
    """Integration tests for complex snapshot store scenarios."""

    def setup_method(self):
        """Setup for integration tests."""
        self.snapshot_store = InMemorySnapshotStore()

    def test_workflow_recovery_scenario(self):
        """Test workflow recovery scenario using snapshots."""
        workflow_id = "recovery-workflow-123"

        # Simulate workflow progression with periodic snapshots
        workflow_states = [
            {"step": "init", "progress": 0, "data": {"initialized": True}},
            {"step": "processing", "progress": 25, "data": {"items_processed": 100}},
            {"step": "validation", "progress": 50, "data": {"validation_passed": True}},
            {"step": "completion", "progress": 100, "data": {"result": "success"}},
        ]

        # Save snapshots at different sequence numbers
        sequence_numbers = [10, 25, 40, 60]
        event_counts = [5, 15, 30, 45]

        snapshots = []
        for i, (state, seq, events) in enumerate(
            zip(workflow_states, sequence_numbers, event_counts)
        ):
            snapshot = self.snapshot_store.save_snapshot(
                workflow_instance_id=workflow_id,
                sequence_number=seq,
                state_data=state,
                event_count=events,
                metadata={"checkpoint": i + 1},
            )
            snapshots.append(snapshot)

        # Simulate recovery from sequence 35 (should get snapshot at seq 25)
        recovery_snapshot = self.snapshot_store.get_snapshot_at_sequence(
            workflow_id, 35
        )

        assert recovery_snapshot is not None
        assert recovery_snapshot.sequence_number == 25
        assert recovery_snapshot.state_data["step"] == "processing"
        assert recovery_snapshot.state_data["progress"] == 25
        assert recovery_snapshot.event_count == 15

    def test_multi_workflow_recovery(self):
        """Test recovery scenario with multiple concurrent workflows."""
        workflows = {
            "order-001": {"customer": "alice", "amount": 100.0},
            "order-002": {"customer": "bob", "amount": 250.0},
            "order-003": {"customer": "charlie", "amount": 75.0},
        }

        # Each workflow progresses at different rates
        for workflow_id, initial_data in workflows.items():
            steps = ["received", "validated", "processed", "shipped"]

            for i, step in enumerate(steps):
                current_state = {
                    **initial_data,
                    "current_step": step,
                    "step_index": i,
                    "completed_at": f"2025-01-{i+1:02d}T10:00:00Z",
                }

                self.snapshot_store.save_snapshot(
                    workflow_instance_id=workflow_id,
                    sequence_number=(i + 1) * 10,
                    state_data=current_state,
                    event_count=(i + 1) * 3,
                )

        # Verify each workflow can be recovered independently
        for workflow_id in workflows:
            latest = self.snapshot_store.get_latest_snapshot(workflow_id)
            assert latest is not None
            assert latest.state_data["current_step"] == "shipped"
            assert latest.sequence_number == 40

            # Verify mid-point recovery
            mid_recovery = self.snapshot_store.get_snapshot_at_sequence(workflow_id, 25)
            assert mid_recovery.state_data["current_step"] == "validated"

    def test_snapshot_versioning_scenario(self):
        """Test snapshot versioning for schema evolution."""
        workflow_id = "versioned-workflow"

        # Version 1.0 schema
        v1_state = {
            "schema_version": "1.0",
            "workflow_data": {"name": "test", "value": 42},
            "metadata": {"created_by": "system"},
        }

        snapshot_v1 = self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=10,
            state_data=v1_state,
            event_count=5,
            metadata={"schema_version": "1.0"},
        )

        # Version 2.0 schema (extended)
        v2_state = {
            "schema_version": "2.0",
            "workflow_data": {
                "name": "test",
                "value": 42,
                "new_field": "added_in_v2",  # New field
            },
            "metadata": {
                "created_by": "system",
                "updated_by": "migration",  # New field
            },
            "extensions": {"feature_flags": ["new_feature"]},  # New section
        }

        snapshot_v2 = self.snapshot_store.save_snapshot(
            workflow_instance_id=workflow_id,
            sequence_number=20,
            state_data=v2_state,
            event_count=10,
            metadata={"schema_version": "2.0"},
        )

        # Verify both versions are stored correctly
        all_snapshots = self.snapshot_store.get_all_snapshots(workflow_id)
        assert len(all_snapshots) == 2

        assert all_snapshots[0].state_data["schema_version"] == "1.0"
        assert all_snapshots[1].state_data["schema_version"] == "2.0"

        # Latest should be v2
        latest = self.snapshot_store.get_latest_snapshot(workflow_id)
        assert latest.state_data["schema_version"] == "2.0"
        assert "extensions" in latest.state_data

        # Recovery to v1 timepoint should get v1 schema
        v1_recovery = self.snapshot_store.get_snapshot_at_sequence(workflow_id, 15)
        assert v1_recovery.state_data["schema_version"] == "1.0"
        assert "extensions" not in v1_recovery.state_data
