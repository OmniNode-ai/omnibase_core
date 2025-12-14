from uuid import UUID

from pydantic import Field

from omnibase_core.enums.enum_discovery_phase import EnumDiscoveryPhase
from omnibase_core.enums.enum_event_type import EnumEventType
from omnibase_core.enums.enum_service_status import EnumServiceStatus
from omnibase_core.models.primitives.model_semver import ModelSemVer

__all__ = [
    "EnumDiscoveryPhase",
    "EnumEventType",
    "EnumServiceStatus",
    "ModelEventDescriptor",
]

"""Event Descriptor model for ONEX Discovery & Integration Event Registry.

This module defines the core EventDescriptor structure used for event-driven service
discovery and Container Adapter coordination throughout the ONEX ecosystem.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict


class ModelEventDescriptor(BaseModel):
    """Core EventDescriptor structure for ONEX Discovery & Integration.

    This model defines the complete event structure used for Container Adapter
    pattern coordination and service discovery via Consul service registry.

    The EventDescriptor serves as the primary data structure for all event-driven
    operations in the ONEX ecosystem, including service discovery, registration,
    and mesh coordination.

    Examples:
        >>> from datetime import datetime
        >>> from uuid import UUID
        >>> from omnibase_core.models.primitives.model_semver import ModelSemVer
        >>>
        >>> # Create a basic service registration event
        >>> event = ModelEventDescriptor(
        ...     event_id=UUID("12345678-1234-5678-1234-567812345678"),
        ...     event_type=EnumEventType.SERVICE_REGISTRATION,
        ...     event_name="Register User Service",
        ...     service_id=UUID("87654321-4321-8765-4321-876543218765"),
        ...     service_name="user-service",
        ...     service_version=ModelSemVer(major=1, minor=0, patch=0),
        ...     discovery_phase=EnumDiscoveryPhase.PHASE_1_SIMPLE,
        ...     consul_service_name="onex-user-service",
        ...     container_status=EnumServiceStatus.ACTIVE,
        ...     event_schema_version=ModelSemVer(major=1, minor=0, patch=0)
        ... )
        >>>
        >>> # Event with Consul metadata
        >>> event_with_meta = ModelEventDescriptor(
        ...     event_id=UUID("11111111-2222-3333-4444-555555555555"),
        ...     event_type=EnumEventType.SERVICE_DISCOVERY,
        ...     event_name="Discover Auth Services",
        ...     service_id=UUID("66666666-7777-8888-9999-000000000000"),
        ...     service_name="auth-discovery",
        ...     service_version=ModelSemVer(major=2, minor=1, patch=0),
        ...     discovery_phase=EnumDiscoveryPhase.PHASE_2_AUTO_PROVISION,
        ...     consul_service_name="onex-auth-discovery",
        ...     consul_tags=["auth", "security", "oauth"],
        ...     consul_meta={"environment": "production", "region": "us-west-2"},
        ...     container_status=EnumServiceStatus.PROVISIONING,
        ...     health_check_endpoint="/health",
        ...     service_endpoints={"api": "https://api.auth.example.com", "admin": "https://admin.auth.example.com"},
        ...     event_schema_version=ModelSemVer(major=1, minor=0, patch=0)
        ... )

    Attributes:
        event_id: Unique identifier for the event (required)
        event_type: Type of event from EventTypeEnum (required)
        event_name: Human-readable event name (required)
        service_id: Unique service identifier (required)
        service_name: Service name for Consul registration (required)
        service_version: Service version (required)
        discovery_phase: Current discovery implementation phase (required)
        consul_service_name: Consul service registry name (required)
        container_status: Current container/service status (required)
        correlation_id: Optional correlation ID for request/response matching
        node_id: Optional node ID hosting the service
        consul_tags: List of Consul service tags (default: empty list[Any])
        consul_meta: Dict of Consul service metadata (default: empty dict[str, Any])
        container_adapter_enabled: Whether Container Adapter pattern is active (default: True)
        health_check_endpoint: Optional health check endpoint for Consul
        event_data: Event-specific data payload (default: empty dict[str, Any])
        event_context: Event execution context (default: empty dict[str, Any])
        event_timestamp: Event creation timestamp (default: current UTC time)
        hub_domain: Optional hub domain for integration
        hub_registration_required: Whether hub should register in Consul (default: True)
        service_endpoints: Service endpoint mappings (default: empty dict[str, Any])
        mesh_coordination_data: Full mesh coordination data (default: empty dict[str, Any])
        auto_provisioning_config: Optional auto-provisioning configuration
        trust_level: Trust level for service (default: "medium")
        validation_required: Whether event requires validation (default: True)
        event_schema_version: EventDescriptor schema version (required, structured format)
    """

    # Core Event Identity
    event_id: UUID = Field(default=..., description="Unique identifier for this event")
    event_type: EnumEventType = Field(
        default=..., description="Type of event being described"
    )
    event_name: str = Field(default=..., description="Human-readable event name")
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID for request/response matching",
    )

    # Service Identity
    service_id: UUID = Field(default=..., description="Unique service identifier")
    service_name: str = Field(
        default=..., description="Service name for Consul registration"
    )
    service_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Service version",
    )
    node_id: UUID | None = Field(
        default=None, description="Node ID hosting the service"
    )

    # Discovery & Registry Information
    discovery_phase: EnumDiscoveryPhase = Field(
        default=...,
        description="Current discovery implementation phase",
    )
    consul_service_name: str = Field(
        default=..., description="Consul service registry name"
    )
    consul_tags: list[str] = Field(
        default_factory=list,
        description="Consul service tags",
    )
    consul_meta: dict[str, str] = Field(
        default_factory=dict,
        description="Consul service metadata",
    )

    # Container Adapter Coordination
    container_adapter_enabled: bool = Field(
        default=True,
        description="Whether Container Adapter pattern is active",
    )
    container_status: EnumServiceStatus = Field(
        default=...,
        description="Current container/service status",
    )
    health_check_endpoint: str | None = Field(
        default=None,
        description="Health check endpoint for Consul",
    )

    # Event Data & Context
    event_data: dict[str, str] = Field(
        default_factory=dict,
        description="Event-specific data payload",
    )
    event_context: dict[str, str] = Field(
        default_factory=dict,
        description="Event execution context",
    )
    event_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event creation timestamp",
    )

    # Hub Integration
    hub_domain: str | None = Field(
        default=None, description="Hub domain for integration"
    )
    hub_registration_required: bool = Field(
        default=True,
        description="Whether hub should register in Consul",
    )

    # Networking & Coordination
    service_endpoints: dict[str, str] = Field(
        default_factory=dict,
        description="Service endpoint mappings",
    )
    mesh_coordination_data: dict[str, str] = Field(
        default_factory=dict,
        description="Full mesh coordination data",
    )
    auto_provisioning_config: dict[str, str] | None = Field(
        default=None,
        description="Auto-provisioning configuration",
    )

    # Quality & Validation
    trust_level: str = Field(
        default="medium",
        description="Trust level for service (high/medium/low)",
    )
    validation_required: bool = Field(
        default=True,
        description="Whether event requires validation",
    )
    event_schema_version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="EventDescriptor schema version",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
