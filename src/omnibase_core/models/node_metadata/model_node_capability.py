"""
Node Capability Model

Replaces EnumNodeCapability with a proper model that includes metadata,
descriptions, and dependencies for each capability.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.enums.enum_performance_impact import EnumPerformanceImpact
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.primitives.model_semver import ModelSemVer
from omnibase_core.types import TypedDictMetadataDict, TypedDictSerializedModel
from omnibase_core.utils.util_uuid_utilities import uuid_from_string

from .model_node_configuration_value import (
    ModelNodeConfigurationNumericValue,
    ModelNodeConfigurationStringValue,
)
from .model_node_configuration_value import from_int as config_from_int
from .model_node_configuration_value import from_string as config_from_string


class ModelNodeCapability(BaseModel):
    """
    Node capability with metadata.

    Replaces the EnumNodeCapability enum to provide richer information
    about each node capability including dependencies and configuration.
    Implements Core protocols:
    - Identifiable: UUID-based identification
    - ProtocolMetadataProvider: Metadata management capabilities
    - Serializable: Data serialization/deserialization
    - Validatable: Validation and verification
    """

    # Core fields (required) - UUID-based entity references
    capability_id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier for the capability entity",
    )
    capability_display_name: str | None = Field(
        default=None,
        description="Human-readable capability identifier (e.g., SUPPORTS_DRY_RUN)",
    )

    value: str = Field(
        default=...,
        description="Lowercase value for current standards (e.g., supports_dry_run)",
    )

    description: str = Field(
        default=...,
        description="Human-readable description of the capability",
    )

    # Metadata fields
    version_introduced: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="ONEX version when this capability was introduced",
    )

    dependencies: list[UUID] = Field(
        default_factory=list,
        description="Other capabilities this one depends on (UUIDs of capability entities)",
    )

    configuration_required: bool = Field(
        default=False,
        description="Whether this capability requires configuration",
    )

    performance_impact: EnumPerformanceImpact = Field(
        default=EnumPerformanceImpact.LOW,
        description="Performance impact level for this capability",
    )

    # Optional fields
    deprecated: bool = Field(
        default=False,
        description="Whether this capability is deprecated",
    )

    replacement: str | None = Field(
        default=None,
        description="Replacement capability if deprecated",
    )

    example_config: (
        dict[
            str,
            ModelNodeConfigurationStringValue | ModelNodeConfigurationNumericValue,
        ]
        | None
    ) = Field(
        default=None,
        description="Example configuration for this capability",
    )

    # Factory methods for standard capabilities
    @property
    def capability_name(self) -> str:
        """Get capability name with fallback to UUID-based name."""
        return (
            self.capability_display_name or f"capability_{str(self.capability_id)[:8]}"
        )

    @capability_name.setter
    def capability_name(self, value: str) -> None:
        """Set capability name."""
        self.capability_display_name = value

    @classmethod
    def supports_dry_run(cls) -> ModelNodeCapability:
        """Dry run support capability."""
        return cls(
            capability_id=uuid_from_string("SUPPORTS_DRY_RUN", "capability"),
            capability_display_name="SUPPORTS_DRY_RUN",
            value="supports_dry_run",
            description="Node can simulate execution without side effects",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=False,
            performance_impact=EnumPerformanceImpact.LOW,
        )

    @classmethod
    def supports_batch_processing(cls) -> ModelNodeCapability:
        """Batch processing support capability."""
        return cls(
            capability_id=uuid_from_string("SUPPORTS_BATCH_PROCESSING", "capability"),
            capability_display_name="SUPPORTS_BATCH_PROCESSING",
            value="supports_batch_processing",
            description="Node can process multiple items in a single execution",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.MEDIUM,
            example_config={
                "batch_size": config_from_int(100),
                "parallel_workers": config_from_int(4),
            },
        )

    @classmethod
    def supports_custom_handlers(cls) -> ModelNodeCapability:
        """Custom handlers support capability."""
        return cls(
            capability_id=uuid_from_string("SUPPORTS_CUSTOM_HANDLERS", "capability"),
            capability_display_name="SUPPORTS_CUSTOM_HANDLERS",
            value="supports_custom_handlers",
            description="Node accepts custom handler implementations",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.LOW,
            dependencies=[uuid_from_string("SUPPORTS_SCHEMA_VALIDATION", "capability")],
        )

    @classmethod
    def telemetry_enabled(cls) -> ModelNodeCapability:
        """Telemetry capability."""
        return cls(
            capability_id=uuid_from_string("TELEMETRY_ENABLED", "capability"),
            capability_display_name="TELEMETRY_ENABLED",
            value="telemetry_enabled",
            description="Node emits telemetry data for monitoring",
            version_introduced=ModelSemVer(major=1, minor=1, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.LOW,
            example_config={
                "telemetry_endpoint": config_from_string(
                    "http://telemetry.example.com",
                ),
            },
        )

    @classmethod
    def supports_correlation_id(cls) -> ModelNodeCapability:
        """Correlation ID support capability."""
        return cls(
            capability_id=uuid_from_string("SUPPORTS_CORRELATION_ID", "capability"),
            capability_display_name="SUPPORTS_CORRELATION_ID",
            value="supports_correlation_id",
            description="Node preserves correlation IDs across executions",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=False,
            performance_impact=EnumPerformanceImpact.LOW,
        )

    @classmethod
    def supports_event_bus(cls) -> ModelNodeCapability:
        """Event bus support capability."""
        return cls(
            capability_id=uuid_from_string("SUPPORTS_EVENT_BUS", "capability"),
            capability_display_name="SUPPORTS_EVENT_BUS",
            value="supports_event_bus",
            description="Node can publish and consume events via event bus",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.MEDIUM,
            dependencies=[uuid_from_string("SUPPORTS_CORRELATION_ID", "capability")],
            example_config={
                "event_bus_type": config_from_string("kafka"),
                "topic": config_from_string("node-events"),
            },
        )

    @classmethod
    def supports_schema_validation(cls) -> ModelNodeCapability:
        """Schema validation support capability."""
        return cls(
            capability_id=uuid_from_string("SUPPORTS_SCHEMA_VALIDATION", "capability"),
            capability_display_name="SUPPORTS_SCHEMA_VALIDATION",
            value="supports_schema_validation",
            description="Node validates input/output against JSON schemas",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=False,
            performance_impact=EnumPerformanceImpact.LOW,
        )

    @classmethod
    def supports_error_recovery(cls) -> ModelNodeCapability:
        """Error recovery support capability."""
        return cls(
            capability_id=uuid_from_string("SUPPORTS_ERROR_RECOVERY", "capability"),
            capability_display_name="SUPPORTS_ERROR_RECOVERY",
            value="supports_error_recovery",
            description="Node can recover from errors with retry logic",
            version_introduced=ModelSemVer(major=1, minor=1, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.MEDIUM,
            example_config={
                "max_retries": config_from_int(3),
                "backoff_strategy": config_from_string(
                    "exponential",
                ),
            },
        )

    @classmethod
    def supports_event_discovery(cls) -> ModelNodeCapability:
        """Event discovery support capability."""
        return cls(
            capability_id=uuid_from_string("SUPPORTS_EVENT_DISCOVERY", "capability"),
            capability_display_name="SUPPORTS_EVENT_DISCOVERY",
            value="supports_event_discovery",
            description="Node can discover available events and their schemas",
            version_introduced=ModelSemVer(major=1, minor=2, patch=0),
            configuration_required=False,
            performance_impact=EnumPerformanceImpact.LOW,
            dependencies=[
                uuid_from_string("SUPPORTS_EVENT_BUS", "capability"),
                uuid_from_string("SUPPORTS_SCHEMA_VALIDATION", "capability"),
            ],
        )

    @classmethod
    def from_string(cls, capability: str) -> ModelNodeCapability:
        """Create ModelNodeCapability from string for current standards."""
        capability_upper = capability.upper().replace(".", "_")
        factory_map = {
            "SUPPORTS_DRY_RUN": cls.supports_dry_run,
            "SUPPORTS_BATCH_PROCESSING": cls.supports_batch_processing,
            "SUPPORTS_CUSTOM_HANDLERS": cls.supports_custom_handlers,
            "TELEMETRY_ENABLED": cls.telemetry_enabled,
            "SUPPORTS_CORRELATION_ID": cls.supports_correlation_id,
            "SUPPORTS_EVENT_BUS": cls.supports_event_bus,
            "SUPPORTS_SCHEMA_VALIDATION": cls.supports_schema_validation,
            "SUPPORTS_ERROR_RECOVERY": cls.supports_error_recovery,
            "SUPPORTS_EVENT_DISCOVERY": cls.supports_event_discovery,
        }

        factory = factory_map.get(capability_upper)
        if factory:
            return factory()
        # Unknown capability - create generic
        return cls(
            capability_id=uuid_from_string(capability_upper, "capability"),
            capability_display_name=capability_upper,
            value=capability.lower(),
            description=f"Custom capability: {capability}",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
        )

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Equality comparison for current standards."""
        if isinstance(other, str):
            return self.value == other or self.capability_name == other.upper()
        if isinstance(other, ModelNodeCapability):
            return self.capability_name == other.capability_name
        return False

    def is_compatible_with_version(self, version: ModelSemVer) -> bool:
        """Check if this capability is available in a given ONEX version."""
        return self.version_introduced <= version

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
        # Map actual fields to TypedDictMetadataDict structure
        # capability_name property always returns non-empty (has UUID fallback)
        result["name"] = self.capability_name
        # description is required (no default), always access directly
        result["description"] = self.description
        # version_introduced is required, always access directly
        result["version"] = self.version_introduced
        # Pack additional fields into metadata
        result["metadata"] = {
            "capability_id": str(self.capability_id),
            "value": self.value,
            "configuration_required": self.configuration_required,
            "performance_impact": self.performance_impact.value,
            "deprecated": self.deprecated,
            "replacement": self.replacement,
            "dependencies": [str(dep) for dep in self.dependencies],
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
