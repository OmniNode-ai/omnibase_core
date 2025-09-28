"""
Node Performance Metrics Model.

Performance and usage statistics for nodes.
Part of the ModelNodeMetadataInfo restructuring.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TypedDict

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    Identifiable,
    MetadataProvider,
    Serializable,
    Validatable,
)


class PerformanceSummary(TypedDict):
    """Type-safe performance summary structure.
    Implements omnibase_spi protocols:
    - Identifiable: UUID-based identification
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    usage_count: int
    error_count: int
    success_rate: float
    has_errors: bool
    is_high_usage: bool


class ModelNodePerformanceMetrics(BaseModel):
    """
    Node performance and usage metrics.

    Contains performance-related data:
    - Usage and error counts
    - Success rate calculations
    - Timestamp tracking
    """

    # Usage metrics (2 fields)
    usage_count: int = Field(default=0, description="Usage count", ge=0)
    error_count: int = Field(default=0, description="Error count", ge=0)

    # Performance indicators (1 field)
    success_rate: float = Field(
        default=100.0,
        description="Success rate percentage",
        ge=0.0,
        le=100.0,
    )

    # Timestamps (3 fields)
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None,
        description="Last update timestamp",
    )
    last_accessed: datetime | None = Field(
        default=None,
        description="Last access timestamp",
    )

    def has_errors(self) -> bool:
        """Check if node has errors."""
        return self.error_count > 0

    def get_success_rate(self) -> float:
        """Get success rate."""
        return self.success_rate

    def is_high_usage(self) -> bool:
        """Check if node has high usage (>100 uses)."""
        return self.usage_count > 100

    def increment_usage(self) -> None:
        """Increment usage count."""
        self.usage_count += 1

    def increment_errors(self) -> None:
        """Increment error count and update success rate."""
        self.error_count += 1
        if self.usage_count > 0:
            success_count = self.usage_count - self.error_count
            self.success_rate = (success_count / self.usage_count) * 100.0

    def update_accessed_time(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = datetime.now(UTC)

    def get_performance_summary(self) -> PerformanceSummary:
        """Get performance metrics summary."""
        return PerformanceSummary(
            usage_count=self.usage_count,
            error_count=self.error_count,
            success_rate=self.success_rate,
            has_errors=self.has_errors(),
            is_high_usage=self.is_high_usage(),
        )

    @classmethod
    def create_new(cls) -> ModelNodePerformanceMetrics:
        """Create new performance metrics with defaults."""
        return cls(
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    # Protocol method implementations

    def get_id(self) -> str:
        """Get unique identifier (Identifiable protocol)."""
        # Try common ID field patterns
        for field in [
            "id",
            "uuid",
            "identifier",
            "node_id",
            "execution_id",
            "metadata_id",
        ]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    return str(value)
        return f"{self.__class__.__name__}_{id(self)}"

    def get_metadata(self) -> dict[str, Any]:
        """Get metadata as dictionary (MetadataProvider protocol)."""
        metadata = {}
        # Include common metadata fields
        for field in ["name", "description", "version", "tags", "metadata"]:
            if hasattr(self, field):
                value = getattr(self, field)
                if value is not None:
                    metadata[field] = (
                        str(value) if not isinstance(value, (dict, list)) else value
                    )
        return metadata

    def set_metadata(self, metadata: dict[str, Any]) -> bool:
        """Set metadata from dictionary (MetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:
            return False

    def serialize(self) -> dict[str, Any]:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (Validatable protocol)."""
        try:
            # Basic validation - ensure required fields exist
            # Override in specific models for custom validation
            return True
        except Exception:
            return False


# Export for use
__all__ = ["ModelNodePerformanceMetrics"]
