"""
Node info summary model.

Clean, strongly-typed replacement for node info union return types.
Follows ONEX one-model-per-file naming conventions.
"""

from datetime import datetime

from pydantic import BaseModel, Field


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
    status: str = Field(default="active", description="Node status")
    complexity: str = Field(default="medium", description="Node complexity level")
    version: str = Field(default="1.0.0", description="Node version")

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

    @classmethod
    def from_legacy_dict(cls, data: dict[str, any]) -> "ModelNodeInfoSummary":
        """
        Create from legacy dict data for migration.

        This method helps migrate from the horrible union type to clean model.
        """
        return cls(
            name=str(data.get("name", "unknown")),
            description=data.get("description"),
            node_type=str(data.get("node_type", "unknown")),
            status=str(data.get("status", "active")),
            complexity=str(data.get("complexity", "medium")),
            version=str(data.get("version", "1.0.0")),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            last_validated=data.get("last_validated"),
            tags=data.get("tags", []) if isinstance(data.get("tags"), list) else [],
            categories=(
                data.get("categories", [])
                if isinstance(data.get("categories"), list)
                else []
            ),
            dependencies=(
                data.get("dependencies", [])
                if isinstance(data.get("dependencies"), list)
                else []
            ),
            related_nodes=(
                data.get("related_nodes", [])
                if isinstance(data.get("related_nodes"), list)
                else []
            ),
            has_documentation=bool(data.get("has_documentation", False)),
            has_examples=bool(data.get("has_examples", False)),
            documentation_quality=str(data.get("documentation_quality", "unknown")),
            usage_count=int(data.get("usage_count", 0)),
            success_rate=float(data.get("success_rate", 0.0)),
            error_rate=float(data.get("error_rate", 0.0)),
            average_execution_time_ms=float(data.get("average_execution_time_ms", 0.0)),
            memory_usage_mb=float(data.get("memory_usage_mb", 0.0)),
        )


# Export the model
__all__ = ["ModelNodeInfoSummary"]
