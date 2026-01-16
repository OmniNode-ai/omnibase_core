"""
ProtocolAuditTrail - Protocol for enforcement decision audit trail.

This protocol defines the interface for tracking and querying enforcement
decisions made during replay execution.

Design:
    Uses dependency inversion - Core defines the interface, and implementations
    provide storage backends (in-memory, file, database) and query capabilities.

Architecture:
    Pipeline context receives an audit trail service via injection. During
    replay execution, the safety enforcer records each decision. After
    execution, the audit trail can be queried for analysis and debugging.

Usage:
    .. code-block:: python

        from omnibase_core.protocols.replay import ProtocolAuditTrail
        from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail

        # Create audit trail
        audit_trail: ProtocolAuditTrail = ServiceAuditTrail()

        # Record decisions
        entry = audit_trail.record(decision)

        # Query entries
        blocked_entries = audit_trail.get_entries(outcome="blocked")

        # Get summary
        summary = audit_trail.get_summary()

Related:
    - OMN-1150: Replay Safety Enforcement
    - ServiceAuditTrail: Default implementation
    - ModelAuditTrailEntry: Individual audit entries
    - ModelAuditTrailSummary: Aggregated statistics

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["ProtocolAuditTrail"]

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from omnibase_core.enums.replay.enum_non_deterministic_source import (
        EnumNonDeterministicSource,
    )
    from omnibase_core.models.replay.model_audit_trail_entry import ModelAuditTrailEntry
    from omnibase_core.models.replay.model_audit_trail_summary import (
        ModelAuditTrailSummary,
    )
    from omnibase_core.models.replay.model_enforcement_decision import (
        ModelEnforcementDecision,
    )
    from omnibase_core.types.type_json import JsonType


@runtime_checkable
class ProtocolAuditTrail(Protocol):
    """
    Protocol for enforcement decision audit trail.

    Defines the interface for recording, querying, and analyzing enforcement
    decisions made during replay execution.

    Implementations must support:
    - Recording individual enforcement decisions
    - Querying by outcome, source, and other criteria
    - Computing summary statistics
    - Exporting for debugging

    Thread Safety:
        Implementations should document their thread-safety guarantees.
        The default ServiceAuditTrail is NOT thread-safe.

    Example:
        .. code-block:: python

            from uuid import UUID, uuid4
            from omnibase_core.protocols.replay import ProtocolAuditTrail

            class DatabaseAuditTrail:
                '''Database-backed audit trail implementation.'''

                def __init__(self, session_id: UUID | None = None):
                    self._session_id = session_id or uuid4()
                    self._connection = get_database_connection()

                @property
                def session_id(self) -> UUID:
                    return self._session_id

                def record(
                    self,
                    decision: ModelEnforcementDecision,
                    context: dict[str, JsonType] | None = None,
                ) -> ModelAuditTrailEntry:
                    # Insert into database
                    ...

                def get_entries(
                    self,
                    outcome: str | None = None,
                    source: EnumNonDeterministicSource | None = None,
                    limit: int | None = None,
                ) -> list[ModelAuditTrailEntry]:
                    # Query database
                    ...

                def get_summary(self) -> ModelAuditTrailSummary:
                    # Compute aggregates
                    ...

                def export_json(self) -> str:
                    # Serialize all entries
                    ...

                def clear(self) -> None:
                    # Delete session entries
                    ...

            # Verify protocol compliance
            audit_trail: ProtocolAuditTrail = DatabaseAuditTrail()
            assert isinstance(audit_trail, ProtocolAuditTrail)

    .. versionadded:: 0.6.3
    """

    @property
    def session_id(self) -> UUID:
        """
        Get the current session identifier.

        Returns:
            UUID: The session ID for this audit trail instance.

        Example:
            .. code-block:: python

                audit_trail = ServiceAuditTrail(session_id=UUID("..."))
                print(audit_trail.session_id)  # UUID('...')
        """
        ...

    def record(
        self,
        decision: ModelEnforcementDecision,
        context: dict[str, JsonType] | None = None,
    ) -> ModelAuditTrailEntry:
        """
        Record an enforcement decision.

        Creates a new audit trail entry for the given decision with
        automatic sequencing within the session.

        Args:
            decision: The enforcement decision to record.
            context: Optional additional context for debugging.

        Returns:
            ModelAuditTrailEntry: The created audit entry with ID and sequence.

        Example:
            .. code-block:: python

                entry = audit_trail.record(
                    decision=enforcement_decision,
                    context={"handler": "my_handler"},
                )
                print(f"Recorded entry {entry.id} at sequence {entry.sequence_number}")
        """
        ...

    def get_entries(
        self,
        outcome: str | None = None,
        source: EnumNonDeterministicSource | None = None,
        limit: int | None = None,
    ) -> list[ModelAuditTrailEntry]:
        """
        Query entries with optional filters.

        Returns entries matching the specified criteria, ordered by
        sequence number.

        Args:
            outcome: Filter by decision outcome ("allowed", "blocked", etc.).
            source: Filter by non-determinism source.
            limit: Maximum number of entries to return.

        Returns:
            list[ModelAuditTrailEntry]: Matching entries in sequence order.

        Example:
            .. code-block:: python

                # Get all blocked decisions
                blocked = audit_trail.get_entries(outcome="blocked")

                # Get first 10 time-related decisions
                time_decisions = audit_trail.get_entries(
                    source=EnumNonDeterministicSource.TIME,
                    limit=10,
                )
        """
        ...

    def get_summary(self) -> ModelAuditTrailSummary:
        """
        Get summary statistics for the current session.

        Computes aggregated statistics from all recorded entries.

        Returns:
            ModelAuditTrailSummary: Summary with counts and breakdowns.

        Example:
            .. code-block:: python

                summary = audit_trail.get_summary()
                print(f"Total: {summary.total_decisions}")
                print(f"Blocked: {summary.decisions_by_outcome.get('blocked', 0)}")
        """
        ...

    def export_json(self) -> str:
        """
        Export audit trail as JSON for debugging.

        Serializes all entries and summary to a JSON string for
        logging, debugging, or external analysis.

        Returns:
            str: JSON representation of the audit trail.

        Example:
            .. code-block:: python

                json_output = audit_trail.export_json()
                with open("audit_trail.json", "w") as f:
                    f.write(json_output)
        """
        ...

    def clear(self) -> None:
        """
        Clear all entries for the current session.

        Removes all recorded entries. Useful for testing and
        session reset.

        Example:
            .. code-block:: python

                audit_trail.record(decision)
                assert len(audit_trail.get_entries()) > 0
                audit_trail.clear()
                assert len(audit_trail.get_entries()) == 0
        """
        ...
