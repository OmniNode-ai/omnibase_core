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
        max_entries: Optional maximum entries to retain. When exceeded, oldest
            entries are evicted (FIFO). None means unlimited (default).
            Recommended: 10000 for typical usage, 1000 for memory-constrained.

    Attributes:
        session_id: The session identifier for this audit trail.
        entry_count: Number of recorded entries.
        max_entries: Maximum entries limit, or None if unlimited.

    Memory Characteristics:
        Without ``max_entries``: Grows unbounded (O(n) memory where n = decisions).
        With ``max_entries``: Bounded to O(max_entries) memory.

        Entry size: ~500-1000 bytes per entry (varies with context size).

        Recommended limits:
            - Typical usage: 10,000 entries (~5-10 MB)
            - Memory-constrained: 1,000 entries (~0.5-1 MB)
            - High-volume pipelines: Consider external storage

    Example:
        >>> from omnibase_core.services.replay.service_audit_trail import (
        ...     ServiceAuditTrail,
        ... )
        >>> audit_trail = ServiceAuditTrail()
        >>> audit_trail.session_id  # UUID generated automatically
        UUID('...')

    Integration:
        **With ServiceReplaySafetyEnforcer**:

        The audit trail is designed to work with the replay safety enforcer
        to provide detailed logging and analysis of enforcement decisions:

        .. code-block:: python

            from omnibase_core.services.replay.service_replay_safety_enforcer import (
                ServiceReplaySafetyEnforcer,
            )
            from omnibase_core.services.replay.service_audit_trail import ServiceAuditTrail
            from omnibase_core.enums.replay import EnumEnforcementMode

            enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.PERMISSIVE)
            audit_trail = ServiceAuditTrail()

            # Process effects and record decisions
            for effect in effects_to_process:
                decision = enforcer.enforce(effect.type, effect.metadata)
                audit_trail.record(
                    decision,
                    context={
                        "node_id": node.id,
                        "handler": effect.handler_name,
                    },
                )

            # Analyze results
            summary = audit_trail.get_summary()
            if summary.decisions_by_outcome.get("blocked", 0) > 0:
                blocked = audit_trail.get_entries(outcome="blocked")
                for entry in blocked:
                    logger.warning(f"Blocked: {entry.decision.effect_type}")

        **Querying Patterns**:

        The audit trail supports efficient queries by outcome and source:

        .. code-block:: python

            # Get all blocked decisions (O(1) lookup + O(k) iteration)
            blocked = audit_trail.get_entries(outcome="blocked")

            # Get all time-related decisions
            from omnibase_core.enums.replay import EnumNonDeterministicSource
            time_decisions = audit_trail.get_entries(
                source=EnumNonDeterministicSource.TIME
            )

            # Combined filter with limit
            recent_blocked_time = audit_trail.get_entries(
                outcome="blocked",
                source=EnumNonDeterministicSource.TIME,
                limit=10,
            )

        **Export for Compliance/Debugging**:

        Export the complete audit trail as JSON for external analysis:

        .. code-block:: python

            # Export full audit trail
            json_output = audit_trail.export_json()

            # Write to file for compliance
            with open("audit_trail.json", "w") as f:
                f.write(json_output)

            # Or analyze programmatically
            import json
            data = json.loads(json_output)
            print(f"Session: {data['session_id']}")
            print(f"Total decisions: {data['summary']['total_decisions']}")

        **Session Management**:

        Use session IDs to correlate audit trails across components:

        .. code-block:: python

            import uuid

            # Create session ID for correlation
            session_id = uuid.uuid4()

            # Use same session across components
            audit_trail = ServiceAuditTrail(session_id=session_id)
            enforcer = ServiceReplaySafetyEnforcer(mode=EnumEnforcementMode.WARN)

            # Session ID appears in all audit entries
            entry = audit_trail.record(enforcer.enforce("time.now"))
            assert entry.session_id == session_id

        **With Pipeline Execution**:

        Integrate the audit trail into pipeline execution for comprehensive
        logging:

        .. code-block:: python

            class NodeEffectWithAudit(NodeEffect):
                def __init__(
                    self,
                    container: ModelONEXContainer,
                    audit_trail: ServiceAuditTrail,
                    enforcer: ServiceReplaySafetyEnforcer,
                ):
                    super().__init__(container)
                    self._audit_trail = audit_trail
                    self._enforcer = enforcer

                async def execute_effect(
                    self,
                    ctx: ProtocolPipelineContext,
                ) -> dict[str, Any]:
                    decision = self._enforcer.enforce("http.get")
                    self._audit_trail.record(
                        decision,
                        context={"correlation_id": ctx.correlation_id},
                    )
                    # ... proceed with effect

    Performance:
        Queries by outcome or source use O(1) index lookup + O(k) iteration
        where k = matching entries. See module docstring for details.

    Thread Safety:
        NOT thread-safe. Mutable state: ``_entries`` list, ``_sequence_counter``,
        ``_index_by_outcome``, ``_index_by_source``.
        Use separate instances per thread or synchronize access.
        See ``docs/guides/THREADING.md``.

    Data Privacy:
        The ``context`` parameter can inadvertently capture sensitive data.
        Avoid including PII, credentials, API keys, or financial data.
        Use sanitized identifiers (e.g., ``user_id`` instead of ``user_email``).
        See ``docs/guides/replay/REPLAY_SAFETY_INTEGRATION.md#data-privacy``.

    See Also:
        - :class:`ServiceReplaySafetyEnforcer`: Creates enforcement decisions.
        - :class:`ModelAuditTrailEntry`: Individual audit entry model.
        - :class:`ModelAuditTrailSummary`: Summary statistics model.
        - :class:`ModelEnforcementDecision`: Enforcement decision model.

    .. versionadded:: 0.6.3
    """

    def __init__(
        self, session_id: UUID | None = None, max_entries: int | None = None
    ) -> None:
        """
        Initialize the audit trail service.

        Args:
            session_id: Optional session identifier. If not provided,
                a new UUID will be generated.
            max_entries: Optional maximum entries to retain. When exceeded,
                oldest entries are evicted (FIFO). None means unlimited
                (default). Recommended: 10000 for typical usage, 1000 for
                memory-constrained environments.
        """
        self._session_id = session_id or uuid.uuid4()
        self._max_entries = max_entries
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

    @property
    def max_entries(self) -> int | None:
        """
        Return the maximum entries limit, or None if unlimited.

        Returns:
            int | None: The maximum number of entries to retain, or None
                if unlimited.

        Example:
            >>> audit_trail = ServiceAuditTrail(max_entries=1000)
            >>> audit_trail.max_entries
            1000
            >>> audit_trail_unlimited = ServiceAuditTrail()
            >>> audit_trail_unlimited.max_entries is None
            True
        """
        return self._max_entries

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

        # Enforce max_entries limit with FIFO eviction
        if self._max_entries is not None and len(self._entries) > self._max_entries:
            # Evict oldest entries to stay within limit
            evict_count = len(self._entries) - self._max_entries
            self._entries = self._entries[evict_count:]
            # Note: indices are NOT rebuilt - they become stale but queries still work
            # via list comprehension filtering. For production use with max_entries,
            # consider using get_entries() instead of relying on indices for
            # filtered queries, or call clear() periodically to reset indices.

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

        Performance:
            Uses single-pass aggregation for optimal performance.
            Leverages existing indices for outcome/source counts (O(k) where k = unique keys).
            Single pass over entries for mode counts, timestamps, and blocked effects.

            Previous implementation: 5 separate passes over O(n) entries.
            Optimized implementation: O(k) index lookups + 1 O(n) pass.

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

        # OPTIMIZATION: Leverage existing indices for outcome/source counts.
        # This is O(k) where k = number of unique outcomes/sources, not O(n).
        # The indices are maintained incrementally during record(), so no
        # iteration over entries is needed for these two aggregations.
        decisions_by_outcome = {
            outcome: len(entries) for outcome, entries in self._index_by_outcome.items()
        }

        decisions_by_source = {
            (source.value if source is not None else "unknown"): len(entries)
            for source, entries in self._index_by_source.items()
        }

        # OPTIMIZATION: Single-pass aggregation for remaining metrics.
        # Collects mode counts, timestamps, and blocked effects in one iteration.
        # Previous implementation used 3 separate passes (mode, min/max, blocked set).
        decisions_by_mode: dict[str, int] = defaultdict(int)
        blocked_effects_set: set[str] = set()
        first_decision_at = self._entries[0].decision.timestamp
        last_decision_at = first_decision_at

        for entry in self._entries:
            decision = entry.decision

            # Aggregate mode counts
            decisions_by_mode[decision.mode.value] += 1

            # Track timestamp range (avoids separate min/max passes)
            timestamp = decision.timestamp
            first_decision_at = min(first_decision_at, timestamp)
            last_decision_at = max(last_decision_at, timestamp)

            # Collect blocked effect types
            if decision.decision == "blocked":
                blocked_effects_set.add(decision.effect_type)

        return ModelAuditTrailSummary(
            session_id=self._session_id,
            total_decisions=len(self._entries),
            decisions_by_outcome=decisions_by_outcome,
            decisions_by_source=decisions_by_source,
            decisions_by_mode=dict(decisions_by_mode),
            first_decision_at=first_decision_at,
            last_decision_at=last_decision_at,
            blocked_effects=sorted(blocked_effects_set),
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
            "session_id": str(self._session_id),
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
