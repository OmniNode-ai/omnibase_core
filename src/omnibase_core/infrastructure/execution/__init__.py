"""
ONEX Runtime Execution Sequencing Module.

This module provides the runtime execution sequencing model that consumes
merged contracts and produces execution plans.

The module contains:
- ModelPhaseStep: A single phase step in the execution sequence
- ModelExecutionPlan: A resolved execution plan derived from a merged contract
- Pure functions for creating and validating execution plans

Key Functions:
    - create_execution_plan: Main entry point for creating execution plans
    - create_empty_execution_plan: Create an empty execution plan
    - create_default_execution_plan: Create a plan with default settings
    - get_canonical_phase_order: Get the canonical phase ordering
    - validate_phase_list: Validate phase list integrity
    - group_handlers_by_phase: Group handlers by their execution phase
    - order_handlers_in_phase: Apply ordering policy to handlers

Example:
    >>> from omnibase_core.infrastructure.execution import (
    ...     ModelExecutionPlan,
    ...     ModelPhaseStep,
    ...     create_execution_plan,
    ... )
    >>> from omnibase_core.enums import EnumHandlerExecutionPhase
    >>> from omnibase_core.models.contracts import ModelExecutionProfile
    >>>
    >>> profile = ModelExecutionProfile()
    >>> mapping = {
    ...     "validate_handler": EnumHandlerExecutionPhase.PREFLIGHT,
    ...     "process_handler": EnumHandlerExecutionPhase.EXECUTE,
    ... }
    >>> plan = create_execution_plan(profile, mapping)
    >>> plan.total_handlers()
    2

.. versionadded:: 0.4.0
    Added as part of Runtime Execution Sequencing Model (OMN-1108)
"""

from omnibase_core.infrastructure.execution.infra_phase_sequencer import (
    create_default_execution_plan,
    create_empty_execution_plan,
    create_execution_plan,
    get_canonical_phase_order,
    get_phases_for_handlers,
    group_handlers_by_phase,
    order_handlers_in_phase,
    validate_phase_list,
    validate_phase_list_strict,
)
from omnibase_core.models.execution.model_execution_plan import ModelExecutionPlan
from omnibase_core.models.execution.model_phase_step import ModelPhaseStep

__all__ = [
    # Models
    "ModelPhaseStep",
    "ModelExecutionPlan",
    # Plan creation functions
    "create_execution_plan",
    "create_empty_execution_plan",
    "create_default_execution_plan",
    # Validation functions
    "validate_phase_list",
    "validate_phase_list_strict",
    # Utility functions
    "get_canonical_phase_order",
    "group_handlers_by_phase",
    "order_handlers_in_phase",
    "get_phases_for_handlers",
]
