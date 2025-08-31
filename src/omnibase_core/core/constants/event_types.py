# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-07-05T12:00:00.000000'
# description: Event type constants for backwards compatibility and namespacing
# entrypoint: python://event_types
# hash: auto-generated
# last_modified_at: '2025-07-05T12:00:00.000000'
# lifecycle: active
# meta_type: constants
# metadata_version: 0.1.0
# name: event_types.py
# namespace: python://omnibase.constants.event_types
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: null
# uuid: auto-generated
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
ONEX Event Type Constants and Validation

This module provides:
1. Backwards compatibility constants for existing OnexEventTypeEnum values
2. Namespaced event type patterns for extensibility
3. Validation patterns and helper functions
4. Factory methods for creating event types

Event Type Naming Convention:
- Core ONEX events: "core.category.action" (e.g., "core.node.start")
- User events: "user.namespace.action" (e.g., "user.mycompany.custom_action")
- Plugin events: "plugin.name.action" (e.g., "plugin.ai_assistant.completion")

Addressing Pattern (for future envelope routing):
- Broadcast: No address prefix (default)
- Node-specific: "node://uuid"
- Service: "service://name"
- Group: "group://name"
"""

import re

# Event type validation pattern - namespace.category.action or namespace.action
# Allow underscores in all parts (first part was incorrectly restrictive)
EVENT_TYPE_PATTERN = re.compile(r"^[a-z_]+(\.[a-z_]+)*$")


class CoreEventTypes:
    """Core ONEX event type constants - use these for backwards compatibility"""

    # Node lifecycle events
    NODE_START = "core.node.start"
    NODE_SUCCESS = "core.node.success"
    NODE_FAILURE = "core.node.failure"
    NODE_REGISTER = "core.node.register"

    # Telemetry and monitoring
    TELEMETRY_OPERATION_START = "core.telemetry.operation_start"
    TELEMETRY_OPERATION_SUCCESS = "core.telemetry.operation_success"
    TELEMETRY_OPERATION_ERROR = "core.telemetry.operation_error"
    STRUCTURED_LOG = "core.telemetry.structured_log"

    # Discovery and introspection
    INTROSPECTION_REQUEST = "core.discovery.introspection_request"
    INTROSPECTION_RESPONSE = "core.discovery.introspection_response"
    NODE_DISCOVERY_REQUEST = "core.discovery.node_request"
    NODE_DISCOVERY_RESPONSE = "core.discovery.node_response"
    NODE_ANNOUNCE = "core.discovery.node_announce"
    NODE_ANNOUNCE_ACCEPTED = "core.discovery.node_announce_accepted"
    NODE_ANNOUNCE_REJECTED = "core.discovery.node_announce_rejected"

    # Tool discovery
    TOOL_DISCOVERY_REQUEST = "core.discovery.tool_request"
    TOOL_DISCOVERY_RESPONSE = "core.discovery.tool_response"

    # Tool invocation (new)
    TOOL_INVOCATION = "core.tool.invocation"
    TOOL_RESPONSE = "core.tool.response"

    # Proxy invocation events
    TOOL_PROXY_INVOKE = "core.proxy.tool_invoke"
    TOOL_PROXY_ACCEPTED = "core.proxy.tool_accepted"
    TOOL_PROXY_REJECTED = "core.proxy.tool_rejected"
    TOOL_PROXY_RESULT = "core.proxy.tool_result"
    TOOL_PROXY_ERROR = "core.proxy.tool_error"
    TOOL_PROXY_TIMEOUT = "core.proxy.tool_timeout"

    # Scenario testing events
    SCENARIO_STARTED = "core.scenario.started"
    SCENARIO_PASSED = "core.scenario.passed"
    SCENARIO_FAILED = "core.scenario.failed"
    SCENARIO_SUMMARY = "core.scenario.summary"

    # Discovery broadcast events
    DISCOVERY_REQUEST = "core.broadcast.discovery_request"
    DISCOVERY_RESPONSE = "core.broadcast.discovery_response"
    DISCOVERY_BROADCAST = "core.broadcast.discovery_broadcast"
    DISCOVERY_ACKNOWLEDGMENT = "core.broadcast.discovery_acknowledgment"
    NODE_ANNOUNCEMENT = "core.broadcast.node_announcement"
    NODE_DISCONNECT = "core.broadcast.node_disconnect"

    # Event-driven discovery events
    NODE_INTROSPECTION_EVENT = "core.discovery.node_introspection"
    NODE_HEALTH_EVENT = "core.health.report"
    NODE_SHUTDOWN_EVENT = "core.lifecycle.shutdown"

    # Request-response introspection events
    REQUEST_REAL_TIME_INTROSPECTION = "core.discovery.realtime_request"
    REAL_TIME_INTROSPECTION_RESPONSE = "core.discovery.realtime_response"
    REAL_TIME_INTROSPECTION_COMPLETE = "core.discovery.realtime_complete"


class EventTypeNamespaces:
    """Reserved namespaces for event types"""

    CORE = "core"  # Core ONEX platform events
    USER = "user"  # User-defined events
    PLUGIN = "plugin"  # Plugin/extension events
    SYSTEM = "system"  # System-level events
    DEBUG = "debug"  # Debug and tracing events


# Legacy enum mapping for backwards compatibility
LEGACY_ENUM_MAPPING = {
    # Map old enum values to new namespaced strings
    "NODE_START": CoreEventTypes.NODE_START,
    "NODE_SUCCESS": CoreEventTypes.NODE_SUCCESS,
    "NODE_FAILURE": CoreEventTypes.NODE_FAILURE,
    "NODE_REGISTER": CoreEventTypes.NODE_REGISTER,
    "TELEMETRY_OPERATION_START": CoreEventTypes.TELEMETRY_OPERATION_START,
    "TELEMETRY_OPERATION_SUCCESS": CoreEventTypes.TELEMETRY_OPERATION_SUCCESS,
    "TELEMETRY_OPERATION_ERROR": CoreEventTypes.TELEMETRY_OPERATION_ERROR,
    "STRUCTURED_LOG": CoreEventTypes.STRUCTURED_LOG,
    "INTROSPECTION_REQUEST": CoreEventTypes.INTROSPECTION_REQUEST,
    "INTROSPECTION_RESPONSE": CoreEventTypes.INTROSPECTION_RESPONSE,
    "NODE_DISCOVERY_REQUEST": CoreEventTypes.NODE_DISCOVERY_REQUEST,
    "NODE_DISCOVERY_RESPONSE": CoreEventTypes.NODE_DISCOVERY_RESPONSE,
    "NODE_ANNOUNCE": CoreEventTypes.NODE_ANNOUNCE,
    "NODE_ANNOUNCE_ACCEPTED": CoreEventTypes.NODE_ANNOUNCE_ACCEPTED,
    "NODE_ANNOUNCE_REJECTED": CoreEventTypes.NODE_ANNOUNCE_REJECTED,
    "TOOL_DISCOVERY_REQUEST": CoreEventTypes.TOOL_DISCOVERY_REQUEST,
    "TOOL_DISCOVERY_RESPONSE": CoreEventTypes.TOOL_DISCOVERY_RESPONSE,
    "TOOL_PROXY_INVOKE": CoreEventTypes.TOOL_PROXY_INVOKE,
    "TOOL_PROXY_ACCEPTED": CoreEventTypes.TOOL_PROXY_ACCEPTED,
    "TOOL_PROXY_REJECTED": CoreEventTypes.TOOL_PROXY_REJECTED,
    "TOOL_PROXY_RESULT": CoreEventTypes.TOOL_PROXY_RESULT,
    "TOOL_PROXY_ERROR": CoreEventTypes.TOOL_PROXY_ERROR,
    "TOOL_PROXY_TIMEOUT": CoreEventTypes.TOOL_PROXY_TIMEOUT,
    "SCENARIO_STARTED": CoreEventTypes.SCENARIO_STARTED,
    "SCENARIO_PASSED": CoreEventTypes.SCENARIO_PASSED,
    "SCENARIO_FAILED": CoreEventTypes.SCENARIO_FAILED,
    "SCENARIO_SUMMARY": CoreEventTypes.SCENARIO_SUMMARY,
    "DISCOVERY_REQUEST": CoreEventTypes.DISCOVERY_REQUEST,
    "DISCOVERY_RESPONSE": CoreEventTypes.DISCOVERY_RESPONSE,
    "DISCOVERY_BROADCAST": CoreEventTypes.DISCOVERY_BROADCAST,
    "DISCOVERY_ACKNOWLEDGMENT": CoreEventTypes.DISCOVERY_ACKNOWLEDGMENT,
    "NODE_ANNOUNCEMENT": CoreEventTypes.NODE_ANNOUNCEMENT,
    "NODE_DISCONNECT": CoreEventTypes.NODE_DISCONNECT,
    "NODE_INTROSPECTION_EVENT": CoreEventTypes.NODE_INTROSPECTION_EVENT,
    "NODE_HEALTH_EVENT": CoreEventTypes.NODE_HEALTH_EVENT,
    "NODE_SHUTDOWN_EVENT": CoreEventTypes.NODE_SHUTDOWN_EVENT,
    "REQUEST_REAL_TIME_INTROSPECTION": CoreEventTypes.REQUEST_REAL_TIME_INTROSPECTION,
    "REAL_TIME_INTROSPECTION_RESPONSE": CoreEventTypes.REAL_TIME_INTROSPECTION_RESPONSE,
}


def is_valid_event_type(event_type: str) -> bool:
    """
    Validate an event type string against the naming convention.

    Args:
        event_type: Event type string to validate

    Returns:
        True if valid, False otherwise

    Examples:
        >>> is_valid_event_type("core.node.start")
        True
        >>> is_valid_event_type("user.mycompany.custom_action")
        True
        >>> is_valid_event_type("Invalid.CamelCase")
        False
    """
    if not isinstance(event_type, str):
        return False

    return bool(EVENT_TYPE_PATTERN.match(event_type))


def validate_event_type(event_type: str) -> str:
    """
    Validate and return an event type, raising ValueError if invalid.

    Args:
        event_type: Event type string to validate

    Returns:
        The validated event type string

    Raises:
        ValueError: If event type is invalid
    """
    if not is_valid_event_type(event_type):
        msg = f"Invalid event type '{event_type}'. Must match pattern: {EVENT_TYPE_PATTERN.pattern}"
        raise ValueError(
            msg,
        )

    return event_type


def normalize_legacy_event_type(event_type: str | object) -> str:
    """
    Normalize legacy enum values to new string format.

    Args:
        event_type: Either a string or legacy enum value

    Returns:
        Normalized event type string

    Raises:
        ValueError: If event type cannot be normalized
    """
    # If it's already a string, validate it
    if isinstance(event_type, str):
        return validate_event_type(event_type)

    # Handle enum objects with .value or .name attributes
    if hasattr(event_type, "value"):
        legacy_value = event_type.value
    elif hasattr(event_type, "name"):
        legacy_value = event_type.name
    else:
        legacy_value = str(event_type)

    # Try to map from legacy enum
    if legacy_value in LEGACY_ENUM_MAPPING:
        return LEGACY_ENUM_MAPPING[legacy_value]

    # If it's already a valid new format, return it
    if is_valid_event_type(legacy_value):
        return legacy_value

    msg = f"Cannot normalize event type: {event_type}"
    raise ValueError(msg)


def create_user_event_type(namespace: str, action: str) -> str:
    """
    Create a user event type with proper validation.

    Args:
        namespace: User namespace (e.g., "mycompany")
        action: Event action (e.g., "custom_action")

    Returns:
        Formatted event type string

    Examples:
        >>> create_user_event_type("mycompany", "workflow_complete")
        "user.mycompany.workflow_complete"
    """
    event_type = f"user.{namespace}.{action}"
    return validate_event_type(event_type)


def create_plugin_event_type(plugin_name: str, action: str) -> str:
    """
    Create a plugin event type with proper validation.

    Args:
        plugin_name: Plugin name (e.g., "ai_assistant")
        action: Event action (e.g., "completion")

    Returns:
        Formatted event type string

    Examples:
        >>> create_plugin_event_type("ai_assistant", "completion_request")
        "plugin.ai_assistant.completion_request"
    """
    event_type = f"plugin.{plugin_name}.{action}"
    return validate_event_type(event_type)


def get_event_namespace(event_type: str) -> str | None:
    """
    Extract the namespace from an event type.

    Args:
        event_type: Event type string

    Returns:
        The namespace portion or None if invalid

    Examples:
        >>> get_event_namespace("core.node.start")
        "core"
        >>> get_event_namespace("user.mycompany.action")
        "user"
    """
    if not is_valid_event_type(event_type):
        return None

    parts = event_type.split(".")
    return parts[0] if parts else None


def is_core_event(event_type: str) -> bool:
    """Check if an event type is a core ONEX event."""
    return get_event_namespace(event_type) == EventTypeNamespaces.CORE


def is_user_event(event_type: str) -> bool:
    """Check if an event type is a user-defined event."""
    return get_event_namespace(event_type) == EventTypeNamespaces.USER


def is_plugin_event(event_type: str) -> bool:
    """Check if an event type is a plugin event."""
    return get_event_namespace(event_type) == EventTypeNamespaces.PLUGIN
