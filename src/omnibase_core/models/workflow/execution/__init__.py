# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Workflow Execution Models

Models for workflow execution internals and orchestration.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_declarative_workflow_result import ModelDeclarativeWorkflowResult
    from .model_declarative_workflow_step_context import (
        ModelDeclarativeWorkflowStepContext,
    )
    from .model_dependency_graph import ModelDependencyGraph
    from .model_workflow_execution_result import ModelWorkflowExecutionResult
    from .model_workflow_input_state import ModelWorkflowInputState
    from .model_workflow_result_metadata import ModelWorkflowResultMetadata
    from .model_workflow_state_snapshot import (
        CONTEXT_MAX_KEYS,
        CONTEXT_MAX_NESTING_DEPTH,
        CONTEXT_MAX_SIZE_BYTES,
        WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION,
        ModelWorkflowStateSnapshot,
    )
    from .model_workflow_step_execution import ModelWorkflowStepExecution

__all__ = [
    "CONTEXT_MAX_KEYS",
    "CONTEXT_MAX_NESTING_DEPTH",
    "CONTEXT_MAX_SIZE_BYTES",
    "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION",
    "ModelDeclarativeWorkflowResult",
    "ModelDeclarativeWorkflowStepContext",
    "ModelDependencyGraph",
    "ModelWorkflowExecutionResult",
    "ModelWorkflowInputState",
    "ModelWorkflowResultMetadata",
    "ModelWorkflowStateSnapshot",
    "ModelWorkflowStepExecution",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelDeclarativeWorkflowResult": (
        "omnibase_core.models.workflow.execution.model_declarative_workflow_result",
        "ModelDeclarativeWorkflowResult",
    ),
    "ModelDeclarativeWorkflowStepContext": (
        "omnibase_core.models.workflow.execution.model_declarative_workflow_step_context",
        "ModelDeclarativeWorkflowStepContext",
    ),
    "ModelDependencyGraph": (
        "omnibase_core.models.workflow.execution.model_dependency_graph",
        "ModelDependencyGraph",
    ),
    "ModelWorkflowExecutionResult": (
        "omnibase_core.models.workflow.execution.model_workflow_execution_result",
        "ModelWorkflowExecutionResult",
    ),
    "ModelWorkflowInputState": (
        "omnibase_core.models.workflow.execution.model_workflow_input_state",
        "ModelWorkflowInputState",
    ),
    "ModelWorkflowResultMetadata": (
        "omnibase_core.models.workflow.execution.model_workflow_result_metadata",
        "ModelWorkflowResultMetadata",
    ),
    "CONTEXT_MAX_KEYS": (
        "omnibase_core.models.workflow.execution.model_workflow_state_snapshot",
        "CONTEXT_MAX_KEYS",
    ),
    "CONTEXT_MAX_NESTING_DEPTH": (
        "omnibase_core.models.workflow.execution.model_workflow_state_snapshot",
        "CONTEXT_MAX_NESTING_DEPTH",
    ),
    "CONTEXT_MAX_SIZE_BYTES": (
        "omnibase_core.models.workflow.execution.model_workflow_state_snapshot",
        "CONTEXT_MAX_SIZE_BYTES",
    ),
    "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION": (
        "omnibase_core.models.workflow.execution.model_workflow_state_snapshot",
        "WORKFLOW_STATE_SNAPSHOT_SCHEMA_VERSION",
    ),
    "ModelWorkflowStateSnapshot": (
        "omnibase_core.models.workflow.execution.model_workflow_state_snapshot",
        "ModelWorkflowStateSnapshot",
    ),
    "ModelWorkflowStepExecution": (
        "omnibase_core.models.workflow.execution.model_workflow_step_execution",
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
