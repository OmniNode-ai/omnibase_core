"""
Discovery Event Models for ONEX Event-Driven Service Discovery

This module contains Pydantic models for the event-driven discovery lifecycle:
- NODE_INTROSPECTION_EVENT: Node capability publishing
- TOOL_DISCOVERY_REQUEST: Request for available tools
- TOOL_DISCOVERY_RESPONSE: Response with tool listings
- NODE_HEALTH_EVENT: Health metric updates
- NODE_SHUTDOWN_EVENT: Node deregistration
- REQUEST_REAL_TIME_INTROSPECTION: Request real-time introspection
- REAL_TIME_INTROSPECTION_RESPONSE: Response to introspection request

Enhanced with new discovery configuration and tool discovery models:
- ModelDiscoveryConfig: Advanced tool discovery configuration
- ModelToolDiscoveryError: Tool discovery error tracking
- ModelToolDiscoveryResult: Tool discovery results
"""

from .enum_node_current_status import NodeCurrentStatusEnum

# Container Adapter I/O models
from .model_container_adapter_io import (
    ModelConsulEventBridgeInput,
    ModelConsulEventBridgeOutput,
    ModelContainerAdapterInput,
    ModelContainerAdapterOutput,
    ModelEventRegistryCoordinatorInput,
    ModelEventRegistryCoordinatorOutput,
)
from .model_current_tool_availability import ModelCurrentToolAvailability

# New discovery models for Workflow orchestration
from .model_discovery_config import *

# Event Registry models for Container Adapter pattern
from .model_event_descriptor import (
    DiscoveryPhaseEnum,
    EventTypeEnum,
    ModelEventDescriptor,
    ServiceStatusEnum,
)
from .model_event_discovery_request import ModelEventDiscoveryRequest
from .model_event_discovery_response import ModelEventDiscoveryResponse

# Hub Consul Registration I/O models
from .model_hub_consul_registration_io import (
    ModelHubConsulRegistrationInput,
    ModelHubConsulRegistrationOutput,
)
from .model_hub_registration_event import ModelHubRegistrationEvent
from .model_introspection_filters import ModelIntrospectionFilters
from .model_introspection_response_event import ModelIntrospectionResponseEvent
from .model_node_health_event import ModelNodeHealthEvent
from .model_node_introspection_event import (
    ModelNodeCapabilities,
    ModelNodeIntrospectionEvent,
)
from .model_node_shutdown_event import ModelNodeShutdownEvent
from .model_performance_metrics import ModelPerformanceMetrics
from .model_request_introspection_event import ModelRequestIntrospectionEvent
from .model_resource_usage import ModelResourceUsage
from .model_tool_discovery_error import *
from .model_tool_discovery_request import ModelToolDiscoveryRequest
from .model_tool_discovery_response import ModelToolDiscoveryResponse
from .model_tool_discovery_result import *

__all__ = [
    "DiscoveryPhaseEnum",
    "EventTypeEnum",
    "ModelConsulEventBridgeInput",
    "ModelConsulEventBridgeOutput",
    # Container Adapter I/O models
    "ModelContainerAdapterInput",
    "ModelContainerAdapterOutput",
    "ModelCurrentToolAvailability",
    # New discovery models
    "ModelDiscoveryConfig",
    # Event Registry models
    "ModelEventDescriptor",
    "ModelEventDiscoveryRequest",
    "ModelEventDiscoveryResponse",
    "ModelEventRegistryCoordinatorInput",
    "ModelEventRegistryCoordinatorOutput",
    # Hub Consul Registration I/O models
    "ModelHubConsulRegistrationInput",
    "ModelHubConsulRegistrationOutput",
    "ModelHubRegistrationEvent",
    "ModelIntrospectionFilters",
    "ModelIntrospectionResponseEvent",
    "ModelNodeCapabilities",
    "ModelNodeHealthEvent",
    "ModelNodeIntrospectionEvent",
    "ModelNodeShutdownEvent",
    "ModelPerformanceMetrics",
    "ModelRequestIntrospectionEvent",
    "ModelResourceUsage",
    "ModelToolDiscoveryError",
    "ModelToolDiscoveryRequest",
    "ModelToolDiscoveryResponse",
    "ModelToolDiscoveryResult",
    "NodeCurrentStatusEnum",
    "ServiceStatusEnum",
]
