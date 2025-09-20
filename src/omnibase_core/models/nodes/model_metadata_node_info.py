"""
Metadata Node Info Model.

Enhanced node information specifically for metadata collections
with usage metrics and performance tracking.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


def _create_usage_metrics() -> "ModelMetadataUsageMetrics":
    """Create default ModelMetadataUsageMetrics instance."""
    return ModelMetadataUsageMetrics()


class ModelMetadataNodeType(str, Enum):
    """Metadata node type enumeration."""

    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    MODULE = "module"
    PROPERTY = "property"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    TYPE_ALIAS = "type_alias"
    DOCUMENTATION = "documentation"
    EXAMPLE = "example"
    TEST = "test"


class ModelMetadataNodeStatus(str, Enum):
    """Metadata node status enumeration."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    BETA = "beta"
    ALPHA = "alpha"


class ModelMetadataNodeComplexity(str, Enum):
    """Metadata node complexity enumeration."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    ADVANCED = "advanced"


class ModelMetadataUsageMetrics(BaseModel):
    """Usage metrics for metadata nodes."""

    total_invocations: int = Field(
        default=0,
        description="Total number of invocations",
        ge=0,
    )
    success_count: int = Field(
        default=0,
        description="Number of successful invocations",
        ge=0,
    )
    failure_count: int = Field(
        default=0,
        description="Number of failed invocations",
        ge=0,
    )
    average_execution_time_ms: float = Field(
        default=0.0,
        description="Average execution time in milliseconds",
        ge=0.0,
    )
    last_invocation: datetime | None = Field(
        default=None,
        description="Last invocation timestamp",
    )
    peak_memory_usage_mb: float = Field(
        default=0.0,
        description="Peak memory usage in MB",
        ge=0.0,
    )

    def get_success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_invocations == 0:
            return 100.0
        return (self.success_count / self.total_invocations) * 100.0

    def get_failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_invocations == 0:
            return 0.0
        return (self.failure_count / self.total_invocations) * 100.0

    def record_invocation(
        self,
        success: bool,
        execution_time_ms: float = 0.0,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Record a new invocation."""
        self.total_invocations += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        # Update averages
        if execution_time_ms > 0:
            current_total = self.average_execution_time_ms * (
                self.total_invocations - 1
            )
            self.average_execution_time_ms = (
                current_total + execution_time_ms
            ) / self.total_invocations

        # Update peak memory usage
        self.peak_memory_usage_mb = max(memory_usage_mb, self.peak_memory_usage_mb)

        self.last_invocation = datetime.now(UTC)


class ModelMetadataNodeInfo(BaseModel):
    """
    Enhanced node information for metadata collections.

    Provides detailed metadata, usage tracking, and performance
    metrics for nodes in metadata collections.
    """

    # Core identification
    name: str = Field(..., description="Node name")
    description: str = Field(default="", description="Node description")
    node_type: ModelMetadataNodeType = Field(
        default=ModelMetadataNodeType.FUNCTION,
        description="Node type",
    )

    # Status and lifecycle
    status: ModelMetadataNodeStatus = Field(
        default=ModelMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    complexity: ModelMetadataNodeComplexity = Field(
        default=ModelMetadataNodeComplexity.SIMPLE,
        description="Node complexity level",
    )
    version: str = Field(default="1.0.0", description="Node version")

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Creation timestamp",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Last update timestamp",
    )
    last_validated: datetime | None = Field(
        default=None,
        description="Last validation timestamp",
    )

    # Categorization
    tags: list[str] = Field(default_factory=list, description="Node tags")
    categories: list[str] = Field(default_factory=list, description="Node categories")

    # Documentation and examples
    has_documentation: bool = Field(
        default=False,
        description="Whether node has documentation",
    )
    has_examples: bool = Field(
        default=False,
        description="Whether node has examples",
    )
    documentation_quality: str = Field(
        default="basic",
        description="Documentation quality level",
    )

    # Dependencies and relationships
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )
    related_nodes: list[str] = Field(
        default_factory=list,
        description="Related nodes",
    )

    # Usage and performance metrics
    usage_metrics: ModelMetadataUsageMetrics = Field(
        default_factory=_create_usage_metrics,
        description="Usage and performance metrics",
    )

    # Custom metadata for extensibility
    custom_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Custom metadata fields",
    )

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.status == ModelMetadataNodeStatus.ACTIVE

    def is_stable(self) -> bool:
        """Check if node is stable."""
        return self.status == ModelMetadataNodeStatus.STABLE

    def is_experimental(self) -> bool:
        """Check if node is experimental."""
        return self.status == ModelMetadataNodeStatus.EXPERIMENTAL

    def is_simple(self) -> bool:
        """Check if node is simple complexity."""
        return self.complexity == ModelMetadataNodeComplexity.SIMPLE

    def is_complex(self) -> bool:
        """Check if node is complex."""
        return self.complexity in [
            ModelMetadataNodeComplexity.COMPLEX,
            ModelMetadataNodeComplexity.ADVANCED,
        ]

    def has_good_documentation(self) -> bool:
        """Check if node has good documentation."""
        return self.has_documentation and self.documentation_quality in [
            "good",
            "excellent",
        ]

    def get_success_rate(self) -> float:
        """Get node success rate."""
        return self.usage_metrics.get_success_rate()

    def get_complexity_score(self) -> int:
        """Get numeric complexity score."""
        complexity_scores = {
            ModelMetadataNodeComplexity.SIMPLE: 1,
            ModelMetadataNodeComplexity.MODERATE: 2,
            ModelMetadataNodeComplexity.COMPLEX: 3,
            ModelMetadataNodeComplexity.ADVANCED: 4,
        }
        return complexity_scores.get(self.complexity, 1)

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def add_category(self, category: str) -> None:
        """Add a category if not already present."""
        if category not in self.categories:
            self.categories.append(category)

    def add_dependency(self, dependency: str) -> None:
        """Add a dependency if not already present."""
        if dependency not in self.dependencies:
            self.dependencies.append(dependency)

    def add_related_node(self, node_name: str) -> None:
        """Add a related node if not already present."""
        if node_name not in self.related_nodes:
            self.related_nodes.append(node_name)

    def mark_active(self) -> None:
        """Mark node as active."""
        self.status = ModelMetadataNodeStatus.ACTIVE
        self.update_timestamp()

    def mark_stable(self) -> None:
        """Mark node as stable."""
        self.status = ModelMetadataNodeStatus.STABLE
        self.update_timestamp()

    def update_timestamp(self) -> None:
        """Update the last modified timestamp."""
        self.updated_at = datetime.now(UTC)

    def validate_node(self) -> None:
        """Mark node as validated."""
        self.last_validated = datetime.now(UTC)

    def record_usage(
        self,
        success: bool,
        execution_time_ms: float = 0.0,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Record node usage."""
        self.usage_metrics.record_invocation(
            success,
            execution_time_ms,
            memory_usage_mb,
        )
        self.update_timestamp()

    def set_documentation_quality(self, quality: str) -> None:
        """Set documentation quality level."""
        valid_levels = ["basic", "good", "excellent"]
        if quality in valid_levels:
            self.documentation_quality = quality
            self.has_documentation = True
            self.update_timestamp()

    def add_custom_metadata(self, key: str, value: Any) -> None:
        """Add custom metadata."""
        self.custom_metadata[key] = value
        self.update_timestamp()

    def get_custom_metadata(self, key: str, default: Any = None) -> Any:
        """Get custom metadata value."""
        return self.custom_metadata.get(key, default)

    def to_summary(self) -> dict[str, Any]:
        """Get node summary for quick overview."""
        return {
            "name": self.name,
            "description": self.description,
            "node_type": self.node_type.value,
            "status": self.status.value,
            "complexity": self.complexity.value,
            "version": self.version,
            "success_rate": self.get_success_rate(),
            "has_documentation": self.has_documentation,
            "has_examples": self.has_examples,
            "total_invocations": self.usage_metrics.total_invocations,
            "tags": self.tags,
            "categories": self.categories,
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def create_simple(
        cls,
        name: str,
        description: str = "",
        node_type: ModelMetadataNodeType = ModelMetadataNodeType.FUNCTION,
    ) -> "ModelMetadataNodeInfo":
        """Create a simple node info."""
        return cls(
            name=name,
            description=description,
            node_type=node_type,
        )

    @classmethod
    def create_function_info(
        cls,
        name: str,
        description: str = "",
        complexity: ModelMetadataNodeComplexity = ModelMetadataNodeComplexity.SIMPLE,
    ) -> "ModelMetadataNodeInfo":
        """Create function node info."""
        return cls(
            name=name,
            description=description,
            node_type=ModelMetadataNodeType.FUNCTION,
            complexity=complexity,
        )

    @classmethod
    def create_documentation_info(
        cls,
        name: str,
        description: str = "",
    ) -> "ModelMetadataNodeInfo":
        """Create documentation node info."""
        return cls(
            name=name,
            description=description,
            node_type=ModelMetadataNodeType.DOCUMENTATION,
            has_documentation=True,
            documentation_quality="good",
        )


# Export for use
__all__ = [
    "ModelMetadataNodeComplexity",
    "ModelMetadataNodeInfo",
    "ModelMetadataNodeStatus",
    "ModelMetadataNodeType",
    "ModelMetadataUsageMetrics",
]