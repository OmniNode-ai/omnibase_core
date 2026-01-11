# SPDX-FileCopyrightText: 2025 OmniNode Team <info@omninode.ai>
#
# SPDX-License-Identifier: Apache-2.0
"""
ServiceAuditTrail - Service for tracking enforcement decisions.

This module provides the ServiceAuditTrail service for recording, querying,
and analyzing enforcement decisions made during replay execution.

Design:
    The audit trail service provides:
    - Recording of enforcement decisions with automatic sequencing
    - Query by session, outcome, source, and other criteria
    - Summary statistics computation
    - JSON export for debugging and compliance

Architecture:
    ::

        ServiceAuditTrail
            |
            +-- ModelAuditTrailEntry (storage)
            |
            +-- ModelAuditTrailSummary (computed)
            |
            +-- ModelEnforcementDecision (input)

Performance:
    The service maintains in-memory indices for common query patterns:

    - **Outcome index**: O(1) lookup + O(k) iteration for outcome-filtered queries
    - **Source index**: O(1) lookup + O(k) iteration for source-filtered queries

    Where k = number of matching entries.

    Without indices, queries would be O(n) where n = total entries.

    Expected Size Limits:
        - Typical usage: 10-100 decisions per session
        - Moderate usage: 100-1,000 decisions per session
        - Heavy usage: 1,000-10,000 decisions per session
        - Index overhead: ~48 bytes per entry (two dict references)

    Indexing Benefit:
        - < 100 entries: Marginal benefit (linear scan is fast)
        - 100-1,000 entries: Noticeable benefit for filtered queries
        - > 1,000 entries: Significant benefit (10-100x speedup)

    Indices are maintained incrementally on ``record()``, not rebuilt on query.

Thread Safety:
    ServiceAuditTrail instances are NOT thread-safe.

    **Mutable State**: ``_entries`` (list), ``_sequence_counter`` (int),
    ``_index_by_outcome`` (dict), ``_index_by_source`` (dict).

    **Recommended Patterns**:
        - Use separate instances per thread (preferred)
        - Or wrap ``record()`` and ``get_entries()`` calls with ``threading.Lock``

    See ``docs/guides/THREADING.md`` for comprehensive guidance.

Usage:
    .. code-block:: python

        from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail
        from omnibase_core.models.replay import ModelEnforcementDecision
        from omnibase_core.enums.replay import (
            EnumEffectDeterminism,
            EnumEnforcementMode,
            EnumNonDeterministicSource,
        )
        from datetime import datetime, timezone

        # Create audit trail
        audit_trail = ServiceAuditTrail()

        # Create a decision
        decision = ModelEnforcementDecision(
            effect_type="time.now",
            determinism=EnumEffectDeterminism.NON_DETERMINISTIC,
            source=EnumNonDeterministicSource.TIME,
            mode=EnumEnforcementMode.STRICT,
            decision="blocked",
            reason="Time effects blocked in strict mode",
            timestamp=datetime.now(timezone.utc),
        )

        # Record the decision
        entry = audit_trail.record(decision, context={"handler": "my_handler"})

        # Query entries
        blocked = audit_trail.get_entries(outcome="blocked")

        # Get summary
        summary = audit_trail.get_summary()
        print(f"Total: {summary.total_decisions}")

        # Export for debugging
        json_output = audit_trail.export_json()

Related:
    - OMN-1150: Replay Safety Enforcement
    - ProtocolAuditTrail: Protocol definition
    - ModelAuditTrailEntry: Entry model
    - ModelAuditTrailSummary: Summary model

.. versionadded:: 0.6.3
"""

from __future__ import annotations

__all__ = ["ServiceAuditTrail"]

import json
import uuid
from collections import defaultdict
from typing import TYPE_CHECKING
from uuid import UUID

from omnibase_core.models.replay.model_audit_trail_entry import ModelAuditTrailEntry
from omnibase_core.models.replay.model_audit_trail_summary import (
    ModelAuditTrailSummary,
)
from omnibase_core.protocols.replay.protocol_audit_trail import ProtocolAuditTrail
from omnibase_core.types.type_json import JsonType

if TYPE_CHECKING:
    from omnibase_core.enums.replay.enum_non_deterministic_source import (
        EnumNonDeterministicSource,
    )
    from omnibase_core.models.replay.model_enforcement_decision import (
        ModelEnforcementDecision,
    )


class ServiceAuditTrail:
    """
    Service for tracking and querying enforcement decisions.

    Provides in-memory storage and query capabilities for enforcement
    decisions made during replay execution.

    Args:
        session_id: Optional session identifier. If not provided, a new
            UUID will be generated.

    Attributes:
        session_id: The session identifier for this audit trail.

    Example:
        >>> from omnibase_core.services.replay.service_audit_trail import (
        ...     ServiceAuditTrail,
        ... )
        >>> audit_trail = ServiceAuditTrail(session_id="my-session")
        >>> audit_trail.session_id
        'my-session'

    Performance:
        Queries by outcome or source use O(1) index lookup + O(k) iteration
        where k = matching entries. See module docstring for details.

    Thread Safety:
        NOT thread-safe. Mutable state: ``_entries`` list, ``_sequence_counter``,
        ``_index_by_outcome``, ``_index_by_source``.
        Use separate instances per thread or synchronize access.
        See ``docs/guides/THREADING.md``.

    .. versionadded:: 0.6.3
    """

    def __init__(self, session_id: UUID | None = None) -> None:
        """
        Initialize the audit trail service.

        Args:
            session_id: Optional session identifier. If not provided,
                a new UUID will be generated.
        """
        self._session_id = session_id or uuid.uuid4()
        self._entries: list[ModelAuditTrailEntry] = []
        self._sequence_counter = 0

        # Indices for O(1) lookup by common query patterns
        # Key: outcome string (e.g., "blocked", "allowed", "mocked")
        # Value: list of entries with that outcome, in sequence order
        self._index_by_outcome: dict[str, list[ModelAuditTrailEntry]] = defaultdict(
            list
        )

        # Key: source enum value (or None for deterministic effects)
        # Value: list of entries with that source, in sequence order

        self._index_by_source: dict[
            EnumNonDeterministicSource | None, list[ModelAuditTrailEntry]
        ] = defaultdict(list)

    @property
    def session_id(self) -> UUID:
        """
        Get the current session identifier.

        Returns:
            UUID: The session ID for this audit trail instance.

        Example:
            >>> audit_trail = ServiceAuditTrail(session_id=UUID("..."))
            >>> audit_trail.session_id
            UUID('...')
        """
        return self._session_id

    def record(
        self,
        decision: ModelEnforcementDecision,
        context: dict[str, JsonType] | None = None,
    ) -> ModelAuditTrailEntry:
        """
        Record an enforcement decision.

        Creates a new audit trail entry with automatic ID and sequencing.
        Indices are updated incrementally for O(1) query performance.

        Args:
            decision: The enforcement decision to record.
            context: Optional additional context for debugging.

        Returns:
            ModelAuditTrailEntry: The created audit entry.

        Complexity:
            O(1) - Appends to list and updates two dict indices.

        Example:
            >>> entry = audit_trail.record(
            ...     decision=enforcement_decision,
            ...     context={"handler": "my_handler"},
            ... )
            >>> entry.sequence_number
            0
        """
        entry = ModelAuditTrailEntry(
            id=uuid.uuid4(),
            session_id=self._session_id,
            sequence_number=self._sequence_counter,
            decision=decision,
            context=context or {},
        )

        # Append to primary storage
        self._entries.append(entry)
        self._sequence_counter += 1

        # Update indices for O(1) query lookup
        self._index_by_outcome[decision.decision].append(entry)
        self._index_by_source[decision.source].append(entry)

        return entry

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

        Complexity:
            - No filters: O(n) copy of all entries
            - Outcome only: O(1) lookup + O(k) copy where k = matching entries
            - Source only: O(1) lookup + O(k) copy where k = matching entries
            - Both filters: O(1) lookup + O(min(k1, k2)) intersection

        Example:
            >>> blocked = audit_trail.get_entries(outcome="blocked")
            >>> time_decisions = audit_trail.get_entries(
            ...     source=EnumNonDeterministicSource.TIME,
            ...     limit=10,
            ... )
        """
        # Use indices for filtered queries (O(1) lookup + O(k) iteration)
        if outcome is not None and source is not None:
            # Both filters: use the smaller index and filter the other
            outcome_entries = self._index_by_outcome.get(outcome, [])
            source_entries = self._index_by_source.get(source, [])

            # Use smaller set as base, filter by other criterion
            if len(outcome_entries) <= len(source_entries):
                result = [e for e in outcome_entries if e.decision.source == source]
            else:
                result = [e for e in source_entries if e.decision.decision == outcome]

        elif outcome is not None:
            # Outcome filter only: O(1) lookup
            result = list(self._index_by_outcome.get(outcome, []))

        elif source is not None:
            # Source filter only: O(1) lookup
            result = list(self._index_by_source.get(source, []))

        else:
            # No filters: return all entries
            result = list(self._entries)

        # Apply limit
        if limit is not None:
            result = result[:limit]

        return result

    def get_summary(self) -> ModelAuditTrailSummary:
        """
        Get summary statistics for the current session.

        Computes aggregated statistics from all recorded entries.

        Returns:
            ModelAuditTrailSummary: Summary with counts and breakdowns.

        Example:
            >>> summary = audit_trail.get_summary()
            >>> summary.total_decisions
            5
        """
        if not self._entries:
            return ModelAuditTrailSummary(
                session_id=self._session_id,
                total_decisions=0,
                decisions_by_outcome={},
                decisions_by_source={},
                decisions_by_mode={},
                first_decision_at=None,
                last_decision_at=None,
                blocked_effects=[],
            )

        # Count by outcome
        decisions_by_outcome: dict[str, int] = defaultdict(int)
        for entry in self._entries:
            decisions_by_outcome[entry.decision.decision] += 1

        # Count by source
        decisions_by_source: dict[str, int] = defaultdict(int)
        for entry in self._entries:
            source = entry.decision.source
            source_key = source.value if source is not None else "unknown"
            decisions_by_source[source_key] += 1

        # Count by mode
        decisions_by_mode: dict[str, int] = defaultdict(int)
        for entry in self._entries:
            decisions_by_mode[entry.decision.mode.value] += 1

        # Time range
        first_decision_at = min(e.decision.timestamp for e in self._entries)
        last_decision_at = max(e.decision.timestamp for e in self._entries)

        # Blocked effects
        blocked_effects = sorted(
            {
                e.decision.effect_type
                for e in self._entries
                if e.decision.decision == "blocked"
            }
        )

        return ModelAuditTrailSummary(
            session_id=self._session_id,
            total_decisions=len(self._entries),
            decisions_by_outcome=dict(decisions_by_outcome),
            decisions_by_source=dict(decisions_by_source),
            decisions_by_mode=dict(decisions_by_mode),
            first_decision_at=first_decision_at,
            last_decision_at=last_decision_at,
            blocked_effects=blocked_effects,
        )

    def export_json(self) -> str:
        """
        Export audit trail as JSON for debugging.

        Serializes all entries and summary to a JSON string.

        Returns:
            str: JSON representation of the audit trail.

        Example:
            >>> json_output = audit_trail.export_json()
            >>> import json
            >>> data = json.loads(json_output)
            >>> "entries" in data
            True
        """
        summary = self.get_summary()

        export_data = {
            "session_id": self._session_id,
            "summary": summary.model_dump(mode="json"),
            "entries": [e.model_dump(mode="json") for e in self._entries],
        }

        return json.dumps(export_data, indent=2, default=str)

    def clear(self) -> None:
        """
        Clear all entries for the current session.

        Resets the entry list, sequence counter, and all indices.

        Example:
            >>> audit_trail.record(decision)
            >>> len(audit_trail.get_entries())
            1
            >>> audit_trail.clear()
            >>> len(audit_trail.get_entries())
            0
        """
        self._entries = []
        self._sequence_counter = 0
        self._index_by_outcome.clear()
        self._index_by_source.clear()

    @property
    def entry_count(self) -> int:
        """
        Get the number of recorded entries.

        Returns:
            int: Number of entries in the audit trail.

        Example:
            >>> audit_trail.entry_count
            0
            >>> audit_trail.record(decision)
            >>> audit_trail.entry_count
            1
        """
        return len(self._entries)


# Verify protocol compliance at module load time
_audit_trail_check: ProtocolAuditTrail = ServiceAuditTrail()
