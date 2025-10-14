from enum import Enum


class EnumEventTypeDiscovery(str, Enum):
    """Event types supported by the Event Registry.

    These event types define the different kinds of operations that can be performed
    through the Container Adapter pattern for ONEX Discovery & Integration.

    Examples:
        >>> event_type = EnumEventTypeDiscovery.SERVICE_DISCOVERY
        >>> print(event_type.value)
        'service_discovery'

        >>> # Used in event descriptors
        >>> event = ModelEventDescriptor(
        ...     event_type=EnumEventTypeDiscovery.SERVICE_REGISTRATION,
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
