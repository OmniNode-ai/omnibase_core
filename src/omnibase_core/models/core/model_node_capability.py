from typing import Any, Optional

from pydantic import Field

"""
Node Capability Model

Replaces EnumNodeCapability with a proper model that includes metadata,
descriptions, and dependencies for each capability.
"""

from pydantic import BaseModel, Field, field_validator

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.core.model_semver import ModelSemVer, parse_semver_from_string


class ModelNodeCapability(BaseModel):
    """
    Node capability with metadata.

    Replaces the EnumNodeCapability enum to provide richer information
    about each node capability including dependencies and configuration.
    """

    # Core fields (required)
    name: str = Field(
        default=...,
        description="Capability identifier (e.g., SUPPORTS_DRY_RUN)",
        pattern="^[A-Z][A-Z0-9_]*$",
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
        default_factory=lambda: ModelSemVer(major=1, minor=0, patch=0),
        description="ONEX version when this capability was introduced",
    )

    dependencies: list[str] = Field(
        default_factory=list,
        description="Other capabilities this one depends on",
    )

    configuration_required: bool = Field(
        default=False,
        description="Whether this capability requires configuration",
    )

    performance_impact: str = Field(
        default="low",
        description="Performance impact level (low, medium, high)",
        pattern="^(low|medium|high)$",
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

    example_config: dict[str, Any] | None = Field(
        default=None,
        description="Example configuration for this capability",
    )

    @field_validator("version_introduced", mode="before")
    @classmethod
    def validate_version_introduced(cls, v: Any) -> ModelSemVer:
        """Validate and convert version_introduced to ModelSemVer."""
        if isinstance(v, ModelSemVer):
            return v
        if isinstance(v, dict):
            return ModelSemVer(**v)
        if isinstance(v, str):
            from omnibase_core.models.core.model_semver import parse_semver_from_string

            return parse_semver_from_string(v)
        msg = "version_introduced must be ModelSemVer, dict, or str"
        raise ModelOnexError(message=msg, error_code=EnumCoreErrorCode.VALIDATION_ERROR)

    # Factory methods for standard capabilities
    @classmethod
    def SUPPORTS_DRY_RUN(cls) -> "ModelNodeCapability":
        """Dry run support capability."""
        return cls(
            name="SUPPORTS_DRY_RUN",
            value="supports_dry_run",
            description="Node can simulate execution without side effects",
            version_introduced=parse_semver_from_string("1.0.0"),
            configuration_required=False,
            performance_impact="low",
        )

    @classmethod
    def SUPPORTS_BATCH_PROCESSING(cls) -> "ModelNodeCapability":
        """Batch processing support capability."""
        return cls(
            name="SUPPORTS_BATCH_PROCESSING",
            value="supports_batch_processing",
            description="Node can process multiple items in a single execution",
            version_introduced=parse_semver_from_string("1.0.0"),
            configuration_required=True,
            performance_impact="medium",
            example_config={"batch_size": 100, "parallel_workers": 4},
        )

    @classmethod
    def SUPPORTS_CUSTOM_HANDLERS(cls) -> "ModelNodeCapability":
        """Custom handlers support capability."""
        return cls(
            name="SUPPORTS_CUSTOM_HANDLERS",
            value="supports_custom_handlers",
            description="Node accepts custom handler implementations",
            version_introduced=parse_semver_from_string("1.0.0"),
            configuration_required=True,
            performance_impact="low",
            dependencies=["SUPPORTS_SCHEMA_VALIDATION"],
        )

    @classmethod
    def TELEMETRY_ENABLED(cls) -> "ModelNodeCapability":
        """Telemetry capability."""
        return cls(
            name="TELEMETRY_ENABLED",
            value="telemetry_enabled",
            description="Node emits telemetry data for monitoring",
            version_introduced=parse_semver_from_string("1.1.0"),
            configuration_required=True,
            performance_impact="low",
            example_config={"telemetry_endpoint": "http://telemetry.example.com"},
        )

    @classmethod
    def SUPPORTS_CORRELATION_ID(cls) -> "ModelNodeCapability":
        """Correlation ID support capability."""
        return cls(
            name="SUPPORTS_CORRELATION_ID",
            value="supports_correlation_id",
            description="Node preserves correlation IDs across executions",
            version_introduced=parse_semver_from_string("1.0.0"),
            configuration_required=False,
            performance_impact="low",
        )

    @classmethod
    def SUPPORTS_EVENT_BUS(cls) -> "ModelNodeCapability":
        """Event bus support capability."""
        return cls(
            name="SUPPORTS_EVENT_BUS",
            value="supports_event_bus",
            description="Node can publish and consume events via event bus",
            version_introduced=parse_semver_from_string("1.0.0"),
            configuration_required=True,
            performance_impact="medium",
            dependencies=["SUPPORTS_CORRELATION_ID"],
            example_config={"event_bus_type": "kafka", "topic": "node-events"},
        )

    @classmethod
    def SUPPORTS_SCHEMA_VALIDATION(cls) -> "ModelNodeCapability":
        """Schema validation support capability."""
        return cls(
            name="SUPPORTS_SCHEMA_VALIDATION",
            value="supports_schema_validation",
            description="Node validates input/output against JSON schemas",
            version_introduced=parse_semver_from_string("1.0.0"),
            configuration_required=False,
            performance_impact="low",
        )

    @classmethod
    def SUPPORTS_ERROR_RECOVERY(cls) -> "ModelNodeCapability":
        """Error recovery support capability."""
        return cls(
            name="SUPPORTS_ERROR_RECOVERY",
            value="supports_error_recovery",
            description="Node can recover from errors with retry logic",
            version_introduced=parse_semver_from_string("1.1.0"),
            configuration_required=True,
            performance_impact="medium",
            example_config={"max_retries": 3, "backoff_strategy": "exponential"},
        )

    @classmethod
    def SUPPORTS_EVENT_DISCOVERY(cls) -> "ModelNodeCapability":
        """Event discovery support capability."""
        return cls(
            name="SUPPORTS_EVENT_DISCOVERY",
            value="supports_event_discovery",
            description="Node can discover available events and their schemas",
            version_introduced=parse_semver_from_string("1.2.0"),
            configuration_required=False,
            performance_impact="low",
            dependencies=["SUPPORTS_EVENT_BUS", "SUPPORTS_SCHEMA_VALIDATION"],
        )

    @classmethod
    def from_string(cls, capability: str) -> "ModelNodeCapability":
        """Create ModelNodeCapability from string for current standards."""
        capability_upper = capability.upper().replace(".", "_")
        factory_map = {
            "SUPPORTS_DRY_RUN": cls.SUPPORTS_DRY_RUN,
            "SUPPORTS_BATCH_PROCESSING": cls.SUPPORTS_BATCH_PROCESSING,
            "SUPPORTS_CUSTOM_HANDLERS": cls.SUPPORTS_CUSTOM_HANDLERS,
            "TELEMETRY_ENABLED": cls.TELEMETRY_ENABLED,
            "SUPPORTS_CORRELATION_ID": cls.SUPPORTS_CORRELATION_ID,
            "SUPPORTS_EVENT_BUS": cls.SUPPORTS_EVENT_BUS,
            "SUPPORTS_SCHEMA_VALIDATION": cls.SUPPORTS_SCHEMA_VALIDATION,
            "SUPPORTS_ERROR_RECOVERY": cls.SUPPORTS_ERROR_RECOVERY,
            "SUPPORTS_EVENT_DISCOVERY": cls.SUPPORTS_EVENT_DISCOVERY,
        }

        factory = factory_map.get(capability_upper)
        if factory:
            return factory()
        # Unknown capability - create generic
        return cls(
            name=capability_upper,
            value=capability.lower(),
            description=f"Custom capability: {capability}",
            version_introduced=parse_semver_from_string("1.0.0"),
        )

    def __str__(self) -> str:
        """String representation for current standards."""
        return self.value

    def __eq__(self, other: object) -> bool:
        """Equality comparison for current standards."""
        if isinstance(other, str):
            return self.value == other or self.name == other.upper()
        if isinstance(other, ModelNodeCapability):
            return self.name == other.name
        return False

    def is_compatible_with_version(self, version: str) -> bool:
        """Check if this capability is available in a given ONEX version."""
        # Parse the version string to ModelSemVer for comparison
        target_version = parse_semver_from_string(version)
        return self.version_introduced <= target_version
