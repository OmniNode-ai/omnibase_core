"""Core event types for the ONEX system.

This module defines the core event types used throughout the ONEX ecosystem
for inter-service communication, discovery, and introspection.

All constants follow ONEX naming convention: module-level UPPER_SNAKE_CASE.
"""

# env-var-ok: constant definitions for event types, not environment variables

from omnibase_core.types.typed_dict_event_type import TypedDictEventType

# Tool-related events
TOOL_INVOCATION = "tool_invocation"
TOOL_RESPONSE = "tool_response"
TOOL_DISCOVERY_REQUEST = "tool_discovery_request"
TOOL_DISCOVERY_RESPONSE = "tool_discovery_response"

# Introspection and discovery events
NODE_INTROSPECTION_EVENT = "node_introspection_event"
REQUEST_REAL_TIME_INTROSPECTION = "request_real_time_introspection"
REAL_TIME_INTROSPECTION_RESPONSE = "real_time_introspection_response"

# Additional core events (can be extended as needed)
NODE_HEALTH_CHECK = "node_health_check"
NODE_HEALTH_EVENT = "node_health_event"
NODE_SHUTDOWN_EVENT = "node_shutdown_event"
SERVICE_DISCOVERY = "service_discovery"


# Node lifecycle events
NODE_START = "node_start"
NODE_SUCCESS = "node_success"
NODE_FAILURE = "node_failure"

# Logging and audit events
LOGGING_APPLICATION_EVENT = "omninode.logging.application.v1"
LOGGING_AUDIT_EVENT = "omninode.logging.audit.v1"
LOGGING_SECURITY_EVENT = "omninode.logging.security.v1"

# Contract registration events (OMN-1652)
# NOTE: These are SHORT event type identifiers used for event classification and routing.
# The full topic names (e.g., "onex.evt.contract-registered.v1") are defined alongside
# the event models in omnibase_core.models.events.contract_registration.
EVENT_TYPE_CONTRACT_REGISTERED = "contract-registered"
EVENT_TYPE_CONTRACT_DEREGISTERED = "contract-deregistered"
EVENT_TYPE_NODE_HEARTBEAT = "node-heartbeat"


def normalize_legacy_event_type(event_type: str | TypedDictEventType | object) -> str:
    """Normalize legacy event types to consistent string format.

    This function handles compatibility by converting various
    event type formats (strings, ModelEventType objects, etc.) to
    standardized string values.

    Args:
        event_type: Event type in various formats (str, ModelEventType, TypedDictEventType)

    Returns:
        Normalized event type as string

    Examples:
        >>> normalize_legacy_event_type("tool_invocation")
        'tool_invocation'

        >>> # For ModelEventType objects
        >>> event_obj = ModelEventType(value="tool_response")
        >>> normalize_legacy_event_type(event_obj)
        'tool_response'
    """
    if isinstance(event_type, str):
        return event_type

    # Handle ModelEventType objects
    if hasattr(event_type, "value"):
        return str(event_type.value)

    # Handle TypedDictEventType-like objects
    if isinstance(event_type, dict):
        if "value" in event_type:
            return str(event_type["value"])
        if "event_type" in event_type:
            return str(event_type["event_type"])

    # Fallback to string conversion
    return str(event_type)
