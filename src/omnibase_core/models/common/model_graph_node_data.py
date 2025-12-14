"""
Typed data model for graph nodes.

This module provides strongly-typed data for graph node patterns.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelGraphNodeData(BaseModel):
    """
    Typed data for graph nodes.

    Replaces dict[str, Any] data field in ModelGraphNode
    with explicit typed fields for graph node data.
    """

    state: str | None = Field(
        default=None,
        description="Current node state",
    )
    priority: int | None = Field(
        default=None,
        description="Node execution priority (0-1000, higher = more urgent)",
        ge=0,
        le=1000,
    )
    timeout_ms: int | None = Field(
        default=None,
        description="Node execution timeout in milliseconds",
        ge=0,
    )
    retry_count: int | None = Field(
        default=None,
        description="Maximum retry count",
        ge=0,
    )
    condition: str | None = Field(
        default=None,
        description="Condition expression for decision nodes",
    )
    output_mapping: dict[str, str] = Field(
        default_factory=dict,
        description="Output variable mappings",
    )
    error_handler: str | None = Field(
        default=None,
        description="Error handler node ID",
    )

    model_config = ConfigDict(
        extra="forbid",  # Prevent silent field drops during migration
        validate_assignment=True,
    )


__all__ = ["ModelGraphNodeData"]
