"""
Cycle Detection Result Model.

Result of cycle detection in workflow DAG validation.
"""

from uuid import UUID

from pydantic import BaseModel, Field

__all__ = ["ModelCycleDetectionResult"]


class ModelCycleDetectionResult(BaseModel):
    """Result of cycle detection in workflow DAG."""

    model_config = {"frozen": True}

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
