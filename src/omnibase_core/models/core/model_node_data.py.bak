from typing import Any

from pydantic import Field

"""
Node Data Model.

Detailed node information data structure.
"""

from pydantic import BaseModel, Field


class ModelNodeData(BaseModel):
    """Detailed node information data."""

    # Basic info
    node_id: str | None = Field(None, description="Node identifier")
    display_name: str | None = Field(None, description="Display name")
    description: str | None = Field(None, description="Node description")
    author: str | None = Field(None, description="Node author")

    # Status
    status: str | None = Field(None, description="Current status")
    health: str | None = Field(None, description="Health status")
    enabled: bool = Field(True, description="Whether node is enabled")

    # Metadata
    created_at: str | None = Field(None, description="Creation timestamp")
    updated_at: str | None = Field(None, description="Last update timestamp")
    tags: list[str] = Field(default_factory=list, description="Node tags")

    # Performance
    execution_count: int | None = Field(None, description="Total executions")
    success_rate: float | None = Field(None, description="Success rate percentage")
    avg_execution_time_ms: float | None = Field(
        None,
        description="Average execution time",
    )

    # Custom metadata
    custom_metadata: dict[str, str] | None = Field(
        None,
        description="Custom metadata",
    )
