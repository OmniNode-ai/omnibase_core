"""
In-Memory Snapshot Store for Development and Testing.

⚠️  WARNING: DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

This implementation provides snapshot storage for development state checkpointing
and event sourcing workflow recovery testing.
"""

import logging
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.core.errors.core_errors import CoreErrorCode, OnexError

logger = logging.getLogger(__name__)


class WorkflowSnapshot(BaseModel):
    """Represents a workflow state snapshot."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    snapshot_id: UUID = Field(
        default_factory=uuid4, description="Unique snapshot identifier"
    )
    workflow_instance_id: str = Field(..., description="Workflow instance ID")
    sequence_number: int = Field(..., description="Last processed event sequence")
    state_data: dict[str, Any] = Field(..., description="Workflow state data")
    created_at: datetime = Field(
        default_factory=datetime.now, description="Snapshot timestamp"
    )
    event_count: int = Field(..., description="Number of events processed")
    checksum: str = Field(..., description="State data checksum")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def calculate_checksum(self) -> str:
        """Calculate checksum for state data."""
        import hashlib
        import json

        # Create deterministic JSON representation
        state_json = json.dumps(self.state_data, sort_keys=True, default=str)
        return hashlib.sha256(state_json.encode()).hexdigest()

    def validate_checksum(self) -> bool:
        """Validate stored checksum against current state."""
        return self.checksum == self.calculate_checksum()


class InMemorySnapshotStore:
    """
    ⚠️  DEV/TEST ONLY - In-Memory Snapshot Store ⚠️

    Provides snapshot storage for workflow state checkpointing with:
    - State versioning and rollback capabilities
    - Checksum validation for integrity
    - Configurable retention policies
    - Development state persistence
    """

    def __init__(self, **kwargs):
        """
        Initialize in-memory snapshot store.

        Args:
            **kwargs: Configuration options
        """
        logger.warning(
            "🚨 InMemorySnapshotStore: DEV/TEST ONLY - NEVER USE IN PRODUCTION 🚨"
        )

        # Snapshots organized by workflow instance ID
        self._snapshots: dict[str, list[WorkflowSnapshot]] = {}

        # Configuration
        self._max_snapshots_per_workflow = kwargs.get("max_snapshots_per_workflow", 10)
        self._enable_checksum_validation = kwargs.get(
            "enable_checksum_validation", True
        )

        logger.info("✅ InMemorySnapshotStore initialized for development/testing")

    def save_snapshot(
        self,
        workflow_instance_id: str,
        sequence_number: int,
        state_data: dict[str, Any],
        event_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowSnapshot:
        """
        Save a workflow state snapshot.

        Args:
            workflow_instance_id: Workflow instance identifier
            sequence_number: Last processed event sequence number
            state_data: Current workflow state data
            event_count: Number of events processed
            metadata: Optional additional metadata

        Returns:
            Created WorkflowSnapshot

        Raises:
            ValueError: If workflow_instance_id is empty or invalid parameters provided
        """
        # Enhanced error handling for edge cases
        if not workflow_instance_id or not workflow_instance_id.strip():
            raise OnexError(
                "workflow_instance_id cannot be empty or whitespace-only",
                CoreErrorCode.INVALID_PARAMETER,
                context={
                    "parameter": "workflow_instance_id",
                    "value": workflow_instance_id,
                },
            )

        if sequence_number < 0:
            raise OnexError(
                f"sequence_number must be non-negative, got {sequence_number}",
                CoreErrorCode.PARAMETER_OUT_OF_RANGE,
                context={
                    "parameter": "sequence_number",
                    "value": sequence_number,
                    "minimum": 0,
                },
            )

        if event_count < 0:
            raise OnexError(
                f"event_count must be non-negative, got {event_count}",
                CoreErrorCode.PARAMETER_OUT_OF_RANGE,
                context={
                    "parameter": "event_count",
                    "value": event_count,
                    "minimum": 0,
                },
            )

        if metadata is None:
            metadata = {}

        # Create snapshot
        snapshot = WorkflowSnapshot(
            workflow_instance_id=workflow_instance_id,
            sequence_number=sequence_number,
            state_data=state_data,
            event_count=event_count,
            metadata=metadata,
            checksum="",  # Will be calculated
        )

        # Calculate and set checksum
        snapshot.checksum = snapshot.calculate_checksum()

        # Initialize workflow snapshots list if needed
        if workflow_instance_id not in self._snapshots:
            self._snapshots[workflow_instance_id] = []

        snapshots = self._snapshots[workflow_instance_id]

        # Add new snapshot
        snapshots.append(snapshot)

        # Sort by sequence number to maintain order
        snapshots.sort(key=lambda s: s.sequence_number)

        # Enforce retention policy
        if len(snapshots) > self._max_snapshots_per_workflow:
            # Remove oldest snapshots
            excess = len(snapshots) - self._max_snapshots_per_workflow
            removed_snapshots = snapshots[:excess]
            snapshots[:] = snapshots[excess:]

            logger.info(
                f"Removed {excess} old snapshots for workflow {workflow_instance_id} "
                f"(retention policy: {self._max_snapshots_per_workflow})"
            )

        logger.debug(
            f"💾 Saved snapshot for workflow {workflow_instance_id} "
            f"(seq: {sequence_number}, events: {event_count})"
        )

        return snapshot

    def get_latest_snapshot(self, workflow_instance_id: str) -> WorkflowSnapshot | None:
        """
        Get the latest snapshot for a workflow.

        Args:
            workflow_instance_id: Workflow instance identifier

        Returns:
            Latest WorkflowSnapshot or None if not found

        Raises:
            ValueError: If workflow_instance_id is empty
        """
        # Enhanced error handling for edge cases
        if not workflow_instance_id or not workflow_instance_id.strip():
            raise OnexError(
                "workflow_instance_id cannot be empty or whitespace-only",
                CoreErrorCode.INVALID_PARAMETER,
                context={
                    "parameter": "workflow_instance_id",
                    "value": workflow_instance_id,
                },
            )

        if workflow_instance_id not in self._snapshots:
            return None

        snapshots = self._snapshots[workflow_instance_id]
        if not snapshots:
            return None

        latest = snapshots[-1]  # Last in sorted list

        # Validate checksum if enabled
        if self._enable_checksum_validation and not latest.validate_checksum():
            logger.error(
                f"Checksum validation failed for latest snapshot of workflow {workflow_instance_id}"
            )
            raise OnexError(
                f"Snapshot corruption detected for workflow {workflow_instance_id}",
                CoreErrorCode.VALIDATION_ERROR,
                context={
                    "workflow_instance_id": workflow_instance_id,
                    "validation_type": "checksum",
                },
            )

        return latest

    def get_snapshot_at_sequence(
        self, workflow_instance_id: str, sequence_number: int
    ) -> WorkflowSnapshot | None:
        """
        Get snapshot at or before a specific sequence number.

        Args:
            workflow_instance_id: Workflow instance identifier
            sequence_number: Target sequence number

        Returns:
            WorkflowSnapshot at or before sequence number, or None

        Raises:
            ValueError: If workflow_instance_id is empty or sequence_number is negative
        """
        # Enhanced error handling for edge cases
        if not workflow_instance_id or not workflow_instance_id.strip():
            raise OnexError(
                "workflow_instance_id cannot be empty or whitespace-only",
                CoreErrorCode.INVALID_PARAMETER,
                context={
                    "parameter": "workflow_instance_id",
                    "value": workflow_instance_id,
                },
            )

        if sequence_number < 0:
            raise OnexError(
                f"sequence_number must be non-negative, got {sequence_number}",
                CoreErrorCode.PARAMETER_OUT_OF_RANGE,
                context={
                    "parameter": "sequence_number",
                    "value": sequence_number,
                    "minimum": 0,
                },
            )

        if workflow_instance_id not in self._snapshots:
            return None

        snapshots = self._snapshots[workflow_instance_id]

        # Find snapshot at or before the sequence number
        best_snapshot = None
        for snapshot in reversed(snapshots):  # Start from latest
            if snapshot.sequence_number <= sequence_number:
                best_snapshot = snapshot
                break

        if best_snapshot and self._enable_checksum_validation:
            if not best_snapshot.validate_checksum():
                logger.error(
                    f"Checksum validation failed for snapshot {best_snapshot.snapshot_id}"
                )
                raise OnexError(
                    f"Snapshot corruption detected: {best_snapshot.snapshot_id}",
                    CoreErrorCode.VALIDATION_ERROR,
                    context={
                        "snapshot_id": str(best_snapshot.snapshot_id),
                        "validation_type": "checksum",
                    },
                )

        return best_snapshot

    def get_all_snapshots(self, workflow_instance_id: str) -> list[WorkflowSnapshot]:
        """
        Get all snapshots for a workflow in chronological order.

        Args:
            workflow_instance_id: Workflow instance identifier

        Returns:
            List of WorkflowSnapshot objects
        """
        if workflow_instance_id not in self._snapshots:
            return []

        snapshots = self._snapshots[workflow_instance_id].copy()

        # Validate checksums if enabled
        if self._enable_checksum_validation:
            for snapshot in snapshots:
                if not snapshot.validate_checksum():
                    logger.error(
                        f"Checksum validation failed for snapshot {snapshot.snapshot_id}"
                    )
                    raise OnexError(
                        f"Snapshot corruption detected: {snapshot.snapshot_id}",
                        CoreErrorCode.VALIDATION_ERROR,
                        context={
                            "snapshot_id": str(snapshot.snapshot_id),
                            "validation_type": "checksum",
                        },
                    )

        return snapshots

    def delete_snapshots(self, workflow_instance_id: str) -> int:
        """
        Delete all snapshots for a workflow.

        Args:
            workflow_instance_id: Workflow instance identifier

        Returns:
            Number of snapshots deleted

        Raises:
            ValueError: If workflow_instance_id is empty
        """
        # Enhanced error handling for edge cases
        if not workflow_instance_id or not workflow_instance_id.strip():
            raise OnexError(
                "workflow_instance_id cannot be empty or whitespace-only",
                CoreErrorCode.INVALID_PARAMETER,
                context={
                    "parameter": "workflow_instance_id",
                    "value": workflow_instance_id,
                },
            )

        if workflow_instance_id not in self._snapshots:
            return 0

        count = len(self._snapshots[workflow_instance_id])
        del self._snapshots[workflow_instance_id]

        logger.info(f"🗑️  Deleted {count} snapshots for workflow {workflow_instance_id}")
        return count

    def delete_old_snapshots(
        self, workflow_instance_id: str, keep_latest: int = 3
    ) -> int:
        """
        Delete old snapshots, keeping only the latest N snapshots.

        Args:
            workflow_instance_id: Workflow instance identifier
            keep_latest: Number of latest snapshots to keep

        Returns:
            Number of snapshots deleted
        """
        if workflow_instance_id not in self._snapshots:
            return 0

        snapshots = self._snapshots[workflow_instance_id]

        if len(snapshots) <= keep_latest:
            return 0

        # Keep only the latest snapshots
        to_delete = len(snapshots) - keep_latest
        del snapshots[:to_delete]

        logger.info(
            f"🗑️  Deleted {to_delete} old snapshots for workflow {workflow_instance_id} "
            f"(kept latest {keep_latest})"
        )

        return to_delete

    def get_workflow_ids(self) -> list[str]:
        """Get list of all workflow instance IDs with snapshots."""
        return list(self._snapshots.keys())

    def get_stats(self) -> dict[str, Any]:
        """Get snapshot store statistics."""
        total_snapshots = sum(len(snapshots) for snapshots in self._snapshots.values())

        workflow_stats = {}
        for workflow_id, snapshots in self._snapshots.items():
            if snapshots:
                workflow_stats[workflow_id] = {
                    "snapshot_count": len(snapshots),
                    "earliest_sequence": snapshots[0].sequence_number,
                    "latest_sequence": snapshots[-1].sequence_number,
                    "latest_event_count": snapshots[-1].event_count,
                    "created_at": snapshots[0].created_at.isoformat(),
                    "updated_at": snapshots[-1].created_at.isoformat(),
                }

        return {
            "total_snapshots": total_snapshots,
            "total_workflows": len(self._snapshots),
            "max_snapshots_per_workflow": self._max_snapshots_per_workflow,
            "checksum_validation_enabled": self._enable_checksum_validation,
            "workflows": workflow_stats,
        }

    def clear_all(self) -> None:
        """Clear all snapshots."""
        total = sum(len(snapshots) for snapshots in self._snapshots.values())
        self._snapshots.clear()

        logger.info(f"🗑️  Cleared all {total} snapshots from snapshot store")

    # === Development/Testing Utilities ===

    def validate_all_checksums(self) -> dict[str, bool]:
        """
        Validate checksums for all snapshots.

        Returns:
            Dict mapping snapshot IDs to validation results
        """
        results = {}

        for workflow_id, snapshots in self._snapshots.items():
            for snapshot in snapshots:
                snapshot_id = str(snapshot.snapshot_id)
                try:
                    results[snapshot_id] = snapshot.validate_checksum()
                    if not results[snapshot_id]:
                        logger.warning(f"Checksum validation failed: {snapshot_id}")
                except Exception as e:
                    logger.error(f"Error validating snapshot {snapshot_id}: {e}")
                    results[snapshot_id] = False

        return results

    def simulate_corruption(self, workflow_instance_id: str) -> bool:
        """
        Simulate snapshot corruption for testing.

        Args:
            workflow_instance_id: Workflow to corrupt snapshot for

        Returns:
            True if corruption was simulated
        """
        if workflow_instance_id not in self._snapshots:
            return False

        snapshots = self._snapshots[workflow_instance_id]
        if not snapshots:
            return False

        # Corrupt the latest snapshot by changing its checksum
        latest = snapshots[-1]
        original_checksum = latest.checksum
        latest.checksum = "corrupted_checksum_for_testing"

        logger.warning(
            f"🧪 Simulated corruption for snapshot {latest.snapshot_id} "
            f"(was: {original_checksum[:8]}..., now: corrupted)"
        )

        return True

    # === Context Manager Support ===

    def __enter__(self) -> "InMemorySnapshotStore":
        """Enter synchronous context manager."""
        logger.debug("📥 Entered InMemorySnapshotStore context manager")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit synchronous context manager with cleanup."""
        try:
            self._snapshots.clear()
            logger.info("🧹 InMemorySnapshotStore context manager cleanup complete")
        except Exception as e:
            logger.error(f"Error during context manager cleanup: {e}")


# Global instance for development/testing
_global_dev_snapshot_store: InMemorySnapshotStore | None = None


def get_dev_snapshot_store() -> InMemorySnapshotStore:
    """
    Get or create the global development snapshot store instance.

    ⚠️  DEV/TEST ONLY - NEVER USE IN PRODUCTION ⚠️

    Returns:
        InMemorySnapshotStore instance
    """
    global _global_dev_snapshot_store
    if _global_dev_snapshot_store is None:
        _global_dev_snapshot_store = InMemorySnapshotStore()
        logger.info("✅ Created global development snapshot store")
    return _global_dev_snapshot_store
