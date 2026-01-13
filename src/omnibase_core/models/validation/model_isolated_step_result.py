"""
Isolated Step Result Model.

Result of isolated step detection in workflow DAG validation.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelIsolatedStepResult"]


class ModelIsolatedStepResult(BaseModel):
    """
    Result of isolated step detection in workflow DAG validation.

    This model captures steps that have no connections to other steps in the
    workflow graph. Isolated steps are problematic because they represent
    unreachable code that will never execute as part of the workflow.

    This model is immutable (frozen=True) after creation, making it safe
    for use as dictionary keys and in thread-safe contexts.

    Attributes:
        isolated_steps: UUIDs of steps that have no incoming or outgoing edges,
            allowing programmatic identification and resolution.
        isolated_step_names: Human-readable comma-separated list of isolated
            step names for logging and error messages.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    isolated_steps: list[UUID] = Field(
        default_factory=list,
        description="Step IDs that are isolated (no incoming or outgoing edges)",
    )
    isolated_step_names: str = Field(
        default="",
        description="Human-readable list of isolated step names",
    )
