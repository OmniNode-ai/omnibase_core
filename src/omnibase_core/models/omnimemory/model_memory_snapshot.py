# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
ModelMemorySnapshot - Unified memory state container ('state is the asset').

Defines the ModelMemorySnapshot model which represents a complete snapshot of
memory state for a subject. This is the core "state is the asset" implementation
that holds all decisions, failures, costs, and context.

This model supports immutable lineage tracking through parent_snapshot_id and
provides content-based hashing for integrity verification.

This is a pure data model with immutable operations (all mutations return
new instances).

.. versionadded:: 0.6.0
    Added as part of OmniMemory core infrastructure (OMN-1243)
"""

import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.omnimemory.model_cost_entry import ModelCostEntry
from omnibase_core.models.omnimemory.model_cost_ledger import ModelCostLedger
from omnibase_core.models.omnimemory.model_decision_record import ModelDecisionRecord
from omnibase_core.models.omnimemory.model_failure_record import ModelFailureRecord
from omnibase_core.models.omnimemory.model_memory_diff import ModelMemoryDiff
from omnibase_core.models.omnimemory.model_subject_ref import ModelSubjectRef
from omnibase_core.types.type_json import JsonType


class ModelMemorySnapshot(BaseModel):
    """Unified memory state container - 'state is the asset'.

    Represents a complete snapshot of memory state for a subject, including
    all decisions made, failures encountered, costs incurred, and execution
    context. This is the central model for the OmniMemory system.

    Attributes:
        snapshot_id: Unique identifier for this snapshot (auto-generated).
        version: Snapshot version number for optimistic concurrency.
        parent_snapshot_id: Reference to parent snapshot for lineage tracking.
        corpus_id: Optional provenance link to a corpus of related snapshots.
        subject: Reference to the subject that owns this snapshot.
        decisions: Immutable tuple of decision records.
        failures: Immutable tuple of failure records.
        cost_ledger: Cost tracking ledger with budget state.
        execution_annotations: Additional execution metadata as JSON-compatible dict.
        schema_version: Schema version for serialization format tracking.
        content_hash: Hash computed from semantic fields for integrity verification.
        created_at: Timestamp when the snapshot was created.
        tags: Optional tags for categorization and filtering.

    Note:
        This model is frozen (immutable). All mutation methods return new
        instances rather than modifying in place. The content_hash is
        computed from semantic fields only, excluding identity and metadata
        fields to enable content-based comparison.

    Example:
        >>> from datetime import datetime, UTC
        >>> from uuid import uuid4
        >>> from omnibase_core.enums.enum_subject_type import EnumSubjectType
        >>> from omnibase_core.models.omnimemory import (
        ...     ModelCostLedger,
        ...     ModelMemorySnapshot,
        ...     ModelSubjectRef,
        ... )
        >>>
        >>> subject = ModelSubjectRef(
        ...     subject_type=EnumSubjectType.AGENT,
        ...     subject_id=uuid4(),
        ... )
        >>> ledger = ModelCostLedger(budget_total=100.0)
        >>> snapshot = ModelMemorySnapshot(subject=subject, cost_ledger=ledger)
        >>> snapshot.version
        1

    .. versionadded:: 0.6.0
        Added as part of OmniMemory core infrastructure (OMN-1243)
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    # === Identity ===

    snapshot_id: UUID = Field(
        default_factory=uuid4,
        description="Unique snapshot identifier",
    )

    version: int = Field(
        default=1,
        ge=1,
        description="Snapshot version number for optimistic concurrency",
    )

    # === Lineage ===

    parent_snapshot_id: UUID | None = Field(
        default=None,
        description="Parent snapshot ID for lineage tracking",
    )

    corpus_id: UUID | None = Field(
        default=None,
        description="Optional provenance link to corpus",
    )

    # === Ownership / Scope ===

    subject: ModelSubjectRef = Field(
        ...,
        description="Subject that owns this snapshot",
    )

    # === Core State (immutable tuples) ===

    decisions: tuple[ModelDecisionRecord, ...] = Field(
        default=(),
        description="Decision records",
    )

    failures: tuple[ModelFailureRecord, ...] = Field(
        default=(),
        description="Failure records",
    )

    cost_ledger: ModelCostLedger = Field(
        ...,
        description="Cost tracking ledger",
    )

    execution_annotations: dict[str, JsonType] = Field(
        default_factory=dict,
        description="Additional execution metadata",
    )

    # === Contract Shape ===

    schema_version: str = Field(
        default="1.0.0",
        description="Schema version for serialization format tracking",
    )

    content_hash: str = Field(
        default="",
        description="Hash computed from semantic fields",
    )

    # === Metadata ===

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When snapshot was created",
    )

    tags: tuple[str, ...] = Field(
        default=(),
        description="Optional tags for categorization",
    )

    # === Immutable Mutation Methods ===

    def with_decision(self, decision: ModelDecisionRecord) -> "ModelMemorySnapshot":
        """Add a decision and return a new snapshot instance.

        Creates a new ModelMemorySnapshot with the decision appended to the
        decisions tuple. The content_hash is recomputed for the new snapshot.

        Args:
            decision: The decision record to add.

        Returns:
            A new ModelMemorySnapshot instance with the decision added.

        Example:
            >>> # Assuming snapshot and decision are already created
            >>> new_snapshot = snapshot.with_decision(decision)
            >>> len(new_snapshot.decisions) == len(snapshot.decisions) + 1
            True

        .. versionadded:: 0.6.0
        """
        new_decisions = (*self.decisions, decision)
        return self._create_updated(decisions=new_decisions)

    def with_failure(self, failure: ModelFailureRecord) -> "ModelMemorySnapshot":
        """Add a failure and return a new snapshot instance.

        Creates a new ModelMemorySnapshot with the failure appended to the
        failures tuple. The content_hash is recomputed for the new snapshot.

        Args:
            failure: The failure record to add.

        Returns:
            A new ModelMemorySnapshot instance with the failure added.

        Example:
            >>> # Assuming snapshot and failure are already created
            >>> new_snapshot = snapshot.with_failure(failure)
            >>> len(new_snapshot.failures) == len(snapshot.failures) + 1
            True

        .. versionadded:: 0.6.0
        """
        new_failures = (*self.failures, failure)
        return self._create_updated(failures=new_failures)

    def with_cost_entry(self, entry: ModelCostEntry) -> "ModelMemorySnapshot":
        """Add a cost entry and return a new snapshot instance.

        Creates a new ModelMemorySnapshot with the cost entry added to the
        cost_ledger. The content_hash is recomputed for the new snapshot.

        Args:
            entry: The cost entry to add.

        Returns:
            A new ModelMemorySnapshot instance with the cost entry added.

        Example:
            >>> # Assuming snapshot and entry are already created
            >>> new_snapshot = snapshot.with_cost_entry(entry)
            >>> new_snapshot.cost_ledger.total_spent > snapshot.cost_ledger.total_spent
            True

        .. versionadded:: 0.6.0
        """
        new_ledger = self.cost_ledger.with_entry(entry)
        return self._create_updated(cost_ledger=new_ledger)

    def compute_content_hash(self) -> str:
        """Compute hash of semantic content.

        Computes a SHA-256 hash of the semantic content fields. This enables
        content-based comparison and integrity verification.

        Fields INCLUDED in hash:
            - decisions
            - failures
            - cost_ledger
            - execution_annotations
            - schema_version

        Fields EXCLUDED from hash (identity/metadata):
            - snapshot_id
            - version
            - parent_snapshot_id
            - corpus_id
            - subject
            - content_hash (self-referential)
            - created_at
            - tags

        Returns:
            SHA-256 hex digest of the semantic content.

        Example:
            >>> hash1 = snapshot.compute_content_hash()
            >>> # Same content produces same hash
            >>> hash2 = snapshot.compute_content_hash()
            >>> hash1 == hash2
            True

        .. versionadded:: 0.6.0
        """
        # Build canonical representation from semantic fields only
        content = {
            "decisions": [d.model_dump(mode="json") for d in self.decisions],
            "failures": [f.model_dump(mode="json") for f in self.failures],
            "cost_ledger": self.cost_ledger.model_dump(mode="json"),
            "execution_annotations": self.execution_annotations,
            "schema_version": self.schema_version,
        }
        # Use sort_keys for deterministic output, default=str for datetime/UUID
        canonical = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _create_updated(self, **kwargs: object) -> "ModelMemorySnapshot":
        """Create updated snapshot with new content hash.

        Internal helper that creates a new snapshot with the specified
        field updates and recomputes the content_hash.

        Args:
            **kwargs: Field updates to apply.

        Returns:
            A new ModelMemorySnapshot instance with updates applied.
        """
        # Use model_copy with update for efficiency (avoids full serialization)
        # First create without hash to compute it
        intermediate = self.model_copy(update={**kwargs, "content_hash": ""})
        # Compute hash and create final snapshot
        new_hash = intermediate.compute_content_hash()
        return intermediate.model_copy(update={"content_hash": new_hash})

    # === Utility Properties ===

    @property
    def decision_count(self) -> int:
        """Get the number of decisions in this snapshot.

        Returns:
            Number of decision records.
        """
        return len(self.decisions)

    @property
    def failure_count(self) -> int:
        """Get the number of failures in this snapshot.

        Returns:
            Number of failure records.
        """
        return len(self.failures)

    @property
    def has_parent(self) -> bool:
        """Check if this snapshot has a parent.

        Returns:
            True if parent_snapshot_id is set, False otherwise.
        """
        return self.parent_snapshot_id is not None

    # === Diff Methods ===

    def diff_from(self, other: "ModelMemorySnapshot") -> ModelMemoryDiff:
        """Compute diff from other snapshot to this one.

        Returns a diff showing what changed from 'other' (base) to 'self' (target).

        Args:
            other: The base snapshot to compare from.

        Returns:
            ModelMemoryDiff describing changes from other to self.

        Example:
            >>> # Assuming base_snapshot and target_snapshot are already created
            >>> diff = target_snapshot.diff_from(base_snapshot)
            >>> diff.has_changes
            True

        .. versionadded:: 0.6.0
            Added as part of OmniMemory diff infrastructure (OMN-1245)
        """
        # Find decisions added (in self but not in other)
        other_decision_ids = {d.decision_id for d in other.decisions}
        self_decision_ids = {d.decision_id for d in self.decisions}

        decisions_added = tuple(
            d for d in self.decisions if d.decision_id not in other_decision_ids
        )
        decisions_removed = tuple(
            d_id for d_id in other_decision_ids if d_id not in self_decision_ids
        )

        # Find failures added (failures are never removed - they're historical)
        other_failure_ids = {f.failure_id for f in other.failures}
        failures_added = tuple(
            f for f in self.failures if f.failure_id not in other_failure_ids
        )

        # Compute cost delta
        cost_delta = self.cost_ledger.total_spent - other.cost_ledger.total_spent

        # Generate summary
        summary_parts = []
        if decisions_added:
            summary_parts.append(f"{len(decisions_added)} decision(s) added")
        if decisions_removed:
            summary_parts.append(f"{len(decisions_removed)} decision(s) removed")
        if failures_added:
            summary_parts.append(f"{len(failures_added)} failure(s) recorded")
        if abs(cost_delta) > 1e-9:
            delta_str = (
                f"+${cost_delta:.4f}" if cost_delta > 0 else f"-${abs(cost_delta):.4f}"
            )
            summary_parts.append(f"cost {delta_str}")
        summary = "; ".join(summary_parts) if summary_parts else "No changes"

        return ModelMemoryDiff(
            base_snapshot_id=other.snapshot_id,
            target_snapshot_id=self.snapshot_id,
            decisions_added=decisions_added,
            decisions_removed=decisions_removed,
            failures_added=failures_added,
            cost_delta=cost_delta,
            summary=summary,
        )

    # === Utility Methods ===

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return (
            f"MemorySnapshot(v{self.version}: "
            f"decisions={self.decision_count}, "
            f"failures={self.failure_count}, "
            f"cost=${self.cost_ledger.total_spent:.2f})"
        )

    def __repr__(self) -> str:
        """Return a detailed string representation for debugging."""
        return (
            f"ModelMemorySnapshot(snapshot_id={self.snapshot_id!r}, "
            f"version={self.version!r}, "
            f"subject={self.subject!r}, "
            f"decision_count={self.decision_count}, "
            f"failure_count={self.failure_count}, "
            f"parent_snapshot_id={self.parent_snapshot_id!r})"
        )


# Export for use
__all__ = ["ModelMemorySnapshot"]
