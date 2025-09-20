"""
Metadata Node Info Model.

Enhanced node information specifically for metadata collections
with usage metrics and performance tracking.
"""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_metadata_node_complexity import EnumMetadataNodeComplexity
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.models.core.model_metadata_usage_metrics import (
    ModelMetadataUsageMetrics,
)
from omnibase_core.models.core.status_dispatch_registry import StatusDispatchRegistry


def _create_usage_metrics() -> ModelMetadataUsageMetrics:
    """Create default ModelMetadataUsageMetrics instance."""
    return ModelMetadataUsageMetrics()

# Compatibility aliases for existing code
ModelMetadataNodeType = EnumMetadataNodeType
ModelMetadataNodeStatus = EnumMetadataNodeStatus
ModelMetadataNodeComplexity = EnumMetadataNodeComplexity


class ModelMetadataNodeInfo(BaseModel):
    """
    Enhanced node information for metadata collections.

    Provides detailed metadata, usage tracking, and performance
    metrics for nodes in metadata collections.
    """

    # Core identification
    name: str = Field(..., description="Node name")
    description: str = Field(default="", description="Node description")
    node_type: EnumMetadataNodeType = Field(
        default=EnumMetadataNodeType.FUNCTION,
        description="Node type",
    )

    # Status and lifecycle
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    complexity: EnumMetadataNodeComplexity = Field(
        default=EnumMetadataNodeComplexity.SIMPLE,
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

    def __post_init__(self) -> None:
        """Initialize status dispatch registry after model creation."""
        self._status_registry = StatusDispatchRegistry()
        self._setup_status_checks()

    def _setup_status_checks(self) -> None:
        """Setup status check functions in registry."""
        # Register status checks
        self._status_registry.register_status_check(
            EnumMetadataNodeStatus.ACTIVE,
            lambda: self.status == EnumMetadataNodeStatus.ACTIVE
        )
        self._status_registry.register_status_check(
            EnumMetadataNodeStatus.STABLE,
            lambda: self.status == EnumMetadataNodeStatus.STABLE
        )
        self._status_registry.register_status_check(
            EnumMetadataNodeStatus.EXPERIMENTAL,
            lambda: self.status == EnumMetadataNodeStatus.EXPERIMENTAL
        )

        # Register complexity checks
        self._status_registry.register_complexity_check(
            EnumMetadataNodeComplexity.SIMPLE,
            lambda: self.complexity == EnumMetadataNodeComplexity.SIMPLE
        )
        self._status_registry.register_complexity_check(
            EnumMetadataNodeComplexity.COMPLEX,
            lambda: self.complexity == EnumMetadataNodeComplexity.COMPLEX
        )
        self._status_registry.register_complexity_check(
            EnumMetadataNodeComplexity.ADVANCED,
            lambda: self.complexity == EnumMetadataNodeComplexity.ADVANCED
        )

    def check_status(self, status: EnumMetadataNodeStatus) -> bool:
        """Check if node has the specified status using enum dispatch."""
        if not hasattr(self, '_status_registry'):
            self._status_registry = StatusDispatchRegistry()
            self._setup_status_checks()
        return self._status_registry.check_status(status)

    def check_complexity(self, complexity: EnumMetadataNodeComplexity) -> bool:
        """Check if node has the specified complexity using enum dispatch."""
        if not hasattr(self, '_status_registry'):
            self._status_registry = StatusDispatchRegistry()
            self._setup_status_checks()
        return self._status_registry.check_complexity(complexity)

    def check_status_group(self, group_name: str) -> bool:
        """Check if node status is in the specified group."""
        if not hasattr(self, '_status_registry'):
            self._status_registry = StatusDispatchRegistry()
            self._setup_status_checks()
        return self._status_registry.check_status_group(group_name)

    def check_complexity_group(self, group_name: str) -> bool:
        """Check if node complexity is in the specified group."""
        if not hasattr(self, '_status_registry'):
            self._status_registry = StatusDispatchRegistry()
            self._setup_status_checks()
        return self._status_registry.check_complexity_group(group_name)

    # Backward compatibility methods using enum dispatch
    def is_active(self) -> bool:
        """Check if node is active."""
        return self.check_status(EnumMetadataNodeStatus.ACTIVE)

    def is_stable(self) -> bool:
        """Check if node is stable."""
        return self.check_status(EnumMetadataNodeStatus.STABLE)

    def is_experimental(self) -> bool:
        """Check if node is experimental."""
        return self.check_status(EnumMetadataNodeStatus.EXPERIMENTAL)

    def is_simple(self) -> bool:
        """Check if node is simple complexity."""
        return self.check_complexity(EnumMetadataNodeComplexity.SIMPLE)

    def is_complex(self) -> bool:
        """Check if node is complex (complex or advanced)."""
        return self.check_complexity_group("complex")

    def is_operational(self) -> bool:
        """Check if node is operational (active or stable)."""
        return self.check_status_group("operational")

    def has_good_documentation(self) -> bool:
        """Check if node has good documentation."""
        return self.has_documentation and self.documentation_quality in [
            "good",
            "excellent",
        ]

    def get_available_status_groups(self) -> list[str]:
        """Get list of available status groups for checking."""
        if not hasattr(self, '_status_registry'):
            self._status_registry = StatusDispatchRegistry()
            self._setup_status_checks()
        return self._status_registry.get_available_status_groups()

    def get_available_complexity_groups(self) -> list[str]:
        """Get list of available complexity groups for checking."""
        if not hasattr(self, '_status_registry'):
            self._status_registry = StatusDispatchRegistry()
            self._setup_status_checks()
        return self._status_registry.get_available_complexity_groups()

    def get_success_rate(self) -> float:
        """Get node success rate."""
        return self.usage_metrics.get_success_rate()

    def get_complexity_score(self) -> int:
        """Get numeric complexity score."""
        complexity_scores = {
            EnumMetadataNodeComplexity.SIMPLE: 1,
            EnumMetadataNodeComplexity.MODERATE: 2,
            EnumMetadataNodeComplexity.COMPLEX: 3,
            EnumMetadataNodeComplexity.ADVANCED: 4,
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
        self.status = EnumMetadataNodeStatus.ACTIVE
        self.update_timestamp()

    def mark_stable(self) -> None:
        """Mark node as stable."""
        self.status = EnumMetadataNodeStatus.STABLE
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
        node_type: EnumMetadataNodeType = EnumMetadataNodeType.FUNCTION,
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
        complexity: EnumMetadataNodeComplexity = EnumMetadataNodeComplexity.SIMPLE,
    ) -> "ModelMetadataNodeInfo":
        """Create function node info."""
        return cls(
            name=name,
            description=description,
            node_type=EnumMetadataNodeType.FUNCTION,
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
            node_type=EnumMetadataNodeType.DOCUMENTATION,
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
