"""
Node Capability Model

Replaces EnumNodeCapability with a proper model that includes metadata,
descriptions, and dependencies for each capability.
"""

from typing import Any

from pydantic import BaseModel, Field

from ...enums.enum_performance_impact import EnumPerformanceImpact
from ..metadata.model_semver import ModelSemVer


class ModelNodeCapability(BaseModel):
    """
    Node capability with metadata.

    Replaces the EnumNodeCapability enum to provide richer information
    about each node capability including dependencies and configuration.
    """

    # Core fields (required)
    name: str = Field(
        ...,
        description="Capability identifier (e.g., SUPPORTS_DRY_RUN)",
        pattern="^[A-Z][A-Z0-9_]*$",
    )

    value: str = Field(
        ...,
        description="Lowercase value for current standards (e.g., supports_dry_run)",
    )

    description: str = Field(
        ...,
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

    example_config: dict[str, str | int | bool] | None = Field(
        default=None,
        description="Example configuration for this capability",
    )

    # Factory methods for standard capabilities
    @classmethod
    def supports_dry_run(cls) -> "ModelNodeCapability":
        """Dry run support capability."""
        return cls(
            name="SUPPORTS_DRY_RUN",
            value="supports_dry_run",
            description="Node can simulate execution without side effects",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=False,
            performance_impact=EnumPerformanceImpact.LOW,
        )

    @classmethod
    def supports_batch_processing(cls) -> "ModelNodeCapability":
        """Batch processing support capability."""
        return cls(
            name="SUPPORTS_BATCH_PROCESSING",
            value="supports_batch_processing",
            description="Node can process multiple items in a single execution",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.MEDIUM,
            example_config={"batch_size": 100, "parallel_workers": 4},
        )

    @classmethod
    def supports_custom_handlers(cls) -> "ModelNodeCapability":
        """Custom handlers support capability."""
        return cls(
            name="SUPPORTS_CUSTOM_HANDLERS",
            value="supports_custom_handlers",
            description="Node accepts custom handler implementations",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.LOW,
            dependencies=["SUPPORTS_SCHEMA_VALIDATION"],
        )

    @classmethod
    def telemetry_enabled(cls) -> "ModelNodeCapability":
        """Telemetry capability."""
        return cls(
            name="TELEMETRY_ENABLED",
            value="telemetry_enabled",
            description="Node emits telemetry data for monitoring",
            version_introduced=ModelSemVer(major=1, minor=1, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.LOW,
            example_config={"telemetry_endpoint": "http://telemetry.example.com"},
        )

    @classmethod
    def supports_correlation_id(cls) -> "ModelNodeCapability":
        """Correlation ID support capability."""
        return cls(
            name="SUPPORTS_CORRELATION_ID",
            value="supports_correlation_id",
            description="Node preserves correlation IDs across executions",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=False,
            performance_impact=EnumPerformanceImpact.LOW,
        )

    @classmethod
    def supports_event_bus(cls) -> "ModelNodeCapability":
        """Event bus support capability."""
        return cls(
            name="SUPPORTS_EVENT_BUS",
            value="supports_event_bus",
            description="Node can publish and consume events via event bus",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.MEDIUM,
            dependencies=["SUPPORTS_CORRELATION_ID"],
            example_config={"event_bus_type": "kafka", "topic": "node-events"},
        )

    @classmethod
    def supports_schema_validation(cls) -> "ModelNodeCapability":
        """Schema validation support capability."""
        return cls(
            name="SUPPORTS_SCHEMA_VALIDATION",
            value="supports_schema_validation",
            description="Node validates input/output against JSON schemas",
            version_introduced=ModelSemVer(major=1, minor=0, patch=0),
            configuration_required=False,
            performance_impact=EnumPerformanceImpact.LOW,
        )

    @classmethod
    def supports_error_recovery(cls) -> "ModelNodeCapability":
        """Error recovery support capability."""
        return cls(
            name="SUPPORTS_ERROR_RECOVERY",
            value="supports_error_recovery",
            description="Node can recover from errors with retry logic",
            version_introduced=ModelSemVer(major=1, minor=1, patch=0),
            configuration_required=True,
            performance_impact=EnumPerformanceImpact.MEDIUM,
            example_config={"max_retries": 3, "backoff_strategy": "exponential"},
        )

    @classmethod
    def supports_event_discovery(cls) -> "ModelNodeCapability":
        """Event discovery support capability."""
        return cls(
            name="SUPPORTS_EVENT_DISCOVERY",
            value="supports_event_discovery",
            description="Node can discover available events and their schemas",
            version_introduced=ModelSemVer(major=1, minor=2, patch=0),
            configuration_required=False,
            performance_impact=EnumPerformanceImpact.LOW,
            dependencies=["SUPPORTS_EVENT_BUS", "SUPPORTS_SCHEMA_VALIDATION"],
        )

    @classmethod
    def from_string(cls, capability: str) -> "ModelNodeCapability":
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
            name=capability_upper,
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
            return self.value == other or self.name == other.upper()
        if isinstance(other, ModelNodeCapability):
            return self.name == other.name
        return False

    def is_compatible_with_version(self, version: ModelSemVer) -> bool:
        """Check if this capability is available in a given ONEX version."""
        return self.version_introduced <= version
