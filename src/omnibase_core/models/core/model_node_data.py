"""
Node Data Model.

Detailed node information data structure.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class ModelNodeData(BaseModel):
    """Detailed node information data."""

    # Basic info
    node_id: UUID | None = Field(default=None, description="Node identifier")
    display_name: str | None = Field(default=None, description="Display name")
    description: str | None = Field(default=None, description="Node description")
    author: str | None = Field(default=None, description="Node author")

    # Status
    status: str | None = Field(default=None, description="Current status")
    health: str | None = Field(default=None, description="Health status")
    enabled: bool = Field(default=True, description="Whether node is enabled")

    # Metadata
    created_at: str | None = Field(default=None, description="Creation timestamp")
    updated_at: str | None = Field(default=None, description="Last update timestamp")
    tags: list[str] = Field(default_factory=list, description="Node tags")

    # Performance
    execution_count: int | None = Field(default=None, description="Total executions")
    success_rate: float | None = Field(
        default=None, description="Success rate percentage"
    )
    avg_execution_time_ms: float | None = Field(
        default=None,
        description="Average execution time",
    )

    # Custom metadata
    custom_metadata: dict[str, str] | None = Field(
        default=None,
        description="Custom metadata",
    )
