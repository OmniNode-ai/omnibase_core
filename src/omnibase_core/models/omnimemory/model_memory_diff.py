"""
ModelMemoryDiff - Diff between two memory snapshots.

Defines the ModelMemoryDiff model which represents the differences between
two memory snapshots. Enables understanding what changed between executions,
including decisions added/removed, failures added, and cost changes.

This is a pure data model with no side effects.

.. versionadded:: 0.6.0
    Added as part of OmniMemory diff infrastructure (OMN-1244)
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants.constants_omnimemory import FLOAT_COMPARISON_EPSILON
from omnibase_core.models.omnimemory.model_decision_record import ModelDecisionRecord
from omnibase_core.models.omnimemory.model_failure_record import ModelFailureRecord


class ModelMemoryDiff(BaseModel):
    """Diff between two memory snapshots.

    Represents the differences between a base (older) snapshot and a
    target (newer) snapshot, tracking decision additions/removals,
    failure additions, and cost delta.

    Attributes:
        diff_id: Unique identifier for this diff (auto-generated).
        base_snapshot_id: ID of the base (older) snapshot.
        target_snapshot_id: ID of the target (newer) snapshot.
        decisions_added: Decisions added in target snapshot.
        decisions_removed: IDs of decisions removed from base snapshot.
        failures_added: Failures added in target snapshot.
        cost_delta: Change in total cost (target - base).
        summary: Human-readable summary of changes.
        computed_at: When the diff was computed.

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import uuid4
        >>> diff = ModelMemoryDiff(
        ...     base_snapshot_id=uuid4(),
        ...     target_snapshot_id=uuid4(),
        ...     cost_delta=0.05,
        ...     summary="Added 2 decisions, 1 failure",
        ... )
        >>> diff.has_changes
        True

    .. versionadded:: 0.6.0
        Added as part of OmniMemory diff infrastructure (OMN-1244)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Identity ===

    diff_id: UUID = Field(
        default_factory=uuid4,
        description="Unique diff identifier",
    )

    base_snapshot_id: UUID = Field(
        ...,
        description="ID of the base (older) snapshot",
    )

    target_snapshot_id: UUID = Field(
        ...,
        description="ID of the target (newer) snapshot",
    )

    # === Decision Changes ===

    decisions_added: tuple[ModelDecisionRecord, ...] = Field(
        default=(),
        description="Decisions added in target snapshot",
    )

    decisions_removed: tuple[UUID, ...] = Field(
        default=(),
        description="IDs of decisions removed from base snapshot",
    )

    # === Failure Changes ===

    failures_added: tuple[ModelFailureRecord, ...] = Field(
        default=(),
        description="Failures added in target snapshot",
    )

    # === Cost Delta ===

    cost_delta: float = Field(
        default=0.0,
        description="Change in total cost (target - base)",
    )

    # === Summary ===

    summary: str = Field(
        default="",
        description="Human-readable summary of changes",
    )

    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When the diff was computed",
    )

    # === Validators ===

    @model_validator(mode="after")
    def validate_different_snapshots(self) -> "ModelMemoryDiff":
        """Ensure base_snapshot_id != target_snapshot_id.

        A diff comparing a snapshot to itself is meaningless.

        Returns:
            The validated model instance.

        Raises:
            ValueError: If base and target snapshot IDs are the same.
        """
        if self.base_snapshot_id == self.target_snapshot_id:
            raise ValueError(
                f"base_snapshot_id and target_snapshot_id must be different. "
                f"Cannot diff a snapshot against itself. Got: {self.base_snapshot_id}"
            )
        return self

    # === Utility Properties ===

    @property
    def has_changes(self) -> bool:
        """Check if any changes exist between snapshots.

        Returns:
            True if any decisions were added/removed, any failures
            were added, or cost_delta is non-zero.
        """
        return bool(
            self.decisions_added
            or self.decisions_removed
            or self.failures_added
            or abs(self.cost_delta) > FLOAT_COMPARISON_EPSILON
        )

    @property
    def decision_change_count(self) -> int:
        """Get total number of decision changes.

        Returns:
            Sum of decisions added and decisions removed.
        """
        return len(self.decisions_added) + len(self.decisions_removed)

    @property
    def failure_change_count(self) -> int:
        """Get total number of failure changes.

        Note: Failures are only ever added, never removed
        (failures are historical records).

        Returns:
            Number of failures added.
        """
        return len(self.failures_added)

    # === Utility Methods ===

    def __str__(self) -> str:
        changes = []
        if self.decisions_added:
            changes.append(f"+{len(self.decisions_added)} decisions")
        if self.decisions_removed:
            changes.append(f"-{len(self.decisions_removed)} decisions")
        if self.failures_added:
            changes.append(f"+{len(self.failures_added)} failures")
        if abs(self.cost_delta) > FLOAT_COMPARISON_EPSILON:
            if self.cost_delta > 0:
                changes.append(f"+${self.cost_delta:.4f} cost")
            else:
                changes.append(f"-${abs(self.cost_delta):.4f} cost")

        if changes:
            return f"MemoryDiff({', '.join(changes)})"
        return "MemoryDiff(no changes)"

    def __repr__(self) -> str:
        return (
            f"ModelMemoryDiff(diff_id={self.diff_id!r}, "
            f"base_snapshot_id={self.base_snapshot_id!r}, "
            f"target_snapshot_id={self.target_snapshot_id!r}, "
            f"decision_change_count={self.decision_change_count}, "
            f"failure_change_count={self.failure_change_count}, "
            f"cost_delta={self.cost_delta!r})"
        )


# Export for use
__all__ = ["ModelMemoryDiff"]
