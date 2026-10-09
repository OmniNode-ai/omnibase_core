# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Workflow Models

Consolidated workflow models for ONEX framework.
Organized into API (external interface) and Execution (internal orchestration).
"""

from __future__ import annotations

# API Models - External interface for workflow operations
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .api import (
        ModelWorkflowExecutionArgs,
        ModelWorkflowListResult,
        ModelWorkflowOutputs,
        ModelWorkflowStatusResult,
        ModelWorkflowStopArgs,
    )

    # Execution Models - Internal workflow execution and orchestration
    from .execution import (
        WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION,
        ModelDependencyGraph,
        ModelWorkflowExecutionResult,
        ModelWorkflowInputState,
        ModelWorkflowStateSnapshot,
        ModelWorkflowStepExecution,
    )

__all__ = [
    # API Models
    "ModelWorkflowExecutionArgs",
    "ModelWorkflowListResult",
    "ModelWorkflowOutputs",
    "ModelWorkflowStatusResult",
    "ModelWorkflowStopArgs",
    # Execution Models
    "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION",
    "ModelDependencyGraph",
    "ModelWorkflowExecutionResult",
    "ModelWorkflowInputState",
    "ModelWorkflowStateSnapshot",
    "ModelWorkflowStepExecution",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelWorkflowExecutionArgs": (
        "omnibase_core.models.workflow.api",
        "ModelWorkflowExecutionArgs",
    ),
    "ModelWorkflowListResult": (
        "omnibase_core.models.workflow.api",
        "ModelWorkflowListResult",
    ),
    "ModelWorkflowOutputs": (
        "omnibase_core.models.workflow.api",
        "ModelWorkflowOutputs",
    ),
    "ModelWorkflowStatusResult": (
        "omnibase_core.models.workflow.api",
        "ModelWorkflowStatusResult",
    ),
    "ModelWorkflowStopArgs": (
        "omnibase_core.models.workflow.api",
        "ModelWorkflowStopArgs",
    ),
    "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION": (
        "omnibase_core.models.workflow.execution",
        "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION",
    ),
    "ModelDependencyGraph": (
        "omnibase_core.models.workflow.execution",
        "ModelDependencyGraph",
    ),
    "ModelWorkflowExecutionResult": (
        "omnibase_core.models.workflow.execution",
        "ModelWorkflowExecutionResult",
    ),
    "ModelWorkflowInputState": (
        "omnibase_core.models.workflow.execution",
        "ModelWorkflowInputState",
    ),
    "ModelWorkflowStateSnapshot": (
        "omnibase_core.models.workflow.execution",
        "ModelWorkflowStateSnapshot",
    ),
    "ModelWorkflowStepExecution": (
        "omnibase_core.models.workflow.execution",
        "ModelWorkflowStepExecution",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
