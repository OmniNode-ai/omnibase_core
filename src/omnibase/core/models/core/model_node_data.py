"""
Node Data Model.

Detailed node information data structure.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ModelNodeData(BaseModel):
    """Detailed node information data."""

    # Basic info
    node_id: Optional[str] = Field(None, description="Node identifier")
    display_name: Optional[str] = Field(None, description="Display name")
    description: Optional[str] = Field(None, description="Node description")
    author: Optional[str] = Field(None, description="Node author")

    # Status
    status: Optional[str] = Field(None, description="Current status")
    health: Optional[str] = Field(None, description="Health status")
    enabled: bool = Field(True, description="Whether node is enabled")

    # Metadata
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    tags: List[str] = Field(default_factory=list, description="Node tags")

    # Performance
    execution_count: Optional[int] = Field(None, description="Total executions")
    success_rate: Optional[float] = Field(None, description="Success rate percentage")
    avg_execution_time_ms: Optional[float] = Field(
        None, description="Average execution time"
    )

    # Custom metadata
    custom_metadata: Optional[Dict[str, str]] = Field(
        None, description="Custom metadata"
    )
