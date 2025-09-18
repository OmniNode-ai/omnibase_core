"""
Reduction operation models for REDUCER nodes.

Provides strongly typed reduction operation specifications.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelReductionOperation(BaseModel):
    """Single reduction operation specification for REDUCER nodes."""

    model_config = ConfigDict(extra="forbid")

    operation_name: str = Field(
        ...,
        description="Name of the reduction operation",
    )
    operation_type: str = Field(
        ...,
        description="Type of reduction (aggregate, merge, transform, etc.)",
    )
    input_schema: str | None = Field(
        None,
        description="Input data schema specification",
    )
    output_schema: str | None = Field(
        None,
        description="Output data schema specification",
    )
    parameters: dict[str, str] | None = Field(
        None,
        description="Operation parameters with type specifications",
    )
    priority: int = Field(
        default=0,
        description="Operation priority (higher number = higher priority)",
    )
    condition: str | None = Field(
        None,
        description="Condition when this operation should be applied",
    )
    description: str | None = Field(
        None,
        description="Operation description",
    )
