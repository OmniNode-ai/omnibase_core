from omnibase_core.constants.constants_contract_fields import (
    NODE_INTROSPECTION_EVENT,
    TOOL_DISCOVERY_REQUEST,
)

"""Core event types for the ONEX system.

This module defines the core event types used throughout the ONEX ecosystem
for inter-service communication, discovery, and introspection.

All constants follow ONEX naming convention: module-level UPPER_SNAKE_CASE.
"""

from typing import Any

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


def normalize_legacy_event_type(event_type: str | dict[str, Any] | object) -> str:
    """Normalize legacy event types to consistent string format.

    This function handles compatibility by converting various
    event type formats (strings, ModelEventType objects, etc.) to
    standardized string values.

    Args:
        event_type: Event type in various formats (str, ModelEventType, etc.)

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

    # Handle dict[str, Any]-like objects
    if isinstance(event_type, dict):
        if "value" in event_type:
            return str(event_type["value"])
        if "event_type" in event_type:
            return str(event_type["event_type"])

    # Fallback to string conversion
    return str(event_type)
