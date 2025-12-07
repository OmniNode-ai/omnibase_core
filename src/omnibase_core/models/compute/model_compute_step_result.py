"""
Result of a single pipeline step.

Captures the output, success status, and any error information.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from omnibase_core.models.compute.model_compute_step_metadata import (
        ModelComputeStepMetadata,
    )

__all__ = [
    "ModelComputeStepResult",
]


class ModelComputeStepResult(BaseModel):
    """
    Result of a single pipeline step.

    Attributes:
        step_name: Name of the step that produced this result.
        output: The output data from this step.
        success: Whether the step completed successfully.
        metadata: Execution metadata (timing, transformation type).
        error_type: v1.0 uses simple string for error type (not enum).
        error_message: Human-readable error message if step failed.
    """

    step_name: str
    output: Any
    success: bool = True
    metadata: "ModelComputeStepMetadata"
    error_type: str | None = None  # v1.0: Simple string, not enum
    error_message: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


# Import at runtime for forward ref resolution
from omnibase_core.models.compute.model_compute_step_metadata import (  # noqa: E402
    ModelComputeStepMetadata,
)

ModelComputeStepResult.model_rebuild()
