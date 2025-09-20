"""
Node info summary model.

Clean, strongly-typed replacement for node info union return types.
Follows ONEX one-model-per-file naming conventions.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from ...enums.enum_metadata_node_status import EnumMetadataNodeStatus
from .model_semver import ModelSemVer


class ModelNodeInfoSummary(BaseModel):
    """
    Clean, strongly-typed model replacing node info union return types.

    Eliminates: dict[str, str | int | bool | float | None]

    With proper structured data using specific field types.
    """

    # Core node info
    name: str = Field(..., description="Node name")
    description: str | None = Field(None, description="Node description")
    node_type: str = Field(default="unknown", description="Type of node")
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE, description="Node status"
    )
    complexity: str = Field(default="medium", description="Node complexity level")
    version: ModelSemVer = Field(
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="Node version",
    )

    # Timestamps
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Update timestamp")
    last_validated: datetime | None = Field(
        None, description="Last validation timestamp"
    )

    # Categories and organization
    tags: list[str] = Field(default_factory=list, description="Node tags")
    categories: list[str] = Field(default_factory=list, description="Node categories")
    dependencies: list[str] = Field(
        default_factory=list, description="Node dependencies"
    )
    related_nodes: list[str] = Field(default_factory=list, description="Related nodes")

    # Quality indicators
    has_documentation: bool = Field(default=False, description="Has documentation")
    has_examples: bool = Field(default=False, description="Has examples")
    documentation_quality: str = Field(
        default="unknown", description="Documentation quality level"
    )

    # Metrics
    usage_count: int = Field(default=0, description="Usage count")
    success_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Success rate (0-1)"
    )

    error_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Error rate (0-1)"
    )

    # Performance
    average_execution_time_ms: float = Field(
        default=0.0, description="Average execution time in milliseconds"
    )

    memory_usage_mb: float = Field(default=0.0, description="Memory usage in MB")


# Export the model
__all__ = ["ModelNodeInfoSummary"]
