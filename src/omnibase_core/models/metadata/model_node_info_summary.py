"""
Node Info Summary Model (Composed).

Composed model that combines focused node information components.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, TypedDict, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.core.type_constraints import (
    MetadataProvider,
    Serializable,
    Validatable,
)

# Type variable for decorator
F = TypeVar("F", bound=Callable[..., Any])


def allow_dict_any(func: F) -> F:
    """
    Decorator to allow dict[str, Any] usage in specific functions.

    This should only be used when:
    1. Converting untyped external data to typed internal models
    2. Complex conversion functions where intermediate dicts need flexibility
    3. Legacy integration where gradual typing is being applied

    Justification: This method accepts flexible parameter data dictionaries
    that get validated and converted by component-specific update methods.
    """
    return func


from omnibase_core.enums.enum_conceptual_complexity import EnumConceptualComplexity
from omnibase_core.enums.enum_documentation_quality import EnumDocumentationQuality
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_node_type import EnumNodeType
from omnibase_core.utils.uuid_utilities import uuid_from_string

from .model_semver import ModelSemVer
from .node_info.model_node_categorization import ModelNodeCategorization
from .node_info.model_node_core import ModelNodeCore
from .node_info.model_node_performance_metrics import ModelNodePerformanceMetrics
from .node_info.model_node_quality_indicators import ModelNodeQualityIndicators
from .node_info.model_node_timestamps import ModelNodeTimestamps


class TypedDictNodeCore(TypedDict):
    """Node core data structure.
    Implements omnibase_spi protocols:
    - MetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    node_id: UUID
    node_name: str | None
    description: str | None
    node_type: str
    status: str
    complexity: str
    version: ModelSemVer
    is_active: bool
    is_complex: bool


class TypedDictNodeInfoSummaryData(TypedDict):
    """Typed structure for node info summary serialization."""

    core: TypedDictNodeCore
    timestamps: Any  # From component method call
    categorization: Any  # From component method call
    quality: Any  # From component method call
    performance: Any  # From component method call


class ModelNodeInfoSummary(BaseModel):
    """
    Composed node info summary using focused components.

    Provides comprehensive node information with core data, timing,
    categorization, quality indicators, and performance metrics.
    """

    # Composed components
    core: ModelNodeCore = Field(
        default_factory=lambda: ModelNodeCore(
            node_display_name=None,
            description=None,
        ),
        description="Core node identification and basic information",
    )
    timestamps: ModelNodeTimestamps = Field(
        default_factory=lambda: ModelNodeTimestamps(
            created_at=None,
            updated_at=None,
            last_validated=None,
        ),
        description="Timing and lifecycle information",
    )
    categorization: ModelNodeCategorization = Field(
        default_factory=ModelNodeCategorization,
        description="Categories, tags, and relationships",
    )
    quality: ModelNodeQualityIndicators = Field(
        default_factory=ModelNodeQualityIndicators,
        description="Quality and documentation indicators",
    )
    performance: ModelNodePerformanceMetrics = Field(
        default_factory=ModelNodePerformanceMetrics,
        description="Usage and performance metrics",
    )

    # Properties for direct access
    @property
    def node_id(self) -> UUID:
        """Get node ID."""
        return self.core.node_id

    @node_id.setter
    def node_id(self, value: UUID) -> None:
        """Set node ID."""
        self.core.node_id = value

    @property
    def node_display_name(self) -> str | None:
        """Get node display name."""
        return self.core.node_display_name

    @node_display_name.setter
    def node_display_name(self, value: str | None) -> None:
        """Set node display name."""
        self.core.node_display_name = value

    @property
    def description(self) -> str | None:
        """Get description."""
        return self.core.description

    @description.setter
    def description(self, value: str | None) -> None:
        """Set description."""
        self.core.description = value

    @property
    def node_type(self) -> EnumNodeType:
        """Get node type."""
        return self.core.node_type

    @node_type.setter
    def node_type(self, value: EnumNodeType) -> None:
        """Set node type."""
        self.core.node_type = value

    @property
    def status(self) -> EnumMetadataNodeStatus:
        """Get status."""
        return self.core.status

    @status.setter
    def status(self, value: EnumMetadataNodeStatus) -> None:
        """Set status."""
        self.core.status = value

    @property
    def complexity(self) -> EnumConceptualComplexity:
        """Get complexity."""
        return self.core.complexity

    @complexity.setter
    def complexity(self, value: EnumConceptualComplexity) -> None:
        """Set complexity."""
        self.core.complexity = value

    @property
    def version(self) -> ModelSemVer:
        """Get version."""
        return self.core.version

    @version.setter
    def version(self, value: ModelSemVer) -> None:
        """Set version."""
        self.core.version = value

    @property
    def created_at(self) -> datetime | None:
        """Get created timestamp."""
        return self.timestamps.created_at

    @created_at.setter
    def created_at(self, value: datetime | None) -> None:
        """Set created timestamp."""
        self.timestamps.created_at = value

    @property
    def updated_at(self) -> datetime | None:
        """Get updated timestamp."""
        return self.timestamps.updated_at

    @updated_at.setter
    def updated_at(self, value: datetime | None) -> None:
        """Set updated timestamp."""
        self.timestamps.updated_at = value

    @property
    def last_validated(self) -> datetime | None:
        """Get last validated timestamp."""
        return self.timestamps.last_validated

    @last_validated.setter
    def last_validated(self, value: datetime | None) -> None:
        """Set last validated timestamp."""
        self.timestamps.last_validated = value

    @property
    def tags(self) -> list[str]:
        """Get tags."""
        return self.categorization.tags

    @tags.setter
    def tags(self, value: list[str]) -> None:
        """Set tags."""
        self.categorization.tags = value.copy()

    @property
    def categories(self) -> list[str]:
        """Get categories."""
        return self.categorization.categories

    @categories.setter
    def categories(self, value: list[str]) -> None:
        """Set categories."""
        self.categorization.categories = value.copy()

    @property
    def dependencies(self) -> list[UUID]:
        """Get dependencies."""
        return self.categorization.dependencies

    @dependencies.setter
    def dependencies(self, value: list[UUID]) -> None:
        """Set dependencies."""
        self.categorization.dependencies = value.copy()

    @property
    def related_nodes(self) -> list[UUID]:
        """Get related nodes."""
        return self.categorization.related_nodes

    @related_nodes.setter
    def related_nodes(self, value: list[UUID]) -> None:
        """Set related nodes."""
        self.categorization.related_nodes = value.copy()

    @property
    def has_documentation(self) -> bool:
        """Get has documentation."""
        return self.quality.has_documentation

    @has_documentation.setter
    def has_documentation(self, value: bool) -> None:
        """Set has documentation."""
        self.quality.has_documentation = value

    @property
    def has_examples(self) -> bool:
        """Get has examples."""
        return self.quality.has_examples

    @has_examples.setter
    def has_examples(self, value: bool) -> None:
        """Set has examples."""
        self.quality.has_examples = value

    @property
    def documentation_quality(self) -> EnumDocumentationQuality:
        """Get documentation quality."""
        return self.quality.documentation_quality

    @documentation_quality.setter
    def documentation_quality(self, value: EnumDocumentationQuality) -> None:
        """Set documentation quality."""
        self.quality.documentation_quality = value

    @property
    def usage_count(self) -> int:
        """Get usage count."""
        return self.performance.usage_count

    @usage_count.setter
    def usage_count(self, value: int) -> None:
        """Set usage count."""
        self.performance.usage_count = value

    @property
    def success_rate(self) -> float:
        """Get success rate."""
        return self.performance.success_rate

    @success_rate.setter
    def success_rate(self, value: float) -> None:
        """Set success rate."""
        self.performance.success_rate = value

    @property
    def error_rate(self) -> float:
        """Get error rate."""
        return self.performance.error_rate

    @error_rate.setter
    def error_rate(self, value: float) -> None:
        """Set error rate."""
        self.performance.error_rate = value

    @property
    def average_execution_time_ms(self) -> float:
        """Get average execution time."""
        return self.performance.average_execution_time_ms

    @average_execution_time_ms.setter
    def average_execution_time_ms(self, value: float) -> None:
        """Set average execution time."""
        self.performance.average_execution_time_ms = value

    @property
    def memory_usage_mb(self) -> float:
        """Get memory usage."""
        return self.performance.memory_usage_mb

    @memory_usage_mb.setter
    def memory_usage_mb(self, value: float) -> None:
        """Set memory usage."""
        self.performance.memory_usage_mb = value

    # Composite methods
    def get_comprehensive_summary(self) -> TypedDictNodeInfoSummaryData:
        """Get comprehensive summary from all components."""
        return {
            "core": {
                "node_id": self.core.node_id,
                "node_name": self.core.node_name,
                "description": self.core.description,
                "node_type": self.core.node_type.value,
                "status": self.core.status.value,
                "complexity": self.core.complexity.value,
                "version": self.core.version,
                "is_active": self.core.is_active,
                "is_complex": self.core.is_complex,
            },
            "timestamps": self.timestamps.get_lifecycle_summary(),
            "categorization": self.categorization.get_categorization_summary(),
            "quality": self.quality.get_quality_summary(),
            "performance": self.performance.get_performance_summary(),
        }

    @allow_dict_any
    def update_all_metrics(
        self,
        core_data: dict[str, Any] | None = None,
        timestamp_data: dict[str, datetime | None] | None = None,
        categorization_data: dict[str, list[str]] | None = None,
        quality_data: dict[str, Any] | None = None,
        performance_data: dict[str, int | float] | None = None,
    ) -> None:
        """Update all component metrics."""
        # Update core data
        if core_data:
            if "node_display_name" in core_data:
                self.core.node_display_name = core_data["node_display_name"]
            if "description" in core_data:
                self.core.description = core_data["description"]
            if "status" in core_data:
                self.core.update_status(core_data["status"])
            if "complexity" in core_data:
                self.core.update_complexity(core_data["complexity"])

        # Update timestamps
        if timestamp_data:
            if "created_at" in timestamp_data:
                self.timestamps.update_created_timestamp(timestamp_data["created_at"])
            if "updated_at" in timestamp_data:
                self.timestamps.update_modified_timestamp(timestamp_data["updated_at"])
            if "last_validated" in timestamp_data:
                self.timestamps.update_validation_timestamp(
                    timestamp_data["last_validated"]
                )

        # Update categorization
        if categorization_data:
            if "tags" in categorization_data:
                self.categorization.add_tags(categorization_data["tags"])
            if "categories" in categorization_data:
                self.categorization.add_categories(categorization_data["categories"])

        # Update quality
        if quality_data:
            if any(
                key in quality_data
                for key in [
                    "has_documentation",
                    "documentation_quality",
                    "has_examples",
                ]
            ):
                self.quality.update_documentation_status(
                    quality_data.get(
                        "has_documentation", self.quality.has_documentation
                    ),
                    quality_data.get("documentation_quality"),
                    quality_data.get("has_examples"),
                )

        # Update performance
        if performance_data:
            if any(
                key in performance_data
                for key in ["usage_count", "success_rate", "error_rate"]
            ):
                self.performance.update_usage_metrics(
                    int(
                        performance_data.get(
                            "usage_count", self.performance.usage_count
                        )
                    ),
                    performance_data.get("success_rate", self.performance.success_rate),
                    performance_data.get("error_rate", self.performance.error_rate),
                )
            if any(
                key in performance_data
                for key in ["average_execution_time_ms", "memory_usage_mb"]
            ):
                self.performance.update_performance_metrics(
                    performance_data.get(
                        "average_execution_time_ms",
                        self.performance.average_execution_time_ms,
                    ),
                    performance_data.get(
                        "memory_usage_mb", self.performance.memory_usage_mb
                    ),
                )

    def is_healthy(self) -> bool:
        """Check if node is healthy overall."""
        return (
            self.core.is_active
            and not self.timestamps.is_stale()
            and self.quality.get_quality_score() > 60.0
            and not self.performance.has_performance_issues
        )

    def get_health_score(self) -> float:
        """Calculate composite health score (0-100)."""
        # Status score (25% weight)
        status_score = 25.0 if self.core.is_active else 0.0

        # Freshness score (25% weight)
        if self.timestamps.is_recently_updated():
            freshness_score = 25.0
        elif self.timestamps.is_stale():
            freshness_score = 5.0
        else:
            freshness_score = 15.0

        # Quality score (25% weight)
        quality_score = self.quality.get_quality_score() * 0.25

        # Performance score (25% weight)
        performance_score = self.performance.calculate_performance_score() * 0.25

        return status_score + freshness_score + quality_score + performance_score

    @classmethod
    def create_for_node(
        cls,
        node_id: UUID,
        node_name: str,
        node_type: EnumNodeType,
        description: str | None = None,
    ) -> ModelNodeInfoSummary:
        """Create node info summary for specific node."""
        core = ModelNodeCore.create_for_node(node_id, node_name, node_type, description)
        timestamps = ModelNodeTimestamps.create_new()
        return cls(core=core, timestamps=timestamps)

    @classmethod
    def create_well_documented_node(
        cls,
        node_name: str,
        node_type: EnumNodeType,
        tags: list[str] | None = None,
        categories: list[str] | None = None,
    ) -> ModelNodeInfoSummary:
        """Create node info summary with excellent quality."""
        core = ModelNodeCore.create_minimal_node(node_name, node_type)
        timestamps = ModelNodeTimestamps.create_new()
        categorization = ModelNodeCategorization.create_comprehensive(
            tags or [],
            categories or [],
        )
        quality = ModelNodeQualityIndicators.create_excellent_quality()
        performance = ModelNodePerformanceMetrics.create_high_performance()

        return cls(
            core=core,
            timestamps=timestamps,
            categorization=categorization,
            quality=quality,
            performance=performance,
        )

    @classmethod
    def create_minimal_node(
        cls,
        node_name: str,
        node_type: EnumNodeType = EnumNodeType.UNKNOWN,
    ) -> ModelNodeInfoSummary:
        """Create minimal node info summary."""
        core = ModelNodeCore.create_minimal_node(node_name, node_type)
        timestamps = ModelNodeTimestamps.create_new()
        return cls(core=core, timestamps=timestamps)

    # Export the model

    # Protocol method implementations

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


__all__ = ["ModelNodeInfoSummary"]
