# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

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
EVENT_TYPE_CONTRACT_REGISTERED = "contract-registered"
EVENT_TYPE_CONTRACT_DEREGISTERED = "contract-deregistered"
EVENT_TYPE_NODE_HEARTBEAT = "node-heartbeat"

# Full Kafka topic names for contract registration events
TOPIC_CONTRACT_REGISTERED_EVENT = "onex.evt.contract-registered.v1"
TOPIC_CONTRACT_DEREGISTERED_EVENT = "onex.evt.contract-deregistered.v1"
TOPIC_NODE_HEARTBEAT_EVENT = "onex.evt.node-heartbeat.v1"

# Workflow automation event topics (OMN-2655, OMN-2813)
# Normalized to 5-segment format: onex.{kind}.{producer}.{event}.v{n}
TOPIC_GITHUB_PR_STATUS_EVENT = "onex.evt.platform.github-pr-status.v1"
TOPIC_GIT_HOOK_EVENT = "onex.evt.platform.git-hook.v1"
TOPIC_LINEAR_SNAPSHOT_EVENT = "onex.evt.platform.linear-snapshot.v1"

# CLI run-node command topics (used by ``onex run-node`` CLI for ad-hoc node dispatch)
# These are informal topics used only by the CLI tool for direct node invocation.
# Production node communication uses contract-defined topics from contract.yaml.
TOPIC_CLI_RUN_NODE_CMD = "onex.cmd.platform.run-node.v1"
TOPIC_CLI_RUN_NODE_RESPONSE = "onex.evt.platform.run-node-response.v1"

# Omniintelligence event topics
TOPIC_EPISODE_BOUNDARY = "onex.evt.omniintelligence.episode-boundary.v1"

# Validation event topics
TOPIC_VALIDATION_RUN_COMPLETED_EVENT = "onex.evt.validation.cross-repo-run-completed.v1"
TOPIC_VALIDATION_RUN_STARTED_EVENT = "onex.evt.validation.cross-repo-run-started.v1"
TOPIC_VALIDATION_VIOLATIONS_BATCH_EVENT = (
    "onex.evt.validation.cross-repo-violations-batch.v1"
)

# Runtime event type alias strings used in legacy payload migration (OMN-8635)
# These are NOT Kafka topic names — they are legacy event-type identifiers used as
# lookup keys to map wire-format strings to typed payload classes.
EVENT_TYPE_ALIAS_NODE_REGISTERED = "onex.runtime.node.registered"
EVENT_TYPE_ALIAS_NODE_UNREGISTERED = "onex.runtime.node.unregistered"
EVENT_TYPE_ALIAS_SUBSCRIPTION_CREATED = "onex.runtime.subscription.created"
EVENT_TYPE_ALIAS_SUBSCRIPTION_FAILED = "onex.runtime.subscription.failed"
EVENT_TYPE_ALIAS_SUBSCRIPTION_REMOVED = "onex.runtime.subscription.removed"
EVENT_TYPE_ALIAS_RUNTIME_READY = "onex.runtime.ready"
EVENT_TYPE_ALIAS_NODE_GRAPH_READY = "onex.runtime.node_graph.ready"
EVENT_TYPE_ALIAS_WIRING_RESULT = "onex.runtime.wiring.result"
EVENT_TYPE_ALIAS_WIRING_ERROR = "onex.runtime.wiring.error"


def normalize_legacy_event_type(event_type: str | TypedDictEventType | object) -> str:
    """Normalize legacy event types to consistent string format.

    Compatibility by converting various
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
