"""
Step Type Enum.

Defines step types for workflow definitions.
"""

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper

__all__ = ["EnumStepType"]


@unique
class EnumStepType(StrValueHelper, str, Enum):
    """Step types for workflow definitions.

    Categorizes workflow steps by their execution semantics.
    The core four types (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR) align
    with the ONEX node architecture, while PARALLEL and CUSTOM
    provide additional workflow flexibility.

    Values:
        COMPUTE: Pure computation step with no side effects.
        EFFECT: Step that performs external I/O operations.
        REDUCER: Step that aggregates or reduces state.
        ORCHESTRATOR: Step that coordinates other steps.
        PARALLEL: Step that executes multiple sub-steps concurrently.
        CUSTOM: User-defined step type with custom semantics.
    """

    COMPUTE = "compute"
    """Pure computation step with no side effects."""

    EFFECT = "effect"
    """Step that performs external I/O operations."""

    REDUCER = "reducer"
    """Step that aggregates or reduces state."""

    ORCHESTRATOR = "orchestrator"
    """Step that coordinates other steps."""

    PARALLEL = "parallel"
    """Step that executes multiple sub-steps concurrently."""

    CUSTOM = "custom"
    """User-defined step type with custom semantics."""
