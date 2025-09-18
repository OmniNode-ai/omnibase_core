"""
I/O operation models for EFFECT nodes.

Provides strongly typed I/O operation specifications.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelIOOperation(BaseModel):
    """Single I/O operation specification for EFFECT nodes."""

    model_config = ConfigDict(extra="forbid")

    operation_type: str = Field(
        ...,
        description="Type of I/O operation (read, write, delete, etc.)",
    )
    resource_type: str = Field(
        ...,
        description="Type of resource (file, database, api, etc.)",
    )
    resource_path: str | None = Field(
        None,
        description="Path or identifier for the resource",
    )
    parameters: dict[str, str] | None = Field(
        None,
        description="Operation parameters",
    )
    timeout_ms: int | None = Field(
        None,
        description="Operation timeout in milliseconds",
        ge=0,
    )
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts",
        ge=0,
    )
    description: str | None = Field(
        None,
        description="Operation description",
    )
