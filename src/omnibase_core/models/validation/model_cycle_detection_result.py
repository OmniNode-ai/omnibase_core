"""
Cycle Detection Result Model.

Result of cycle detection in workflow DAG validation.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelCycleDetectionResult"]


class ModelCycleDetectionResult(BaseModel):
    """
    Result of cycle detection in workflow DAG validation.

    This model captures the outcome of checking a workflow DAG for circular
    dependencies. Cycles in workflows are invalid because they create infinite
    execution loops where steps depend on each other in a closed chain.

    This model is immutable (frozen=True) after creation, making it safe
    for use as dictionary keys and in thread-safe contexts.

    Attributes:
        has_cycle: Whether a cycle was detected in the workflow.
        cycle_description: Human-readable description of the detected cycle,
            including the names of steps involved.
        cycle_step_ids: UUIDs of the steps that form the cycle, allowing
            programmatic identification and resolution.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    has_cycle: bool = Field(
        default=False,
        description="Whether a cycle was detected in the workflow",
    )
    cycle_description: str = Field(
        default="",
        description="Human-readable description of the cycle including step names",
    )
    cycle_step_ids: list[UUID] = Field(
        default_factory=list,
        description="Step IDs involved in the cycle",
    )
