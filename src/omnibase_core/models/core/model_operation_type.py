"""
Operation Type Model.

Extensible operation type model that replaces string literals with
rich metadata for operation tracking and categorization.
"""

from pydantic import BaseModel, Field


class ModelOperationType(BaseModel):
    """
    Extensible operation type model.

    Replaces string literals with rich operation metadata that can be
    extended by plugins and third-party systems.
    """

    operation_name: str = Field(
        default=...,
        description="Operation identifier",
        pattern="^[a-z][a-z0-9_]*$",
    )
    category: str = Field(
        default=...,
        description="Operation category",
        pattern="^[a-z][a-z0-9_]*$",
    )
    description: str = Field(
        default=..., description="Human-readable operation description"
    )
    is_read_only: bool = Field(
        default=True,
        description="Whether operation modifies state",
    )
    is_idempotent: bool = Field(
        default=True,
        description="Whether operation can be safely retried",
    )
    expected_duration_ms: int | None = Field(
        default=None,
        description="Expected operation duration",
        ge=0,
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Operation tags for categorization",
    )

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.operation_name
