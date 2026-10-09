# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Workflow API Models

Models for workflow operations interface (CLI/API).
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_workflow_args import ModelWorkflowExecutionArgs
    from .model_workflow_list_result import ModelWorkflowListResult
    from .model_workflow_outputs import ModelWorkflowOutputs
    from .model_workflow_status_result import ModelWorkflowStatusResult
    from .model_workflow_stop_args import ModelWorkflowStopArgs

__all__ = [
    "ModelWorkflowExecutionArgs",
    "ModelWorkflowListResult",
    "ModelWorkflowOutputs",
    "ModelWorkflowStatusResult",
    "ModelWorkflowStopArgs",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelWorkflowExecutionArgs": (
        "omnibase_core.models.workflow.api.model_workflow_args",
        "ModelWorkflowExecutionArgs",
    ),
    "ModelWorkflowListResult": (
        "omnibase_core.models.workflow.api.model_workflow_list_result",
        "ModelWorkflowListResult",
    ),
    "ModelWorkflowOutputs": (
        "omnibase_core.models.workflow.api.model_workflow_outputs",
        "ModelWorkflowOutputs",
    ),
    "ModelWorkflowStatusResult": (
        "omnibase_core.models.workflow.api.model_workflow_status_result",
        "ModelWorkflowStatusResult",
    ),
    "ModelWorkflowStopArgs": (
        "omnibase_core.models.workflow.api.model_workflow_stop_args",
        "ModelWorkflowStopArgs",
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
