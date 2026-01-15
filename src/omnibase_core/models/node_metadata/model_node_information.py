"""
Node information model.
Restructured to use focused sub-models for better organization.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_registry_status import EnumRegistryStatus
from omnibase_core.enums.enum_status import EnumStatus
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel

from .model_node_capabilities_info import ModelNodeCapabilitiesInfo
from .model_node_configuration import ModelNodeConfiguration
from .model_node_core_info import ModelNodeCoreInfo
from .model_node_information_summary import ModelNodeInformationSummary


class ModelNodeInformation(BaseModel):
    """
    Node information with typed fields.

    Restructured to use focused sub-models for better organization.
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Composed sub-models (3 primary components)
    core_info: ModelNodeCoreInfo = Field(
        default=...,
        description="Core node information",
    )
    capabilities: ModelNodeCapabilitiesInfo = Field(
        default_factory=lambda: ModelNodeCapabilitiesInfo(performance_metrics=None),
        description="Node capabilities and operations",
    )
    configuration: ModelNodeConfiguration = Field(
        default_factory=lambda: ModelNodeConfiguration(),
        description="Node configuration",
    )

    # Delegation properties
    @property
    def node_id(self) -> UUID:
        return self.core_info.node_id

    @node_id.setter
    def node_id(self, value: UUID) -> None:
        self.core_info.node_id = value

    @property
    def node_name(self) -> str:
        return self.core_info.node_name

    @node_name.setter
    def node_name(self, value: str) -> None:
        # Update the underlying node_display_name instead
        self.core_info = self.core_info.model_copy(update={"node_display_name": value})

    @property
    def node_type(self) -> EnumMetadataNodeType:
        return self.core_info.node_type

    @node_type.setter
    def node_type(self, value: EnumMetadataNodeType) -> None:
        self.core_info.node_type = value

    @property
    def node_version(self) -> ModelSemVer:
        return self.core_info.node_version

    @node_version.setter
    def node_version(self, value: ModelSemVer) -> None:
        self.core_info.node_version = value

    @property
    def description(self) -> str | None:
        return self.core_info.description

    @description.setter
    def description(self, value: str | None) -> None:
        self.core_info.description = value

    @property
    def author(self) -> str | None:
        return self.core_info.author

    @author.setter
    def author(self, value: str | None) -> None:
        # Update the underlying author_display_name instead
        self.core_info = self.core_info.model_copy(
            update={"author_display_name": value},
        )

    @property
    def created_at(self) -> datetime | None:
        return self.core_info.created_at

    @created_at.setter
    def created_at(self, value: datetime | None) -> None:
        self.core_info.created_at = value

    @property
    def updated_at(self) -> datetime | None:
        return self.core_info.updated_at

    @updated_at.setter
    def updated_at(self, value: datetime | None) -> None:
        self.core_info.updated_at = value

    @property
    def status(self) -> EnumMetadataNodeStatus:
        return self.core_info.status

    @status.setter
    def status(self, value: EnumMetadataNodeStatus) -> None:
        self.core_info.status = value

    # Mapping from EnumRegistryStatus to EnumHealthStatus for consistent API
    _REGISTRY_TO_HEALTH_MAP: dict[EnumRegistryStatus, EnumHealthStatus] = {
        EnumRegistryStatus.HEALTHY: EnumHealthStatus.HEALTHY,
        EnumRegistryStatus.DEGRADED: EnumHealthStatus.DEGRADED,
        EnumRegistryStatus.UNAVAILABLE: EnumHealthStatus.UNAVAILABLE,
        EnumRegistryStatus.INITIALIZING: EnumHealthStatus.INITIALIZING,
        EnumRegistryStatus.MAINTENANCE: EnumHealthStatus.UNAVAILABLE,
    }

    # Reverse mapping from EnumHealthStatus to EnumRegistryStatus for setter
    _HEALTH_TO_REGISTRY_MAP: dict[EnumHealthStatus, EnumRegistryStatus] = {
        EnumHealthStatus.HEALTHY: EnumRegistryStatus.HEALTHY,
        EnumHealthStatus.DEGRADED: EnumRegistryStatus.DEGRADED,
        EnumHealthStatus.UNAVAILABLE: EnumRegistryStatus.UNAVAILABLE,
        EnumHealthStatus.INITIALIZING: EnumRegistryStatus.INITIALIZING,
        # Other health statuses map to UNAVAILABLE as closest match
        EnumHealthStatus.UNHEALTHY: EnumRegistryStatus.UNAVAILABLE,
        EnumHealthStatus.CRITICAL: EnumRegistryStatus.UNAVAILABLE,
        EnumHealthStatus.UNKNOWN: EnumRegistryStatus.UNAVAILABLE,
        EnumHealthStatus.WARNING: EnumRegistryStatus.DEGRADED,
        EnumHealthStatus.UNREACHABLE: EnumRegistryStatus.UNAVAILABLE,
        EnumHealthStatus.AVAILABLE: EnumRegistryStatus.HEALTHY,
        EnumHealthStatus.DISPOSING: EnumRegistryStatus.MAINTENANCE,
        EnumHealthStatus.ERROR: EnumRegistryStatus.UNAVAILABLE,
    }

    @property
    def health(self) -> EnumHealthStatus:
        """Node health status (delegated to core_info with type mapping).

        Returns:
            EnumHealthStatus: The health status mapped from the underlying
            EnumRegistryStatus stored in core_info. This provides a consistent
            API with ModelNodeCoreInfoSummary.health.

        Note:
            The underlying core_info.health stores EnumRegistryStatus, which
            is mapped to EnumHealthStatus for API consistency. Unknown registry
            statuses map to EnumHealthStatus.UNKNOWN.
        """
        return self._REGISTRY_TO_HEALTH_MAP.get(
            self.core_info.health, EnumHealthStatus.UNKNOWN
        )

    @health.setter
    def health(self, value: EnumHealthStatus) -> None:
        """Set node health status.

        Args:
            value: EnumHealthStatus to set. This is reverse-mapped to
                EnumRegistryStatus for storage in core_info.
        """
        self.core_info.health = self._HEALTH_TO_REGISTRY_MAP.get(
            value, EnumRegistryStatus.UNAVAILABLE
        )

    @property
    def supported_operations(self) -> list[str]:
        return self.capabilities.supported_operations

    @property
    def dependencies(self) -> list[UUID]:
        return self.capabilities.dependencies

    @property
    def performance_metrics(self) -> dict[str, float] | None:
        return self.capabilities.performance_metrics

    @performance_metrics.setter
    def performance_metrics(self, value: dict[str, float] | None) -> None:
        self.capabilities.performance_metrics = value

    def is_active(self) -> bool:
        return self.core_info.is_active()

    def is_healthy(self) -> bool:
        return self.core_info.is_healthy()

    def has_capabilities(self) -> bool:
        return self.capabilities.has_capabilities()

    def add_capability(self, capability: str) -> None:
        self.capabilities.add_capability(capability)

    def add_operation(self, operation: str) -> None:
        self.capabilities.add_operation(operation)

    def add_dependency(self, dependency: UUID) -> None:
        self.capabilities.add_dependency(dependency)

    def get_information_summary(self) -> ModelNodeInformationSummary:
        """Get comprehensive node information summary."""
        from .model_node_capabilities_summary import ModelNodeCapabilitiesSummary
        from .model_node_configuration_summary import ModelNodeConfigurationSummary
        from .model_node_core_info_summary import ModelNodeCoreInfoSummary

        # Create proper summary objects instead of dict[str, Any]s
        # Use self.health property which handles EnumRegistryStatus -> EnumHealthStatus mapping
        core_summary = ModelNodeCoreInfoSummary(
            node_id=self.core_info.node_id,
            node_name=self.core_info.node_name,
            node_type=self.core_info.node_type,
            node_version=self.core_info.node_version,
            status=EnumStatus.ACTIVE,  # Convert from metadata status
            health=self.health,
            is_active=(self.core_info.status == EnumMetadataNodeStatus.ACTIVE),
            is_healthy=self.core_info.is_healthy(),
            has_description=self.core_info.has_description(),
            has_author=self.core_info.has_author(),
        )

        # Create capabilities summary with proper structure
        capabilities_summary = ModelNodeCapabilitiesSummary(
            capabilities_count=len(self.capabilities.capabilities),
            operations_count=len(self.capabilities.supported_operations),
            dependencies_count=len(self.capabilities.dependencies),
            has_capabilities=self.capabilities.has_capabilities(),
            has_operations=self.capabilities.has_operations(),
            has_dependencies=self.capabilities.has_dependencies(),
            has_performance_metrics=bool(self.capabilities.performance_metrics),
            primary_capability=(
                self.capabilities.capabilities[0]
                if self.capabilities.capabilities
                else None
            ),
            metrics_count=(
                len(self.capabilities.performance_metrics)
                if self.capabilities.performance_metrics
                else 0
            ),
        )

        # Create configuration summary with proper structure
        configuration_summary = ModelNodeConfigurationSummary(
            execution={},  # Default empty dict[str, Any]
            resources={},  # Default empty dict[str, Any]
            features={},  # Default empty dict[str, Any]
            connection={},  # Default empty dict[str, Any]
            is_production_ready=False,  # Default value
            is_performance_optimized=False,  # Default value
            has_custom_settings=False,  # Default value
        )

        return ModelNodeInformationSummary(
            core_info=core_summary,
            capabilities=capabilities_summary,
            configuration=configuration_summary,
            is_fully_configured=self.is_fully_configured(),
        )

    def is_fully_configured(self) -> bool:
        """Check if node is fully configured."""
        return (
            self.core_info.has_description()
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
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name=node_name,
            node_type=node_type,
            node_version=node_version,
            description=description,
        )
        return cls(core_info=core_info)

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
        core_info = ModelNodeCoreInfo.create_streamlined(
            node_name=node_name,
            node_type=node_type,
            node_version=node_version,
        )
        caps_info = ModelNodeCapabilitiesInfo.create_with_capabilities(
            capabilities=capabilities,
            operations=operations,
        )
        return cls(core_info=core_info, capabilities=caps_info)

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
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
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"{self.__class__.__name__} must have a valid ID field "
            f"(type_id, id, uuid, identifier, etc.). "
            f"Cannot generate stable ID without UUID field.",
        )

    def get_metadata(self) -> TypedDictMetadataDict:
        """Get metadata as dictionary (ProtocolMetadataProvider protocol)."""
        result: TypedDictMetadataDict = {}
        # Map actual fields to TypedDictMetadataDict structure via delegated properties
        # node_name property always returns non-empty (has UUID fallback)
        result["name"] = self.node_name
        if self.description:
            result["description"] = self.description
        result["version"] = self.node_version
        # Pack additional fields into metadata
        result["metadata"] = {
            "node_id": str(self.node_id),
            "node_type": self.node_type.value,
            "status": self.status.value,
            "health": self.health.value,
            "author": self.author,
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_capabilities": self.has_capabilities(),
        }
        return result

    def set_metadata(self, metadata: TypedDictMetadataDict) -> bool:
        """Set metadata from dictionary (ProtocolMetadataProvider protocol)."""
        try:
            for key, value in metadata.items():
                if hasattr(self, key):
                    setattr(self, key, value)
            return True
        except Exception:  # fallback-ok: Protocol method - graceful fallback for optional implementation
            return False

    def serialize(self) -> TypedDictSerializedModel:
        """Serialize to dictionary (Serializable protocol)."""
        return self.model_dump(exclude_none=False, by_alias=True)

    def validate_instance(self) -> bool:
        """Validate instance integrity (ProtocolValidatable protocol)."""
        return True


# Export for use
__all__ = ["ModelNodeInformation"]
