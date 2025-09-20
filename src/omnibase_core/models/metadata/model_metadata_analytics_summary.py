"""
Metadata analytics summary model.

Clean, strongly-typed replacement for analytics union return types.
Follows ONEX one-model-per-file naming conventions.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelMetadataAnalyticsSummary(BaseModel):
    """
    Clean, strongly-typed model replacing analytics union return types.

    Eliminates: dict[str, str | int | bool | float | None]

    With proper structured data using specific field types.
    """

    # Core collection info
    collection_name: str | None = Field(None, description="Name of the collection")

    # Node counts
    total_nodes: int = Field(default=0, description="Total number of nodes")

    active_nodes: int = Field(default=0, description="Number of active nodes")

    deprecated_nodes: int = Field(default=0, description="Number of deprecated nodes")

    disabled_nodes: int = Field(default=0, description="Number of disabled nodes")

    # Quality metrics
    health_score: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Overall health score (0-100)"
    )

    success_rate: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Overall success rate (0-1)"
    )

    documentation_coverage: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Documentation coverage (0-1)"
    )

    # Error tracking
    error_count: int = Field(default=0, description="Number of errors")

    warning_count: int = Field(default=0, description="Number of warnings")

    critical_error_count: int = Field(
        default=0, description="Number of critical errors"
    )

    # Timestamps
    last_modified: datetime | None = Field(
        None, description="Last modification timestamp"
    )

    last_validated: datetime | None = Field(
        None, description="Last validation timestamp"
    )

    # Performance metrics
    average_execution_time_ms: float = Field(
        default=0.0, description="Average execution time in milliseconds"
    )

    peak_memory_usage_mb: float = Field(
        default=0.0, description="Peak memory usage in MB"
    )

    total_invocations: int = Field(default=0, description="Total number of invocations")

    @classmethod
    def from_legacy_dict(cls, data: dict[str, any]) -> "ModelMetadataAnalyticsSummary":
        """
        Create from legacy dict data for migration.

        This method helps migrate from the horrible union type to clean model.
        """
        return cls(
            collection_name=data.get("collection_name"),
            total_nodes=int(data.get("total_nodes", 0)),
            active_nodes=int(data.get("active_nodes", 0)),
            deprecated_nodes=int(data.get("deprecated_nodes", 0)),
            disabled_nodes=int(data.get("disabled_nodes", 0)),
            health_score=float(data.get("health_score", 0.0)),
            success_rate=float(data.get("success_rate", 0.0)),
            documentation_coverage=float(data.get("documentation_coverage", 0.0)),
            error_count=int(data.get("error_count", 0)),
            warning_count=int(data.get("warning_count", 0)),
            critical_error_count=int(data.get("critical_error_count", 0)),
            last_modified=data.get("last_modified"),
            last_validated=data.get("last_validated"),
            average_execution_time_ms=float(data.get("average_execution_time_ms", 0.0)),
            peak_memory_usage_mb=float(data.get("peak_memory_usage_mb", 0.0)),
            total_invocations=int(data.get("total_invocations", 0)),
        )


# Export the model
__all__ = ["ModelMetadataAnalyticsSummary"]
