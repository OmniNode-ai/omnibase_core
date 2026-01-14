"""
TypedDict for workflow execution context.

Provides type-safe structure for workflow context passed between steps.
"""

from __future__ import annotations

from typing import TypedDict


class TypedDictWorkflowContext(TypedDict):
    """
    TypedDict for workflow execution context.

    Used by _build_workflow_context to provide type-safe context
    for workflow step execution.

    Attributes:
        workflow_uuid_str: String representation of workflow UUID (for JSON serialization)
        completed_steps: List of completed step UUIDs as strings
        step_outputs: Dict mapping step UUID strings to their outputs
        step_count: Number of completed steps
    """

    workflow_uuid_str: str
    completed_steps: list[str]
    step_outputs: dict[str, object]
    step_count: int


__all__ = ["TypedDictWorkflowContext"]
