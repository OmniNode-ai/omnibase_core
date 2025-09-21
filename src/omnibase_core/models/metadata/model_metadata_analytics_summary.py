"""
Metadata analytics summary model.

Clean, strongly-typed replacement for analytics union return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ...utils.uuid_helpers import uuid_from_string


class ModelMetadataAnalyticsSummary(BaseModel):
    """
    Clean, strongly-typed model replacing analytics union return types.

    Eliminates: dict[str, str | int | bool | float | None]

    With proper structured data using specific field types.
    """

    # Core collection info - UUID-based entity references
    collection_id: UUID = Field(default_factory=lambda: uuid_from_string("default", "collection"), description="Unique identifier for the collection")
    collection_display_name: str | None = Field(None, description="Human-readable collection name")

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

    @property
    def collection_name(self) -> str | None:
        """Get collection name with fallback for backward compatibility."""
        return self.collection_display_name

    @collection_name.setter
    def collection_name(self, value: str | None) -> None:
        """Set collection name (for backward compatibility)."""
        self.collection_display_name = value
        if value:
            self.collection_id = uuid_from_string(value, "collection")
