"""
ONEX Execution Models Module.

This module provides the data models for the Runtime Execution Sequencing Model,
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
