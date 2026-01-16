"""
ONEX Execution Trace Models Module.

This module provides models for detailed execution traces, which form the
foundation of the replay infrastructure. Unlike manifests (which are summaries),
traces capture step-by-step timing and status for every operation.

Key Concepts:
    - **Trace**: Complete timeline of a single execution
    - **Step**: Individual unit of work within a trace

Relationship to Manifests:
    - Manifest = summary ("what happened" at high level)
    - Trace = detailed timeline ("exactly what happened and when")

Example:
    >>> from datetime import datetime, UTC
    >>> from uuid import uuid4
    >>> from omnibase_core.models.trace import (
    ...     ModelExecutionTrace,
    ...     ModelExecutionTraceStep,
    ... )
    >>> from omnibase_core.enums.enum_execution_status import EnumExecutionStatus
    >>>
    >>> step = ModelExecutionTraceStep(
    ...     step_id="step-001",
    ...     step_kind="handler",
    ...     name="handler_transform",
    ...     start_ts=datetime.now(UTC),
    ...     end_ts=datetime.now(UTC),
    ...     duration_ms=45.2,
    ...     status="success",
    ... )
    >>>
    >>> trace = ModelExecutionTrace(
    ...     correlation_id=uuid4(),
    ...     run_id=uuid4(),
    ...     started_at=datetime.now(UTC),
    ...     ended_at=datetime.now(UTC),
    ...     status=EnumExecutionStatus.SUCCESS,
    ...     steps=[step],
    ... )
    >>> trace.is_successful()
    True
    >>> trace.get_step_count()
    1

See Also:
    - :mod:`~omnibase_core.models.manifest`: High-level execution manifests
    - :class:`~omnibase_core.enums.enum_execution_status.EnumExecutionStatus`:
      Execution status values

.. versionadded:: 0.4.0
    Added as part of Execution Trace infrastructure (OMN-1208)
"""

from omnibase_core.models.trace.model_execution_trace import ModelExecutionTrace
from omnibase_core.models.trace.model_execution_trace_step import (
    ModelExecutionTraceStep,
)

__all__ = [
    # Trace Models
    "ModelExecutionTrace",
    "ModelExecutionTraceStep",
]
