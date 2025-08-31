# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-07-05T12:00:00.000000'
# description: DEPRECATED - OnexEventTypeEnum moved for backwards compatibility only
# entrypoint: python://enum_event_type
# hash: auto-generated
# last_modified_at: '2025-07-05T12:00:00.000000'
# lifecycle: deprecated
# meta_type: enum
# metadata_version: 0.1.0
# name: enum_event_type.py
# namespace: python://omnibase.enums.enum_event_type
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
DEPRECATED: OnexEventTypeEnum

This enum is deprecated in favor of extensible string event types.
Use omnibase.constants.event_types.CoreEventTypes instead.

This module is maintained for backwards compatibility only.
"""

import warnings
from enum import Enum

# Deprecation warning
warnings.warn(
    "OnexEventTypeEnum is deprecated. Use omnibase.constants.event_types.CoreEventTypes instead.",
    DeprecationWarning,
    stacklevel=2,
)


class OnexEventTypeEnum(str, Enum):
    """
    DEPRECATED: Use omnibase.constants.event_types.CoreEventTypes instead.

    This enum is maintained for backwards compatibility only.
    New code should use the extensible string event types.
    """

    NODE_START = "NODE_START"
    NODE_SUCCESS = "NODE_SUCCESS"
    NODE_FAILURE = "NODE_FAILURE"
    NODE_REGISTER = "NODE_REGISTER"
    TELEMETRY_OPERATION_START = "TELEMETRY_OPERATION_START"
    TELEMETRY_OPERATION_SUCCESS = "TELEMETRY_OPERATION_SUCCESS"
    TELEMETRY_OPERATION_ERROR = "TELEMETRY_OPERATION_ERROR"
    STRUCTURED_LOG = "STRUCTURED_LOG"
    INTROSPECTION_REQUEST = "INTROSPECTION_REQUEST"
    INTROSPECTION_RESPONSE = "INTROSPECTION_RESPONSE"
    NODE_DISCOVERY_REQUEST = "NODE_DISCOVERY_REQUEST"
    NODE_DISCOVERY_RESPONSE = "NODE_DISCOVERY_RESPONSE"
    NODE_ANNOUNCE = "NODE_ANNOUNCE"  # Emitted by nodes on startup or registration
    NODE_ANNOUNCE_ACCEPTED = (
        "NODE_ANNOUNCE_ACCEPTED"  # Emitted by registry node on successful registration
    )
    NODE_ANNOUNCE_REJECTED = (
        "NODE_ANNOUNCE_REJECTED"  # Emitted by registry node if registration fails
    )
    TOOL_DISCOVERY_REQUEST = (
        "TOOL_DISCOVERY_REQUEST"  # Protocol-pure tool discovery request
    )
    TOOL_DISCOVERY_RESPONSE = (
        "TOOL_DISCOVERY_RESPONSE"  # Protocol-pure tool discovery response
    )
    # --- Proxy invocation event types ---
    TOOL_PROXY_INVOKE = "TOOL_PROXY_INVOKE"  # Request to invoke a tool via proxy
    TOOL_PROXY_ACCEPTED = "TOOL_PROXY_ACCEPTED"  # Proxy invocation accepted and routed
    TOOL_PROXY_REJECTED = (
        "TOOL_PROXY_REJECTED"  # Proxy invocation rejected (invalid or unroutable)
    )
    TOOL_PROXY_RESULT = "TOOL_PROXY_RESULT"  # Result of proxy tool invocation
    TOOL_PROXY_ERROR = "TOOL_PROXY_ERROR"  # Error during proxy tool invocation
    TOOL_PROXY_TIMEOUT = "TOOL_PROXY_TIMEOUT"  # Proxy invocation timed out
    # --- Scenario event types ---
    SCENARIO_STARTED = "SCENARIO_STARTED"
    SCENARIO_PASSED = "SCENARIO_PASSED"
    SCENARIO_FAILED = "SCENARIO_FAILED"
    SCENARIO_SUMMARY = "SCENARIO_SUMMARY"
    # --- Discovery broadcast event types ---
    DISCOVERY_REQUEST = (
        "DISCOVERY_REQUEST"  # CLI/client requests discovery of available nodes
    )
    DISCOVERY_RESPONSE = (
        "DISCOVERY_RESPONSE"  # Node responds to discovery request with introspection
    )
    DISCOVERY_BROADCAST = "DISCOVERY_BROADCAST"  # Periodic announcements from nodes
    DISCOVERY_ACKNOWLEDGMENT = (
        "DISCOVERY_ACKNOWLEDGMENT"  # Bootstrap acknowledges node announcement
    )
    NODE_ANNOUNCEMENT = "NODE_ANNOUNCEMENT"  # Node announces itself for discovery
    NODE_DISCONNECT = "NODE_DISCONNECT"  # Node announces disconnection
    # --- Event-driven discovery event types ---
    NODE_INTROSPECTION_EVENT = "NODE_INTROSPECTION_EVENT"  # Node publishes capabilities
    NODE_HEALTH_EVENT = "NODE_HEALTH_EVENT"  # Node publishes health metrics
    NODE_SHUTDOWN_EVENT = "NODE_SHUTDOWN_EVENT"  # Node announces shutdown
    # --- Request-response introspection event types ---
    REQUEST_REAL_TIME_INTROSPECTION = (
        "REQUEST_REAL_TIME_INTROSPECTION"  # Request real-time introspection
    )
    REAL_TIME_INTROSPECTION_RESPONSE = (
        "REAL_TIME_INTROSPECTION_RESPONSE"  # Response to introspection request
    )
    # Add more event types as needed


# Backwards compatibility - allow importing from old location
__all__ = ["OnexEventTypeEnum"]
