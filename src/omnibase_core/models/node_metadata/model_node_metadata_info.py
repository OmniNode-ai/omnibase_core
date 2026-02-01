"""
Node Metadata Info Model.

Simple model for node metadata information used in CLI output.
"""

from __future__ import annotations

from uuid import UUID, uuid4

# Import SPI protocol directly - no fallback pattern per ONEX standards
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_category import EnumCategory
from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_health_status import EnumHealthStatus
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.metadata.model_metadata_value import ModelMetadataValue
from omnibase_core.models.metadata.node_info import ModelNodePerformanceMetrics
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.types.typed_dict_node_metadata_summary import (
    TypedDictNodeMetadataSummary,
)

from .model_node_core_metadata import ModelNodeCoreMetadata
from .model_node_organization_metadata import ModelNodeOrganizationMetadata


class ModelNodeMetadataInfo(BaseModel):
    """
    Node metadata information model.

    Restructured to use focused sub-models for better organization.
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Composed sub-models (3 primary components)
    core: ModelNodeCoreMetadata = Field(
        default_factory=lambda: ModelNodeCoreMetadata(
            node_display_name="",
            node_type=EnumMetadataNodeType.FUNCTION,
        ),
        description="Core node metadata",
    )
    performance: ModelNodePerformanceMetrics = Field(
        default_factory=lambda: ModelNodePerformanceMetrics(),
        description="Performance metrics",
    )
    organization: ModelNodeOrganizationMetadata = Field(
        default_factory=lambda: ModelNodeOrganizationMetadata(),
        description="Organization metadata",
    )

    # Delegation properties
    @property
    def node_id(self) -> UUID:
        return self.core.node_id

    @node_id.setter
    def node_id(self, value: UUID) -> None:
        self.core.node_id = value

    @property
    def node_name(self) -> str:
        return self.core.node_name

    @node_name.setter
    def node_name(self, value: str) -> None:
        self.core.node_name = value

    @property
    def node_type(self) -> EnumMetadataNodeType:
        return self.core.node_type

    @node_type.setter
    def node_type(self, value: EnumMetadataNodeType) -> None:
        self.core.node_type = value

    @property
    def status(self) -> EnumMetadataNodeStatus:
        return self.core.status

    @status.setter
    def status(self, value: EnumMetadataNodeStatus) -> None:
        self.core.status = value

    @property
    def health(self) -> str:
        return self.core.health.value

    @health.setter
    def health(self, value: str) -> None:
        try:
            self.core.health = EnumHealthStatus(value)
        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid health status '{value}': {e}",
            ) from e

    @property
    def version(self) -> ModelSemVer | None:
        return self.core.version

    @version.setter
    def version(self, value: ModelSemVer | None) -> None:
        self.core.version = value

    @property
    def description(self) -> str | None:
        return self.organization.description

    @description.setter
    def description(self, value: str | None) -> None:
        self.organization.description = value

    @property
    def author(self) -> str | None:
        return self.organization.author

    @author.setter
    def author(self, value: str | None) -> None:
        self.organization.author = value

    @property
    def capabilities(self) -> list[str]:
        return self.organization.capabilities

    @property
    def tags(self) -> list[str]:
        return self.organization.tags

    @property
    def categories(self) -> list[EnumCategory]:
        return self.organization.categories

    @property
    def dependencies(self) -> list[UUID]:
        return self.organization.dependencies

    @property
    def dependents(self) -> list[UUID]:
        return self.organization.dependents

    @property
    def usage_count(self) -> int:
        return self.performance.usage_count

    @property
    def error_rate(self) -> float:
        return self.performance.error_rate

    @property
    def success_rate(self) -> float:
        return self.performance.success_rate

    @property
    def custom_metadata(self) -> dict[str, ModelMetadataValue]:
        # Convert from typed custom properties to ModelMetadataValue format
        result: dict[str, ModelMetadataValue] = {}
        if self.organization.custom_properties.custom_strings:
            for key, val in self.organization.custom_properties.custom_strings.items():
                result[key] = ModelMetadataValue.from_string(val, "custom_strings")
        if self.organization.custom_properties.custom_numbers:
            for item in self.organization.custom_properties.custom_numbers.items():
                num_key: str = item[0]
                num_val: float = item[1]
                result[num_key] = ModelMetadataValue.from_any(num_val, "custom_numbers")
        if self.organization.custom_properties.custom_flags:
            for item in self.organization.custom_properties.custom_flags.items():
                flag_key: str = item[0]
                flag_val: bool = item[1]
                result[flag_key] = ModelMetadataValue.from_bool(
                    flag_val,
                    "custom_flags",
                )
        return result

    @custom_metadata.setter
    def custom_metadata(self, value: dict[str, ModelMetadataValue]) -> None:
        """Set custom metadata (convert from ModelMetadataValue to typed properties)."""
        for key, metadata_val in value.items():
            python_val = metadata_val.to_python_value()
            if isinstance(python_val, str):
                self.organization.custom_properties.custom_strings[key] = python_val
            elif isinstance(
                python_val,
                bool,
            ):  # Check bool before int since bool is a subclass of int
                self.organization.custom_properties.custom_flags[key] = python_val
            elif isinstance(python_val, (int, float)):
                self.organization.custom_properties.custom_numbers[key] = python_val

    def is_active(self) -> bool:
        return self.core.is_active()

    def is_healthy(self) -> bool:
        return self.core.is_healthy()

    def has_errors(self) -> bool:
        return self.performance.error_rate > 0.0

    def get_success_rate(self) -> float:
        return self.performance.success_rate

    def is_high_usage(self) -> bool:
        return self.performance.is_high_usage

    def add_tag(self, tag: str) -> None:
        self.organization.add_tag(tag)

    def remove_tag(self, tag: str) -> None:
        self.organization.remove_tag(tag)

    def add_capability(self, capability: str) -> None:
        self.organization.add_capability(capability)

    def has_capability(self, capability: str) -> bool:
        return self.organization.has_capability(capability)

    def add_category(self, category: EnumCategory) -> None:
        self.organization.add_category(category)

    def add_execution_sample(
        self,
        execution_time_ms: float,
        success: bool,
        memory_usage_mb: float = 0.0,
    ) -> None:
        """Add execution sample to performance metrics."""
        self.performance.add_execution_sample(
            execution_time_ms,
            success,
            memory_usage_mb,
        )

    def get_summary(self) -> TypedDictNodeMetadataSummary:
        # Get organization summary (core and performance data accessed via properties)
        org_summary = self.organization.get_organization_summary()

        return {
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_type": self.node_type.value,
            "status": self.status.value,
            "health": self.health,
            "version": self.core.version,
            "usage_count": self.usage_count,
            "error_rate": self.error_rate,
            "success_rate": self.success_rate,
            "capabilities": self.capabilities,
            "tags": self.tags,
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
            "has_errors": self.has_errors(),
            "capabilities_count": int(org_summary["capabilities_count"]),
            "tags_count": int(org_summary["tags_count"]),
            "is_high_usage": self.performance.is_high_usage,
        }

    @classmethod
    def create_simple(
        cls,
        node_id: UUID,
        node_name: str,
        node_type: EnumMetadataNodeType = EnumMetadataNodeType.FUNCTION,
    ) -> ModelNodeMetadataInfo:
        core = ModelNodeCoreMetadata(
            node_id=node_id,
            node_display_name=node_name,
            node_type=node_type,
        )
        return cls(
            core=core,
            performance=ModelNodePerformanceMetrics.create_unused(),
            organization=ModelNodeOrganizationMetadata(),
        )

    @classmethod
    def from_node_info(
        cls, node_info: TypedDictSerializedModel
    ) -> ModelNodeMetadataInfo:
        # Extract basic information and distribute to sub-models
        core = ModelNodeCoreMetadata(
            node_id=getattr(node_info, "node_id", uuid4()),
            node_display_name=getattr(node_info, "node_name", "unknown"),
            node_type=getattr(node_info, "node_type", EnumMetadataNodeType.FUNCTION),
            version=getattr(node_info, "version", None),
            status=getattr(node_info, "status", EnumMetadataNodeStatus.ACTIVE),
        )

        # Handle health with enum conversion
        health_str = getattr(node_info, "health", "healthy")
        try:
            core.health = EnumHealthStatus(health_str)
        except ValueError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid health status '{health_str}': {e}",
            ) from e

        organization = ModelNodeOrganizationMetadata(
            description=getattr(node_info, "description", None),
            author=getattr(node_info, "author", None),
        )

        return cls(
            core=core,
            performance=ModelNodePerformanceMetrics.create_unused(),
            organization=organization,
        )

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
        if self.version:
            result["version"] = self.version
        if self.tags:
            result["tags"] = self.tags
        # Pack additional fields into metadata
        result["metadata"] = {
            "node_id": str(self.node_id),
            "node_type": self.node_type.value,
            "status": self.status.value,
            "health": self.health,
            "author": self.author,
            "is_active": self.is_active(),
            "is_healthy": self.is_healthy(),
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


# NOTE: model_rebuild() not needed - Pydantic v2 handles forward references automatically
# ModelMetadataValue is imported at runtime, Pydantic will resolve references lazily

# Export for use
__all__ = ["ModelNodeMetadataInfo"]
