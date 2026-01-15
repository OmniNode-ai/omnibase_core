"""
Workflow Type Enum.

Strongly typed enumeration for workflow execution patterns.
Replaces string literals for workflow type discrimination.
"""

from __future__ import annotations

from enum import Enum, unique

from omnibase_core.utils.util_str_enum_base import StrValueHelper


@unique
class EnumWorkflowType(StrValueHelper, str, Enum):
    """
    Strongly typed workflow execution patterns.

    Used for workflow discrimination in orchestration scenarios.
    Inherits from str for JSON serialization compatibility while
    providing type safety and IDE support.
    """

    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOP = "loop"

    @classmethod
    def requires_branching(cls, workflow_type: EnumWorkflowType) -> bool:
        """Check if the workflow type requires branching logic."""
        return workflow_type in {cls.CONDITIONAL, cls.PARALLEL}

    @classmethod
    def supports_iteration(cls, workflow_type: EnumWorkflowType) -> bool:
        """Check if the workflow type supports iteration."""
        return workflow_type == cls.LOOP

    @classmethod
    def is_linear(cls, workflow_type: EnumWorkflowType) -> bool:
        """Check if the workflow type executes linearly."""
        return workflow_type == cls.SEQUENTIAL

    @classmethod
    def requires_synchronization(cls, workflow_type: EnumWorkflowType) -> bool:
        """Check if the workflow type requires synchronization points."""
        return workflow_type in {cls.PARALLEL, cls.LOOP}

    @classmethod
    def supports_parallelism(cls, workflow_type: EnumWorkflowType) -> bool:
        """Check if the workflow type supports parallel execution."""
        return workflow_type == cls.PARALLEL

    @classmethod
    def get_execution_description(cls, workflow_type: EnumWorkflowType) -> str:
        """Get a human-readable description of the workflow type."""
        descriptions = {
            cls.SEQUENTIAL: "Sequential execution of workflow steps",
            cls.PARALLEL: "Parallel execution with synchronization points",
            cls.CONDITIONAL: "Conditional branching based on runtime conditions",
            cls.LOOP: "Iterative execution with break conditions",
        }
        return descriptions.get(workflow_type, "Unknown workflow type")


# Export for use
__all__ = ["EnumWorkflowType"]
