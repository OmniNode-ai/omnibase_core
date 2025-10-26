"""
Node information model.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_node_configuration import ModelNodeConfiguration
from omnibase_core.primitives.model_semver import ModelSemVer

__all__ = [
    "ModelNodeConfiguration",
    "ModelNodeInformation",
]


class ModelNodeInformation(BaseModel):
    """
    Node information with typed fields.
    Replaces Dict[str, Any] for node_information fields.
    """

    # Node identification
    node_id: UUID = Field(default=..., description="Node identifier")
    node_name: str = Field(default=..., description="Node name")
    node_type: str = Field(default=..., description="Node type")
    node_version: ModelSemVer = Field(default=..., description="Node version")

    # Node metadata
    description: str | None = Field(default=None, description="Node description")
    author: str | None = Field(default=None, description="Node author")
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )

    # Node capabilities
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    supported_operations: list[str] = Field(
        default_factory=list,
        description="Supported operations",
    )

    # Node configuration
    configuration: ModelNodeConfiguration = Field(
        default_factory=lambda: ModelNodeConfiguration(),
        description="Node configuration",
    )

    # Node status
    status: str = Field(default="active", description="Node status")
    health: str = Field(default="healthy", description="Node health")

    # Performance metrics
    performance_metrics: dict[str, float] | None = Field(
        default=None,
        description="Performance metrics",
    )

    # Dependencies
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelNodeInformation"]:
        """Create from dict[str, Any]ionary for easy migration."""
        if data is None:
            return None

        # Create a copy to avoid mutating original data
        normalized_data = data.copy()

        # Apply field mappings for current standards
        normalized_data.setdefault("node_id", normalized_data.get("id", "unknown"))
        normalized_data.setdefault("node_name", normalized_data.get("name", "unknown"))
        normalized_data.setdefault("node_type", normalized_data.get("type", "generic"))
        normalized_data.setdefault(
            "node_version", normalized_data.get("version", "1.0.0")
        )

        # Use Pydantic validation instead of manual validation
        return cls.model_validate(normalized_data)
