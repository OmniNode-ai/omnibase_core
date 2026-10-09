# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Execution Models Module.

The data models for the Runtime Execution Sequencing Model,
including phase steps, execution plans, and resolution metadata.

Models included:
    Core Models (OMN-1108):
        - ModelPhaseStep: A single phase step in the execution sequence
        - ModelExecutionPlan: A resolved execution plan with ordered phases

    Resolution Models (OMN-1106):
        - ModelPhaseEntry: A single handler's entry in a phase
        - ModelConstraintSatisfaction: Records constraint evaluation results
        - ModelResolutionMetadata: Metadata about the resolution process
        - ModelTieBreakerDecision: Records a tie-breaker decision
        - ModelExecutionConflict: Describes a conflict detected during resolution

Example:
    >>> from omnibase_core.models.execution import (
    ...     ModelPhaseStep,
    ...     ModelExecutionPlan,
    ...     ModelResolutionMetadata,
    ... )
    >>> from omnibase_core.enums import EnumHandlerExecutionPhase
    >>>
    >>> step = ModelPhaseStep(
    ...     phase=EnumHandlerExecutionPhase.EXECUTE,
    ...     handler_ids=["handler_a", "handler_b"]
    ... )
    >>> plan = ModelExecutionPlan(
    ...     phases=[step],
    ...     resolution_metadata=ModelResolutionMetadata(
    ...         strategy="topological_sort",
    ...         total_handlers_resolved=2,
    ...     ),
    ...     is_valid=True,
    ... )

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)

.. versionchanged:: 0.4.1
    Added resolution models (OMN-1106)
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.execution.model_constraint_satisfaction import (
        ModelConstraintSatisfaction,
    )
    from omnibase_core.models.execution.model_execution_conflict import (
        ModelExecutionConflict,
    )
    from omnibase_core.models.execution.model_execution_plan import ModelExecutionPlan
    from omnibase_core.models.execution.model_phase_entry import ModelPhaseEntry
    from omnibase_core.models.execution.model_phase_step import ModelPhaseStep
    from omnibase_core.models.execution.model_resolution_metadata import (
        ModelResolutionMetadata,
    )
    from omnibase_core.models.execution.model_tie_breaker_decision import (
        ModelTieBreakerDecision,
    )

__all__ = [
    # Core models (OMN-1108)
    "ModelPhaseStep",
    "ModelExecutionPlan",
    # Resolution models (OMN-1106)
    "ModelPhaseEntry",
    "ModelConstraintSatisfaction",
    "ModelResolutionMetadata",
    "ModelTieBreakerDecision",
    "ModelExecutionConflict",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelConstraintSatisfaction": (
        "omnibase_core.models.execution.model_constraint_satisfaction",
        "ModelConstraintSatisfaction",
    ),
    "ModelExecutionConflict": (
        "omnibase_core.models.execution.model_execution_conflict",
        "ModelExecutionConflict",
    ),
    "ModelExecutionPlan": (
        "omnibase_core.models.execution.model_execution_plan",
        "ModelExecutionPlan",
    ),
    "ModelPhaseEntry": (
        "omnibase_core.models.execution.model_phase_entry",
        "ModelPhaseEntry",
    ),
    "ModelPhaseStep": (
        "omnibase_core.models.execution.model_phase_step",
        "ModelPhaseStep",
    ),
    "ModelResolutionMetadata": (
        "omnibase_core.models.execution.model_resolution_metadata",
        "ModelResolutionMetadata",
    ),
    "ModelTieBreakerDecision": (
        "omnibase_core.models.execution.model_tie_breaker_decision",
        "ModelTieBreakerDecision",
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
