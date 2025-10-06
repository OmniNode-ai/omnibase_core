"""Constants module for omnibase_core."""

from omnibase_core.constants import constants_contract_fields
from omnibase_core.constants.constants_contract_fields import (
    BACKEND_KEY,
    CUSTOM_KEY,
    DEFAULT_PROCESSED_VALUE,
    INTEGRATION_KEY,
    PROCESSED_KEY,
)
from omnibase_core.constants.event_types import (
    NODE_FAILURE,
    NODE_HEALTH_CHECK,
    NODE_HEALTH_EVENT,
    NODE_INTROSPECTION_EVENT,
    NODE_SHUTDOWN_EVENT,
    NODE_START,
    NODE_SUCCESS,
    REAL_TIME_INTROSPECTION_RESPONSE,
    REQUEST_REAL_TIME_INTROSPECTION,
    SERVICE_DISCOVERY,
    TOOL_DISCOVERY_REQUEST,
    TOOL_DISCOVERY_RESPONSE,
    TOOL_INVOCATION,
    TOOL_RESPONSE,
    normalize_legacy_event_type,
)

__all__ = [
    "constants_contract_fields",
    "normalize_legacy_event_type",
    # Event type constants
    "NODE_FAILURE",
    "NODE_HEALTH_CHECK",
    "NODE_HEALTH_EVENT",
    "NODE_INTROSPECTION_EVENT",
    "NODE_SHUTDOWN_EVENT",
    "NODE_START",
    "NODE_SUCCESS",
    "REAL_TIME_INTROSPECTION_RESPONSE",
    "REQUEST_REAL_TIME_INTROSPECTION",
    "SERVICE_DISCOVERY",
    "TOOL_DISCOVERY_REQUEST",
    "TOOL_DISCOVERY_RESPONSE",
    "TOOL_INVOCATION",
    "TOOL_RESPONSE",
    # Output field processing keys
    "BACKEND_KEY",
    "CUSTOM_KEY",
    "DEFAULT_PROCESSED_VALUE",
    "INTEGRATION_KEY",
    "PROCESSED_KEY",
]
