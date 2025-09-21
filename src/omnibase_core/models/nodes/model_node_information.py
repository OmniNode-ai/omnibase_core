"""
Node information model.
Restructured to use focused sub-models for better organization.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_metadata_node_status import EnumMetadataNodeStatus
from ...enums.enum_metadata_node_type import EnumMetadataNodeType
from ...enums.enum_registry_status import EnumRegistryStatus
from ..metadata.model_semver import ModelSemVer
from .model_node_basic_info import ModelNodeBasicInfo
from .model_node_capabilities_info import ModelNodeCapabilitiesInfo
from .model_node_configuration import ModelNodeConfiguration


class ModelNodeInformation(BaseModel):
    """
    Node information with typed fields.

    Restructured to use focused sub-models for better organization.
    Maintains backward compatibility through property delegation.
    """

    # Composed sub-models (3 primary components)
    basic_info: ModelNodeBasicInfo = Field(
        ...,
        description="Basic node information",
    )
    capabilities: ModelNodeCapabilitiesInfo = Field(
        default_factory=ModelNodeCapabilitiesInfo,
        description="Node capabilities and operations",
    )
    configuration: ModelNodeConfiguration = Field(
        default_factory=ModelNodeConfiguration,
        description="Node configuration",
    )

    # Backward compatibility properties
    @property
    def node_id(self) -> UUID:
        """Node identifier (delegated to basic_info)."""
        return self.basic_info.node_id

    @node_id.setter
    def node_id(self, value: UUID) -> None:
        """Set node identifier."""
        self.basic_info.node_id = value

    @property
    def node_name(self) -> str:
        """Node name (delegated to basic_info)."""
        return self.basic_info.node_name

    @node_name.setter
    def node_name(self, value: str) -> None:
        """Set node name."""
        self.basic_info.node_name = value

    @property
    def node_type(self) -> EnumMetadataNodeType:
        """Node type (delegated to basic_info)."""
        return self.basic_info.node_type

    @node_type.setter
    def node_type(self, value: EnumMetadataNodeType) -> None:
        """Set node type."""
        self.basic_info.node_type = value

    @property
    def node_version(self) -> ModelSemVer:
        """Node version (delegated to basic_info)."""
        return self.basic_info.node_version

    @node_version.setter
    def node_version(self, value: ModelSemVer) -> None:
        """Set node version."""
        self.basic_info.node_version = value

    @property
    def description(self) -> str | None:
        """Node description (delegated to basic_info)."""
        return self.basic_info.description

    @description.setter
    def description(self, value: str | None) -> None:
        """Set node description."""
        self.basic_info.description = value

    @property
    def author(self) -> str | None:
        """Node author (delegated to basic_info)."""
        return self.basic_info.author

    @author.setter
    def author(self, value: str | None) -> None:
        """Set node author."""
        self.basic_info.author = value

    @property
    def created_at(self) -> datetime | None:
        """Creation timestamp (delegated to basic_info)."""
        return self.basic_info.created_at

    @created_at.setter
    def created_at(self, value: datetime | None) -> None:
        """Set creation timestamp."""
        self.basic_info.created_at = value

    @property
    def updated_at(self) -> datetime | None:
        """Update timestamp (delegated to basic_info)."""
        return self.basic_info.updated_at

    @updated_at.setter
    def updated_at(self, value: datetime | None) -> None:
        """Set update timestamp."""
        self.basic_info.updated_at = value

    @property
    def status(self) -> EnumMetadataNodeStatus:
        """Node status (delegated to basic_info)."""
        return self.basic_info.status

    @status.setter
    def status(self, value: EnumMetadataNodeStatus) -> None:
        """Set node status."""
        self.basic_info.status = value

    @property
    def health(self) -> EnumRegistryStatus:
        """Node health (delegated to basic_info)."""
        return self.basic_info.health

    @health.setter
    def health(self, value: EnumRegistryStatus) -> None:
        """Set node health."""
        self.basic_info.health = value

    @property
    def supported_operations(self) -> list[str]:
        """Supported operations (delegated to capabilities)."""
        return self.capabilities.supported_operations

    @property
    def dependencies(self) -> list[str]:
        """Node dependencies (delegated to capabilities)."""
        return self.capabilities.dependencies

    @property
    def performance_metrics(self) -> dict[str, float] | None:
        """Performance metrics (delegated to capabilities)."""
        return self.capabilities.performance_metrics

    @performance_metrics.setter
    def performance_metrics(self, value: dict[str, float] | None) -> None:
        """Set performance metrics."""
        self.capabilities.performance_metrics = value

    def is_active(self) -> bool:
        """Check if node is active."""
        return self.basic_info.is_active()

    def is_healthy(self) -> bool:
        """Check if node is healthy."""
        return self.basic_info.is_healthy()

    def has_capabilities(self) -> bool:
        """Check if node has capabilities."""
        return self.capabilities.has_capabilities()

    def add_capability(self, capability: str) -> None:
        """Add a capability."""
        self.capabilities.add_capability(capability)

    def add_operation(self, operation: str) -> None:
        """Add a supported operation."""
        self.capabilities.add_operation(operation)

    def add_dependency(self, dependency: str) -> None:
        """Add a dependency."""
        self.capabilities.add_dependency(dependency)

    def get_information_summary(self) -> dict[str, Any]:
        """Get comprehensive node information summary."""
        basic_summary = self.basic_info.get_basic_summary()
        capabilities_summary = self.capabilities.get_capabilities_summary()
        config_summary = self.configuration.get_configuration_summary()

        return {
            "basic_info": basic_summary,
            "capabilities": capabilities_summary,
            "configuration": config_summary,
            "is_fully_configured": self.is_fully_configured(),
        }

    def is_fully_configured(self) -> bool:
        """Check if node is fully configured."""
        return (
            self.basic_info.has_description()
            and self.capabilities.has_capabilities()
            and self.configuration.is_production_ready()
        )

    @classmethod
    def create_simple(
        cls,
        node_name: str,
        node_type: EnumMetadataNodeType,
        node_version: ModelSemVer,
        description: str | None = None,
    ) -> ModelNodeInformation:
        """Create simple node information."""
        basic_info = ModelNodeBasicInfo.create_simple(
            node_name=node_name,
            node_type=node_type,
            node_version=node_version,
            description=description,
        )
        return cls(basic_info=basic_info)

    @classmethod
    def create_with_capabilities(
        cls,
        node_name: str,
        node_type: EnumMetadataNodeType,
        node_version: ModelSemVer,
        capabilities: list[str],
        operations: list[str] | None = None,
    ) -> ModelNodeInformation:
        """Create node information with capabilities."""
        basic_info = ModelNodeBasicInfo.create_simple(
            node_name=node_name,
            node_type=node_type,
            node_version=node_version,
        )
        caps_info = ModelNodeCapabilitiesInfo.create_with_capabilities(
            capabilities=capabilities,
            operations=operations,
        )
        return cls(basic_info=basic_info, capabilities=caps_info)


# Export for use
__all__ = ["ModelNodeInformation"]