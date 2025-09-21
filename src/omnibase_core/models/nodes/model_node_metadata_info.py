"""
Node Metadata Info Model.

Simple model for node metadata information used in CLI output.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from ...enums.enum_metadata_node_status import EnumMetadataNodeStatus
from ...enums.enum_metadata_node_type import EnumMetadataNodeType
from ...enums.enum_node_health_status import EnumNodeHealthStatus
from ...protocols.protocol_node_info_like import NodeInfoLike
from ..metadata.model_semver import ModelSemVer
from .model_node_core_metadata import ModelNodeCoreMetadata
from .model_node_organization_metadata import ModelNodeOrganizationMetadata
from .model_node_performance_metrics import ModelNodePerformanceMetrics


class ModelNodeMetadataInfo(BaseModel):
    """
    Node metadata information model.

    Restructured to use focused sub-models for better organization.
    Maintains backward compatibility through property delegation.
    """

    # Composed sub-models (3 primary components)
    core: ModelNodeCoreMetadata = Field(
        default_factory=ModelNodeCoreMetadata,
        description="Core node metadata",
    )
    performance: ModelNodePerformanceMetrics = Field(
        default_factory=ModelNodePerformanceMetrics,
        description="Performance metrics",
    )
    organization: ModelNodeOrganizationMetadata = Field(
        default_factory=ModelNodeOrganizationMetadata,
        description="Organization metadata",
    )

    # Backward compatibility properties
    @property
    def node_id(self) -> UUID:
        """Node identifier (delegated to core)."""
        return self.core.node_id

    @node_id.setter
    def node_id(self, value: UUID) -> None:
        """Set node identifier."""
        self.core.node_id = value

    @property
    def node_name(self) -> str:
        """Node name (delegated to core)."""
        return self.core.node_name

    @node_name.setter
    def node_name(self, value: str) -> None:
        """Set node name."""
        self.core.node_name = value

    @property
    def node_type(self) -> EnumMetadataNodeType:
        """Node type (delegated to core)."""
        return self.core.node_type

    @node_type.setter
    def node_type(self, value: EnumMetadataNodeType) -> None:
        """Set node type."""
        self.core.node_type = value

    @property
    def status(self) -> EnumMetadataNodeStatus:
        """Node status (delegated to core)."""
        return self.core.status

    @status.setter
    def status(self, value: EnumMetadataNodeStatus) -> None:
        """Set node status."""
        self.core.status = value

    @property
    def health(self) -> str:
        """Node health (backward compatible string)."""
        return self.core.health.value

    @health.setter
    def health(self, value: str) -> None:
        """Set node health from string."""
        try:
            self.core.health = EnumNodeHealthStatus(value)
        except ValueError:
            self.core.health = EnumNodeHealthStatus.UNKNOWN

    @property
    def version(self) -> ModelSemVer | None:
        """Node version (delegated to core)."""
        return self.core.version

    @version.setter
    def version(self, value: ModelSemVer | None) -> None:
        """Set node version."""
        self.core.version = value

    @property
    def description(self) -> str | None:
        """Node description (delegated to organization)."""
        return self.organization.description

    @description.setter
    def description(self, value: str | None) -> None:
        """Set node description."""
        self.organization.description = value

    @property
    def author(self) -> str | None:
        """Node author (delegated to organization)."""
        return self.organization.author

    @author.setter
    def author(self, value: str | None) -> None:
        """Set node author."""
        self.organization.author = value

    @property
    def capabilities(self) -> list[str]:
        """Node capabilities (delegated to organization)."""
        return self.organization.capabilities

    @property
    def tags(self) -> list[str]:
        """Node tags (delegated to organization)."""
        return self.organization.tags

    @property
    def categories(self) -> list[str]:
        """Node categories (delegated to organization)."""
        return self.organization.categories

    @property
    def dependencies(self) -> list[str]:
        """Node dependencies (delegated to organization)."""
        return self.organization.dependencies

    @property
    def dependents(self) -> list[str]:
        """Node dependents (delegated to organization)."""
        return self.organization.dependents

    @property
    def usage_count(self) -> int:
        """Usage count (delegated to performance)."""
        return self.performance.usage_count

    @property
    def error_count(self) -> int:
        """Error count (delegated to performance)."""
        return self.performance.error_count

    @property
    def success_rate(self) -> float:
        """Success rate (delegated to performance)."""
        return self.performance.success_rate

    @property
    def created_at(self) -> datetime | None:
        """Creation timestamp (delegated to performance)."""
        return self.performance.created_at

    @created_at.setter
    def created_at(self, value: datetime | None) -> None:
        """Set creation timestamp."""
        self.performance.created_at = value

    @property
    def updated_at(self) -> datetime | None:
        """Update timestamp (delegated to performance)."""
        return self.performance.updated_at

    @updated_at.setter
    def updated_at(self, value: datetime | None) -> None:
        """Set update timestamp."""
        self.performance.updated_at = value

    @property
    def last_accessed(self) -> datetime | None:
        """Last access timestamp (delegated to performance)."""
        return self.performance.last_accessed

    @last_accessed.setter
    def last_accessed(self, value: datetime | None) -> None:
        """Set last access timestamp."""
        self.performance.last_accessed = value

    @property
    def custom_metadata(self) -> dict[str, str | int | bool | float]:
        """Custom metadata (backward compatible)."""
        # Convert from typed custom properties to legacy format
        result = {}
        if self.organization.custom_properties.string_properties:
            result.update(self.organization.custom_properties.string_properties)
        if self.organization.custom_properties.numeric_properties:
            result.update(self.organization.custom_properties.numeric_properties)
        if self.organization.custom_properties.boolean_properties:
            result.update(self.organization.custom_properties.boolean_properties)
        return result

    @custom_metadata.setter
    def custom_metadata(self, value: dict[str, str | int | bool | float]) -> None:
        """Set custom metadata (convert to typed properties)."""
        for key, val in value.items():
            if isinstance(val, str):
                self.organization.custom_properties.string_properties[key] = val
            elif isinstance(val, (int, float)):
                self.organization.custom_properties.numeric_properties[key] = val
            elif isinstance(val, bool):
                self.organization.custom_properties.boolean_properties[key] = val

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.core.is_active()

    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return self.core.is_healthy()

    def has_errors(self) -> bool:
        """Check if node has errors."""
        return self.performance.has_errors()

    def get_success_rate(self) -> float:
        """Get success rate."""
        return self.performance.get_success_rate()

    def is_high_usage(self) -> bool:
        """Check if node has high usage (>100 uses)."""
        return self.performance.is_high_usage()

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        self.organization.add_tag(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        self.organization.remove_tag(tag)

    def add_capability(self, capability: str) -> None:
        """Add a capability if not already present."""
        self.organization.add_capability(capability)

    def has_capability(self, capability: str) -> bool:
        """Check if node has a specific capability."""
        return self.organization.has_capability(capability)

    def add_category(self, category: str) -> None:
        """Add a category if not already present."""
        self.organization.add_category(category)

    def increment_usage(self) -> None:
        """Increment usage count."""
        self.performance.increment_usage()

    def increment_errors(self) -> None:
        """Increment error count and update success rate."""
        self.performance.increment_errors()

    def update_accessed_time(self) -> None:
        """Update last accessed timestamp."""
        self.performance.update_accessed_time()

    def get_summary(self) -> dict[str, str | int | bool | float | list[str] | None]:
        """Get node metadata summary."""
        # Combine summaries from all sub-models
        core_summary = self.core.get_status_summary()
        performance_summary = self.performance.get_performance_summary()
        org_summary = self.organization.get_organization_summary()

        return {
            "node_id": str(self.node_id),
            "node_name": self.node_name,
            "node_type": self.node_type.value,
            "status": self.status.value,
            "health": self.health,
            "version": core_summary["version"],
            "usage_count": self.usage_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_errors": self.has_errors(),
            "capabilities_count": org_summary["capabilities_count"],
            "tags_count": org_summary["tags_count"],
            "is_high_usage": performance_summary["is_high_usage"],
        }

    @classmethod
    def create_simple(
        cls,
        node_id: UUID,
        node_name: str,
        node_type: EnumMetadataNodeType = EnumMetadataNodeType.FUNCTION,
    ) -> ModelNodeMetadataInfo:
        """Create a simple node metadata info."""
        core = ModelNodeCoreMetadata(
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
        )
        return cls(
            core=core,
            performance=ModelNodePerformanceMetrics.create_new(),
            organization=ModelNodeOrganizationMetadata(),
        )

    @classmethod
    def from_node_info(cls, node_info: NodeInfoLike) -> ModelNodeMetadataInfo:
        """Create from node info object."""
        # Extract basic information and distribute to sub-models
        core = ModelNodeCoreMetadata(
            node_id=getattr(node_info, "node_id", uuid4()),
            node_name=getattr(node_info, "node_name", "unknown"),
            node_type=getattr(node_info, "node_type", EnumMetadataNodeType.FUNCTION),
            version=getattr(node_info, "version", None),
            status=getattr(node_info, "status", EnumMetadataNodeStatus.ACTIVE),
        )

        # Handle health with enum conversion
        health_str = getattr(node_info, "health", "healthy")
        try:
            core.health = EnumNodeHealthStatus(health_str)
        except ValueError:
            core.health = EnumNodeHealthStatus.HEALTHY

        organization = ModelNodeOrganizationMetadata(
            description=getattr(node_info, "description", None),
            author=getattr(node_info, "author", None),
        )

        return cls(
            core=core,
            performance=ModelNodePerformanceMetrics.create_new(),
            organization=organization,
        )


# Export for use
__all__ = ["ModelNodeMetadataInfo"]
