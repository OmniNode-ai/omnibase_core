"""
Node info summary model.

Clean, strongly-typed replacement for node info union return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_metadata_node_status import EnumMetadataNodeStatus
from ...enums.enum_node_type import EnumNodeType
from ...enums.enum_complexity_level import EnumComplexityLevel
from ...enums.enum_documentation_quality import EnumDocumentationQuality
from ...utils.uuid_helpers import uuid_from_string
from .model_semver import ModelSemVer


class ModelNodeInfoSummary(BaseModel):
    """
    Clean, strongly-typed model replacing node info union return types.

    Eliminates: dict[str, str | int | bool | float | None]

    With proper structured data using specific field types.
    """

    # Core node info - UUID-based entity references
    node_id: UUID = Field(default_factory=lambda: uuid_from_string("default", "node"), description="Unique identifier for the node")
    node_display_name: str | None = Field(None, description="Human-readable node name")
    description: str | None = Field(None, description="Node description")
    node_type: EnumNodeType = Field(default=EnumNodeType.UNKNOWN, description="Type of node")
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE, description="Node status"
    )
    complexity: EnumComplexityLevel = Field(default=EnumComplexityLevel.MEDIUM, description="Node complexity level")
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
    documentation_quality: EnumDocumentationQuality = Field(
        default=EnumDocumentationQuality.UNKNOWN, description="Documentation quality level"
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

    @property
    def name(self) -> str:
        """Get node name with fallback to UUID-based name."""
        return self.node_display_name or f"node_{str(self.node_id)[:8]}"

    @name.setter
    def name(self, value: str) -> None:
        """Set node name (for backward compatibility)."""
        self.node_display_name = value
        self.node_id = uuid_from_string(value, "node")

    @classmethod
    def create_legacy(
        cls,
        name: str,
        **kwargs,
    ) -> "ModelNodeInfoSummary":
        """Create node info summary with legacy name parameter for backward compatibility."""
        return cls(
            node_id=uuid_from_string(name, "node"),
            node_display_name=name,
            **kwargs,
        )


# Export the model
__all__ = ["ModelNodeInfoSummary"]
