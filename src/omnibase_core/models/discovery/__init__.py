# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Discovery Event Models for ONEX Event-Driven Service Discovery

Pydantic models for the event-driven discovery lifecycle:
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

from __future__ import annotations

# Event Registry models for Container Adapter pattern
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_discovery_phase import EnumDiscoveryPhase
    from omnibase_core.enums.enum_event_type import EnumEventType
    from omnibase_core.enums.enum_node_current_status import EnumNodeCurrentStatus
    from omnibase_core.enums.enum_service_status import EnumServiceStatus

    # Container Adapter I/O models
    from .model_container_adapter_io import (
        ModelContainerAdapterInput,
        ModelContainerAdapterOutput,
        ModelEventRegistryCoordinatorInput,
        ModelEventRegistryCoordinatorOutput,
    )
    from .model_current_tool_availability import ModelCurrentToolAvailability

    # New discovery models for Workflow orchestration
    from .model_discovery_config import ModelDiscoveryConfig
    from .model_discovery_performance_metrics import ModelPerformanceMetrics
    from .model_event_descriptor import ModelEventDescriptor
    from .model_event_discovery_request import ModelEventDiscoveryRequest
    from .model_event_discovery_response import ModelEventDiscoveryResponse
    from .model_hub_registration_event import ModelHubRegistrationEvent
    from .model_introspection_filters import ModelIntrospectionFilters
    from .model_introspection_response_event import ModelIntrospectionResponseEvent
    from .model_mixin_info import ModelMixinInfo
    from .model_node_health_event import ModelNodeHealthEvent
    from .model_node_introspection_event import (
        ModelNodeCapabilities,
        ModelNodeIntrospectionEvent,
    )
    from .model_node_shutdown_event import ModelNodeShutdownEvent
    from .model_request_introspection_event import ModelRequestIntrospectionEvent
    from .model_resource_usage import ModelResourceUsage
    from .model_tool_discovery_error import ModelToolDiscoveryError
    from .model_tool_discovery_result import ModelToolDiscoveryResult
    from .model_tooldiscoveryrequest import ModelToolDiscoveryRequest
    from .model_tooldiscoveryresponse import ModelToolDiscoveryResponse

__all__ = [
    "EnumDiscoveryPhase",
    "EnumEventType",
    "EnumServiceStatus",
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
    "ModelHubRegistrationEvent",
    "ModelIntrospectionFilters",
    "ModelIntrospectionResponseEvent",
    "ModelMixinInfo",
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
    "EnumNodeCurrentStatus",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumDiscoveryPhase": (
        "omnibase_core.enums.enum_discovery_phase",
        "EnumDiscoveryPhase",
    ),
    "EnumEventType": ("omnibase_core.enums.enum_event_type", "EnumEventType"),
    "EnumNodeCurrentStatus": (
        "omnibase_core.enums.enum_node_current_status",
        "EnumNodeCurrentStatus",
    ),
    "EnumServiceStatus": (
        "omnibase_core.enums.enum_service_status",
        "EnumServiceStatus",
    ),
    "ModelContainerAdapterInput": (
        "omnibase_core.models.discovery.model_container_adapter_io",
        "ModelContainerAdapterInput",
    ),
    "ModelContainerAdapterOutput": (
        "omnibase_core.models.discovery.model_container_adapter_io",
        "ModelContainerAdapterOutput",
    ),
    "ModelEventRegistryCoordinatorInput": (
        "omnibase_core.models.discovery.model_container_adapter_io",
        "ModelEventRegistryCoordinatorInput",
    ),
    "ModelEventRegistryCoordinatorOutput": (
        "omnibase_core.models.discovery.model_container_adapter_io",
        "ModelEventRegistryCoordinatorOutput",
    ),
    "ModelCurrentToolAvailability": (
        "omnibase_core.models.discovery.model_current_tool_availability",
        "ModelCurrentToolAvailability",
    ),
    "ModelDiscoveryConfig": (
        "omnibase_core.models.discovery.model_discovery_config",
        "ModelDiscoveryConfig",
    ),
    "ModelPerformanceMetrics": (
        "omnibase_core.models.discovery.model_discovery_performance_metrics",
        "ModelPerformanceMetrics",
    ),
    "ModelEventDescriptor": (
        "omnibase_core.models.discovery.model_event_descriptor",
        "ModelEventDescriptor",
    ),
    "ModelEventDiscoveryRequest": (
        "omnibase_core.models.discovery.model_event_discovery_request",
        "ModelEventDiscoveryRequest",
    ),
    "ModelEventDiscoveryResponse": (
        "omnibase_core.models.discovery.model_event_discovery_response",
        "ModelEventDiscoveryResponse",
    ),
    "ModelHubRegistrationEvent": (
        "omnibase_core.models.discovery.model_hub_registration_event",
        "ModelHubRegistrationEvent",
    ),
    "ModelIntrospectionFilters": (
        "omnibase_core.models.discovery.model_introspection_filters",
        "ModelIntrospectionFilters",
    ),
    "ModelIntrospectionResponseEvent": (
        "omnibase_core.models.discovery.model_introspection_response_event",
        "ModelIntrospectionResponseEvent",
    ),
    "ModelMixinInfo": (
        "omnibase_core.models.discovery.model_mixin_info",
        "ModelMixinInfo",
    ),
    "ModelNodeHealthEvent": (
        "omnibase_core.models.discovery.model_node_health_event",
        "ModelNodeHealthEvent",
    ),
    "ModelNodeCapabilities": (
        "omnibase_core.models.discovery.model_node_introspection_event",
        "ModelNodeCapabilities",
    ),
    "ModelNodeIntrospectionEvent": (
        "omnibase_core.models.discovery.model_node_introspection_event",
        "ModelNodeIntrospectionEvent",
    ),
    "ModelNodeShutdownEvent": (
        "omnibase_core.models.discovery.model_node_shutdown_event",
        "ModelNodeShutdownEvent",
    ),
    "ModelRequestIntrospectionEvent": (
        "omnibase_core.models.discovery.model_request_introspection_event",
        "ModelRequestIntrospectionEvent",
    ),
    "ModelResourceUsage": (
        "omnibase_core.models.discovery.model_resource_usage",
        "ModelResourceUsage",
    ),
    "ModelToolDiscoveryError": (
        "omnibase_core.models.discovery.model_tool_discovery_error",
        "ModelToolDiscoveryError",
    ),
    "ModelToolDiscoveryResult": (
        "omnibase_core.models.discovery.model_tool_discovery_result",
        "ModelToolDiscoveryResult",
    ),
    "ModelToolDiscoveryRequest": (
        "omnibase_core.models.discovery.model_tooldiscoveryrequest",
        "ModelToolDiscoveryRequest",
    ),
    "ModelToolDiscoveryResponse": (
        "omnibase_core.models.discovery.model_tooldiscoveryresponse",
        "ModelToolDiscoveryResponse",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
