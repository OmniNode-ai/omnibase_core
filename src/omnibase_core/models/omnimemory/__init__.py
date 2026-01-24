"""
OmniMemory Models Module.

This module provides models for OmniMemory - the agent memory and state
tracking system. It includes cost tracking, decision recording, failure
analysis, and unified memory snapshots.

Key Concepts:
    - **SubjectRef**: Typed reference for memory ownership (agent, user, workflow, etc.)
    - **CostEntry**: Individual billable operation with token counts and cost
    - **CostLedger**: Budget state machine with cost tracking and escalation
    - **DecisionRecord**: Record of agent decisions with context for replay
    - **FailureRecord**: Failures as first-class state for learning
    - **MemorySnapshot**: Unified state container ("state is the asset")
    - **MemoryDiff**: Diff between snapshots for change tracking

Example:
    >>> from datetime import datetime, UTC
    >>> from uuid import uuid4
    >>> from omnibase_core.models.omnimemory import (
    ...     ModelCostEntry,
    ...     ModelCostLedger,
    ...     ModelSubjectRef,
    ...     ModelMemorySnapshot,
    ... )
    >>> from omnibase_core.enums import EnumSubjectType
    >>>
    >>> # Create a subject reference
    >>> subject = ModelSubjectRef(
    ...     subject_type=EnumSubjectType.AGENT,
    ...     subject_id=uuid4(),
    ... )
    >>>
    >>> # Create a budget ledger
    >>> ledger = ModelCostLedger(budget_total=10.0)
    >>>
    >>> # Create a memory snapshot
    >>> snapshot = ModelMemorySnapshot(
    ...     subject=subject,
    ...     cost_ledger=ledger,
    ... )
    >>>
    >>> # Add a cost entry (returns new immutable instance)
    >>> entry = ModelCostEntry(
    ...     timestamp=datetime.now(UTC),
    ...     operation="chat_completion",
    ...     model_used="gpt-4",
    ...     tokens_in=100,
    ...     tokens_out=50,
    ...     cost=0.0045,
    ...     cumulative_total=0.0045,
    ... )
    >>> updated_snapshot = snapshot.with_cost_entry(entry)

.. versionadded:: 0.6.0
    Added cost tracking models (OMN-1239, OMN-1240)

.. versionadded:: 0.6.4
    Added subject ref, decision/failure records, snapshots, and diffs
    (OMN-1238, OMN-1241, OMN-1242, OMN-1243, OMN-1244, OMN-1245)
"""

from omnibase_core.models.omnimemory.model_claude_code_prompt_record import (
    ModelClaudeCodePromptRecord,
)
from omnibase_core.models.omnimemory.model_claude_code_session_snapshot import (
    ModelClaudeCodeSessionSnapshot,
)
from omnibase_core.models.omnimemory.model_claude_code_tool_record import (
    ModelClaudeCodeToolRecord,
)
from omnibase_core.models.omnimemory.model_cost_entry import ModelCostEntry
from omnibase_core.models.omnimemory.model_cost_ledger import ModelCostLedger
from omnibase_core.models.omnimemory.model_decision_record import ModelDecisionRecord
from omnibase_core.models.omnimemory.model_failure_record import ModelFailureRecord
from omnibase_core.models.omnimemory.model_memory_diff import ModelMemoryDiff
from omnibase_core.models.omnimemory.model_memory_snapshot import ModelMemorySnapshot
from omnibase_core.models.omnimemory.model_subject_ref import ModelSubjectRef

__all__ = [
    "ModelClaudeCodePromptRecord",
    "ModelClaudeCodeSessionSnapshot",
    "ModelClaudeCodeToolRecord",
    "ModelCostEntry",
    "ModelCostLedger",
    "ModelDecisionRecord",
    "ModelFailureRecord",
    "ModelMemoryDiff",
    "ModelMemorySnapshot",
    "ModelSubjectRef",
]
