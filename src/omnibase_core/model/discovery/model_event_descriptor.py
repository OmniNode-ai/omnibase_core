"""Event Descriptor model for ONEX Discovery & Integration Event Registry.

This module defines the core EventDescriptor structure used for event-driven service
discovery and Container Adapter coordination throughout the ONEX ecosystem.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EventTypeEnum(str, Enum):
    """Event types supported by the Event Registry.

    These event types define the different kinds of operations that can be performed
    through the Container Adapter pattern for ONEX Discovery & Integration.

    Examples:
        >>> event_type = EventTypeEnum.SERVICE_DISCOVERY
        >>> print(event_type.value)
        'service_discovery'

        >>> # Used in event descriptors
        >>> event = ModelEventDescriptor(
        ...     event_type=EventTypeEnum.SERVICE_REGISTRATION,
        ...     # ... other fields
        ... )
    """

    SERVICE_DISCOVERY = "service_discovery"
    SERVICE_REGISTRATION = "service_registration"
    SERVICE_DEREGISTRATION = "service_deregistration"
    CONTAINER_PROVISIONING = "container_provisioning"
    CONTAINER_HEALTH_CHECK = "container_health_check"
    MESH_COORDINATION = "mesh_coordination"
    HUB_STATUS_UPDATE = "hub_status_update"


class ServiceStatusEnum(str, Enum):
    """Service status values for Container Adapter coordination."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    PROVISIONING = "provisioning"
    DECOMMISSIONING = "decommissioning"
    HEALTH_CHECK_FAILING = "health_check_failing"


class DiscoveryPhaseEnum(str, Enum):
    """Discovery implementation phases."""

    PHASE_1_SIMPLE = "phase_1_simple_discovery"
    PHASE_2_AUTO_PROVISION = "phase_2_auto_provisioning"
    PHASE_3_FULL_MESH = "phase_3_full_mesh"


class ModelEventDescriptor(BaseModel):
    """Core EventDescriptor structure for ONEX Discovery & Integration.

    This model defines the complete event structure used for Container Adapter
    pattern coordination and service discovery via Consul service registry.

    The EventDescriptor serves as the primary data structure for all event-driven
    operations in the ONEX ecosystem, including service discovery, registration,
    and mesh coordination.

    Examples:
        >>> from datetime import datetime
        >>>
        >>> # Create a basic service registration event
        >>> event = ModelEventDescriptor(
        ...     event_id="evt_reg_001",
        ...     event_type=EventTypeEnum.SERVICE_REGISTRATION,
        ...     event_name="Register User Service",
        ...     service_id="user_service_001",
        ...     service_name="user-service",
        ...     service_version="1.0.0",
        ...     discovery_phase=DiscoveryPhaseEnum.PHASE_1_SIMPLE,
        ...     consul_service_name="onex-user-service",
        ...     container_status=ServiceStatusEnum.ACTIVE
        ... )
        >>>
        >>> # Event with Consul metadata
        >>> event_with_meta = ModelEventDescriptor(
        ...     event_id="evt_disc_002",
        ...     event_type=EventTypeEnum.SERVICE_DISCOVERY,
        ...     event_name="Discover Auth Services",
        ...     service_id="auth_discovery",
        ...     service_name="auth-discovery",
        ...     service_version="2.1.0",
        ...     discovery_phase=DiscoveryPhaseEnum.PHASE_2_AUTO_PROVISION,
        ...     consul_service_name="onex-auth-discovery",
        ...     consul_tags=["auth", "security", "oauth"],
        ...     consul_meta={"environment": "production", "region": "us-west-2"},
        ...     container_status=ServiceStatusEnum.PROVISIONING,
        ...     health_check_endpoint="/health",
        ...     service_endpoints={"api": "https://api.auth.example.com", "admin": "https://admin.auth.example.com"}
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
        consul_tags: List of Consul service tags (default: empty list)
        consul_meta: Dict of Consul service metadata (default: empty dict)
        container_adapter_enabled: Whether Container Adapter pattern is active (default: True)
        health_check_endpoint: Optional health check endpoint for Consul
        event_data: Event-specific data payload (default: empty dict)
        event_context: Event execution context (default: empty dict)
        event_timestamp: Event creation timestamp (default: current UTC time)
        hub_domain: Optional hub domain for integration
        hub_registration_required: Whether hub should register in Consul (default: True)
        service_endpoints: Service endpoint mappings (default: empty dict)
        mesh_coordination_data: Full mesh coordination data (default: empty dict)
        auto_provisioning_config: Optional auto-provisioning configuration
        trust_level: Trust level for service (default: "medium")
        validation_required: Whether event requires validation (default: True)
        event_schema_version: EventDescriptor schema version (default: "1.0.0")
    """

    # Core Event Identity
    event_id: str = Field(..., description="Unique identifier for this event")
    event_type: EventTypeEnum = Field(..., description="Type of event being described")
    event_name: str = Field(..., description="Human-readable event name")
    correlation_id: str | None = Field(
        None,
        description="Correlation ID for request/response matching",
    )

    # Service Identity
    service_id: str = Field(..., description="Unique service identifier")
    service_name: str = Field(..., description="Service name for Consul registration")
    service_version: str = Field(..., description="Service version")
    node_id: str | None = Field(None, description="Node ID hosting the service")

    # Discovery & Registry Information
    discovery_phase: DiscoveryPhaseEnum = Field(
        ...,
        description="Current discovery implementation phase",
    )
    consul_service_name: str = Field(..., description="Consul service registry name")
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
        True,
        description="Whether Container Adapter pattern is active",
    )
    container_status: ServiceStatusEnum = Field(
        ...,
        description="Current container/service status",
    )
    health_check_endpoint: str | None = Field(
        None,
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
        default_factory=datetime.utcnow,
        description="Event creation timestamp",
    )

    # Hub Integration
    hub_domain: str | None = Field(None, description="Hub domain for integration")
    hub_registration_required: bool = Field(
        True,
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
        None,
        description="Auto-provisioning configuration",
    )

    # Quality & Validation
    trust_level: str = Field(
        "medium",
        description="Trust level for service (high/medium/low)",
    )
    validation_required: bool = Field(
        True,
        description="Whether event requires validation",
    )
    event_schema_version: str = Field(
        "1.0.0",
        description="EventDescriptor schema version",
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
    )
