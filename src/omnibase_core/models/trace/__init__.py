# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Execution Trace Models Module.

Models for detailed execution traces, which form the
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

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.trace.model_execution_trace import ModelExecutionTrace
    from omnibase_core.models.trace.model_execution_trace_step import (
        ModelExecutionTraceStep,
    )

__all__ = [
    # Trace Models
    "ModelExecutionTrace",
    "ModelExecutionTraceStep",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelExecutionTrace": (
        "omnibase_core.models.trace.model_execution_trace",
        "ModelExecutionTrace",
    ),
    "ModelExecutionTraceStep": (
        "omnibase_core.models.trace.model_execution_trace_step",
        "ModelExecutionTraceStep",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
