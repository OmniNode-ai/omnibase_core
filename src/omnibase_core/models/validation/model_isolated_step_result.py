"""
Isolated Step Result Model.

Result of isolated step detection in workflow DAG validation.
"""

from uuid import UUID

from pydantic import BaseModel, Field

__all__ = ["ModelIsolatedStepResult"]


class ModelIsolatedStepResult(BaseModel):
    """Result of isolated step detection."""

    model_config = {"frozen": True}

    isolated_steps: list[UUID] = Field(
        default_factory=list,
        description="Step IDs that are isolated (no incoming or outgoing edges)",
    )
    isolated_step_names: str = Field(
        default="",
        description="Human-readable list of isolated step names",
    )
