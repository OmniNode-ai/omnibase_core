"""
Metadata for a single pipeline step execution.

Captures timing and type information for step observability.
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ModelComputeStepMetadata",
]


class ModelComputeStepMetadata(BaseModel):
    """
    Metadata for a single pipeline step execution.

    Attributes:
        duration_ms: Execution time for this step in milliseconds (must be >= 0).
        transformation_type: Optional type of transformation applied (for transformation steps).
    """

    duration_ms: float = Field(ge=0)
    transformation_type: str | None = None

    model_config = ConfigDict(frozen=True)
