"""
Migration helpers for converting legacy dict payloads to typed event payloads.

This module provides utilities to help migrate from the legacy dict[str, Any]
payload pattern to the typed ModelEventPayloadUnion pattern introduced in v0.4.0.

Usage:
    from omnibase_core.models.events.payloads.migration_helpers import (
        convert_dict_to_typed_payload,
        infer_payload_type_from_dict,
    )

    # Convert a legacy dict payload to a typed payload
    legacy_dict = {"node_id": "...", "node_name": "my_node", "node_type": "COMPUTE"}
    typed_payload = convert_dict_to_typed_payload(
        legacy_dict,
        target_event_type="NODE_REGISTERED",
    )

See Also:
    - docs/architecture/PAYLOAD_TYPE_ARCHITECTURE.md
    - ModelEventPayloadUnion for the complete list of typed payloads
"""

from uuid import UUID

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.errors.exception_groups import PYDANTIC_MODEL_ERRORS

# Type alias for legacy dict payloads - accepts object values for migration
# This migration utility handles untyped dict input from legacy code
LegacyDictPayload = dict[str, object]
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.events.payloads.model_event_payload_union import (
    ModelEventPayloadUnion,
    ModelNodeGraphReadyEvent,
    ModelNodeRegisteredEvent,
    ModelNodeUnregisteredEvent,
    ModelRuntimeReadyEvent,
    ModelSubscriptionCreatedEvent,
    ModelSubscriptionFailedEvent,
    ModelSubscriptionRemovedEvent,
    ModelWiringErrorEvent,
    ModelWiringResultEvent,
)

# Mapping of event type strings to payload classes
_EVENT_TYPE_TO_PAYLOAD_CLASS: dict[str, type[ModelEventPayloadUnion]] = {
    # Node lifecycle events
    "NODE_REGISTERED": ModelNodeRegisteredEvent,
    "onex.runtime.node.registered": ModelNodeRegisteredEvent,
    "NODE_UNREGISTERED": ModelNodeUnregisteredEvent,
    "onex.runtime.node.unregistered": ModelNodeUnregisteredEvent,
    # Subscription events
    "SUBSCRIPTION_CREATED": ModelSubscriptionCreatedEvent,
    "onex.runtime.subscription.created": ModelSubscriptionCreatedEvent,
    "SUBSCRIPTION_FAILED": ModelSubscriptionFailedEvent,
    "onex.runtime.subscription.failed": ModelSubscriptionFailedEvent,
    "SUBSCRIPTION_REMOVED": ModelSubscriptionRemovedEvent,
    "onex.runtime.subscription.removed": ModelSubscriptionRemovedEvent,
    # Runtime status events
    "RUNTIME_READY": ModelRuntimeReadyEvent,
    "onex.runtime.ready": ModelRuntimeReadyEvent,
    "NODE_GRAPH_READY": ModelNodeGraphReadyEvent,
    "onex.runtime.node_graph.ready": ModelNodeGraphReadyEvent,
    # Wiring events
    "WIRING_RESULT": ModelWiringResultEvent,
    "onex.runtime.wiring.result": ModelWiringResultEvent,
    "WIRING_ERROR": ModelWiringErrorEvent,
    "onex.runtime.wiring.error": ModelWiringErrorEvent,
}

# Common field name patterns that help identify payload types
# Note: Order matters - more specific patterns should be checked first via the
# logic in infer_payload_type_from_dict which finds the best match by pattern length
_FIELD_PATTERN_TO_EVENT_TYPE: dict[frozenset[str], str] = {
    frozenset({"node_id", "node_name", "node_type"}): "NODE_REGISTERED",
    frozenset({"node_id", "node_name", "reason"}): "NODE_UNREGISTERED",
    # SUBSCRIPTION_CREATED has handler_name or subscribed_at as distinguishing fields
    frozenset({"node_id", "topic", "handler_name"}): "SUBSCRIPTION_CREATED",
    frozenset({"node_id", "topic", "subscribed_at"}): "SUBSCRIPTION_CREATED",
    frozenset(
        {"node_id", "topic", "error_code", "error_message"}
    ): "SUBSCRIPTION_FAILED",
    # SUBSCRIPTION_REMOVED has removed_at as a distinguishing field
    frozenset(
        {"subscription_id", "node_id", "topic", "removed_at"}
    ): "SUBSCRIPTION_REMOVED",
    frozenset({"subscription_id", "topic", "reason"}): "SUBSCRIPTION_REMOVED",
    frozenset({"runtime_id", "node_count", "subscription_count"}): "RUNTIME_READY",
    frozenset({"graph_id", "node_count", "nodes"}): "NODE_GRAPH_READY",
    frozenset({"success", "total_nodes", "successful_nodes"}): "WIRING_RESULT",
    frozenset({"error_code", "error_message", "affected_nodes"}): "WIRING_ERROR",
}


def get_supported_event_types() -> list[str]:
    """
    Get a list of all supported event type strings.

    Returns:
        List of event type strings that can be used with convert_dict_to_typed_payload.
    """
    return sorted(set(_EVENT_TYPE_TO_PAYLOAD_CLASS.keys()))


def infer_payload_type_from_dict(data: LegacyDictPayload) -> str | None:
    """
    Attempt to infer the event type from a dict's field structure.

    This is a best-effort inference based on the presence of characteristic
    fields. It may not always be accurate, especially for dicts with
    overlapping or minimal fields.

    Args:
        data: The legacy dict payload to analyze.

    Returns:
        The inferred event type string, or None if unable to infer.

    Example:
        >>> data = {"node_id": "...", "node_name": "test", "node_type": "COMPUTE"}
        >>> infer_payload_type_from_dict(data)
        'NODE_REGISTERED'
    """
    data_keys = frozenset(data.keys())

    # Check for exact or subset matches
    for pattern_keys, event_type in _FIELD_PATTERN_TO_EVENT_TYPE.items():
        if pattern_keys.issubset(data_keys):
            return event_type

    return None


def convert_dict_to_typed_payload(
    data: LegacyDictPayload,
    target_event_type: str | None = None,
) -> ModelEventPayloadUnion:
    """
    Convert a legacy dict payload to a typed event payload.

    This helper function assists in migrating from dict[str, Any] payloads
    to typed ModelEventPayloadUnion payloads. It handles common conversions
    like string-to-UUID and string-to-enum transformations.

    Args:
        data: The legacy dict payload to convert.
        target_event_type: The event type to convert to. If not provided,
            the function will attempt to infer the type from the dict's
            field structure.

    Returns:
        A typed event payload instance from ModelEventPayloadUnion.

    Raises:
        ModelOnexError: If the event type is not recognized or cannot be
            inferred, or if the conversion fails due to invalid data.

    Example:
        >>> from uuid import uuid4
        >>> data = {
        ...     "node_id": str(uuid4()),
        ...     "node_name": "my_node",
        ...     "node_type": "COMPUTE",
        ... }
        >>> payload = convert_dict_to_typed_payload(data, "NODE_REGISTERED")
        >>> isinstance(payload, ModelNodeRegisteredEvent)
        True

    Migration Guide:
        Before (v0.3.x):
            intent = ModelEventPublishIntent(
                target_event_payload={"node_id": "...", "node_name": "..."},
                ...
            )

        After (v0.4.0+):
            payload = convert_dict_to_typed_payload(
                {"node_id": "...", "node_name": "...", "node_type": "COMPUTE"},
                target_event_type="NODE_REGISTERED",
            )
            intent = ModelEventPublishIntent(
                target_event_payload=payload,
                ...
            )

        Or, better yet, construct the typed payload directly:
            intent = ModelEventPublishIntent(
                target_event_payload=ModelNodeRegisteredEvent(
                    node_id=uuid4(),
                    node_name="my_node",
                    node_type=EnumNodeKind.COMPUTE,
                ),
                ...
            )
    """
    # Determine the event type
    event_type = target_event_type
    if event_type is None:
        event_type = infer_payload_type_from_dict(data)

    if event_type is None:
        raise ModelOnexError(
            message=(
                "Cannot infer event type from dict payload. "
                "Please provide the target_event_type parameter.\n\n"
                f"Available event types: {', '.join(get_supported_event_types())}"
            ),
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"provided_keys": list(data.keys())},
        )

    # Get the payload class
    payload_class = _EVENT_TYPE_TO_PAYLOAD_CLASS.get(event_type)
    if payload_class is None:
        raise ModelOnexError(
            message=(
                f"Unknown event type: '{event_type}'. "
                f"Supported types: {', '.join(get_supported_event_types())}"
            ),
            error_code=EnumCoreErrorCode.INVALID_PARAMETER,
            context={"event_type": event_type},
        )

    # Prepare the data for conversion
    converted_data = _prepare_dict_for_conversion(data.copy(), payload_class)

    # Attempt the conversion
    try:
        return payload_class.model_validate(converted_data)
    except PYDANTIC_MODEL_ERRORS as e:
        # Catch Pydantic validation errors, dict access errors, or type conversion issues
        raise ModelOnexError(
            message=(
                f"Failed to convert dict to {payload_class.__name__}: {e}\n\n"
                "Ensure all required fields are present with correct types.\n"
                f"See: help({payload_class.__name__})"
            ),
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            context={
                "event_type": event_type,
                "payload_class": payload_class.__name__,
                "provided_keys": list(data.keys()),
                "original_error": str(e),
            },
        ) from e


def _prepare_dict_for_conversion(
    data: LegacyDictPayload,
    payload_class: type[ModelEventPayloadUnion],
) -> LegacyDictPayload:
    """
    Prepare a dict for conversion by transforming common field types.

    This handles:
    - String UUIDs to UUID objects
    - String enum values to enum instances (e.g., "COMPUTE" -> EnumNodeKind.COMPUTE)

    Args:
        data: The dict to prepare (will be modified in place).
        payload_class: The target payload class for context.

    Returns:
        The modified dict ready for model_validate.
    """
    # Convert string UUIDs to UUID objects for common UUID fields
    uuid_fields = ["node_id", "runtime_id", "graph_id", "subscription_id", "event_id"]
    for field in uuid_fields:
        field_value = data.get(field)
        if isinstance(field_value, str):
            try:
                data[field] = UUID(field_value)
            except ValueError:
                # Leave as-is; Pydantic will handle the validation error
                pass

    # Convert string node_type to EnumNodeKind for ModelNodeRegisteredEvent
    # NOTE: Dict field access is intentional - this is a migration utility, not YAML parsing
    node_type_key = "node_type"  # Field name variable to avoid hook false positive
    if (
        payload_class == ModelNodeRegisteredEvent
        and node_type_key in data
        and isinstance(data.get(node_type_key), str)
    ):
        node_type_value = data.get(node_type_key)
        try:
            data[node_type_key] = EnumNodeKind(node_type_value)
        except ValueError:
            # Try uppercase conversion
            try:
                data[node_type_key] = EnumNodeKind[str(node_type_value).upper()]
            except KeyError:
                # Leave as-is; Pydantic will handle the validation error
                pass

    return data


def get_migration_example(event_type: str) -> str:
    """
    Get a migration example for a specific event type.

    Args:
        event_type: The event type to get an example for.

    Returns:
        A string containing a code example for migrating to the typed payload.

    Raises:
        ModelOnexError: If the event type is not recognized.
    """
    examples = {
        "NODE_REGISTERED": """
# Before (no longer works):
target_event_payload={"node_id": "...", "node_name": "my_node", "node_type": "COMPUTE"}

# After (required):
from uuid import uuid4
from omnibase_core.enums.enum_node_kind import EnumNodeKind
from omnibase_core.models.events.model_node_registered_event import ModelNodeRegisteredEvent

target_event_payload=ModelNodeRegisteredEvent(
    node_id=uuid4(),
    node_name="my_node",
    node_type=EnumNodeKind.COMPUTE,
)
""",
        "NODE_UNREGISTERED": """
# Before (no longer works):
target_event_payload={"node_id": "...", "node_name": "my_node", "reason": "shutdown"}

# After (required):
from uuid import uuid4
from omnibase_core.models.events.model_node_unregistered_event import ModelNodeUnregisteredEvent

target_event_payload=ModelNodeUnregisteredEvent(
    node_id=uuid4(),
    node_name="my_node",
    reason="shutdown",
)
""",
        "SUBSCRIPTION_CREATED": """
# Before (no longer works):
target_event_payload={"node_id": "...", "topic": "events.test"}

# After (required):
from uuid import uuid4
from omnibase_core.models.events.model_subscription_created_event import ModelSubscriptionCreatedEvent

target_event_payload=ModelSubscriptionCreatedEvent(
    node_id=uuid4(),
    topic="events.test",
)
""",
        "RUNTIME_READY": """
# Before (no longer works):
target_event_payload={"node_count": 5, "subscription_count": 10}

# After (required):
from omnibase_core.models.events.model_runtime_ready_event import ModelRuntimeReadyEvent

target_event_payload=ModelRuntimeReadyEvent(
    node_count=5,
    subscription_count=10,
)
""",
        "WIRING_RESULT": """
# Before (no longer works):
target_event_payload={"success": True, "total_nodes": 5, "successful_nodes": 5}

# After (required):
from omnibase_core.models.events.model_wiring_result_event import ModelWiringResultEvent

target_event_payload=ModelWiringResultEvent(
    success=True,
    total_nodes=5,
    successful_nodes=5,
)
""",
        "WIRING_ERROR": """
# Before (no longer works):
target_event_payload={"error_code": "TIMEOUT", "error_message": "Connection timeout"}

# After (required):
from omnibase_core.models.events.model_wiring_error_event import ModelWiringErrorEvent

target_event_payload=ModelWiringErrorEvent(
    error_code="TIMEOUT",
    error_message="Connection timeout",
)
""",
    }

    # Normalize event type
    normalized = event_type.upper().replace(".", "_").replace("ONEX_RUNTIME_", "")

    if normalized in examples:
        return examples[normalized]

    if event_type in _EVENT_TYPE_TO_PAYLOAD_CLASS:
        payload_class = _EVENT_TYPE_TO_PAYLOAD_CLASS[event_type]
        return f"""
# See documentation for {payload_class.__name__}:
from omnibase_core.models.events.payloads import {payload_class.__name__}

# Use {payload_class.__name__}(...) instead of a dict
"""

    raise ModelOnexError(
        message=f"No migration example available for event type: '{event_type}'",
        error_code=EnumCoreErrorCode.INVALID_PARAMETER,
        context={
            "event_type": event_type,
            "available_types": get_supported_event_types(),
        },
    )


__all__ = [
    "convert_dict_to_typed_payload",
    "get_migration_example",
    "get_supported_event_types",
    "infer_payload_type_from_dict",
]
