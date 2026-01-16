"""
Typed Payload Integration for ModelAction.

Bridges EnumActionType (COMPUTE, EFFECT, REDUCE, ORCHESTRATE, CUSTOM) with the
semantic-category-based SpecificActionPayload system.

Design Decision:
----------------
The codebase already has a comprehensive typed payload system at
`omnibase_core.models.core.model_action_payload_*` organized by SEMANTIC
operation type (what the action does):
- Lifecycle: initialize, shutdown, health_check
- Data: read, write, create, update, delete
- Transformation: transform, convert, parse
- Operational: process, execute, run
- Validation: validate, verify, check
- Management: configure, deploy, migrate
- Monitoring: monitor, collect, report
- Registry: register, unregister, discover
- Filesystem: scan, watch, sync
- Custom: any custom operations

This is SUPERIOR to organizing by node type (COMPUTE/EFFECT/REDUCE/ORCHESTRATE)
because:
1. A single node type can handle multiple semantic operations
2. The semantic categorization provides more precise type safety
3. Payload fields directly match the operation being performed

This module provides:
1. `ActionPayloadType` - Type alias for use in ModelAction.payload field
2. `get_recommended_payloads_for_action_type()` - Mapping from EnumActionType
3. `create_action_payload()` - Factory for creating payloads based on action type

Usage Example:
--------------
```python
from omnibase_core.models.orchestrator.model_action import ModelAction
from omnibase_core.models.orchestrator.payloads import (
    ActionPayloadType,
    ModelDataActionPayload,
    create_action_payload,
)
from omnibase_core.enums.enum_workflow_execution import EnumActionType

# Create a typed payload for an EFFECT action that reads data
payload = create_action_payload(
    action_type=EnumActionType.EFFECT,
    semantic_action="read",
    target_path="/data/users.json",
    filters={"active": True},
)

# The payload is now fully typed as ModelDataActionPayload
assert isinstance(payload, ModelDataActionPayload)
```
"""

from omnibase_core.enums.enum_workflow_execution import EnumActionType
from omnibase_core.models.core.model_action_category import ModelActionCategory
from omnibase_core.models.core.model_action_payload_types import (
    SpecificActionPayload,
    create_specific_action_payload,
)
from omnibase_core.models.core.model_custom_action_payload import (
    ModelCustomActionPayload,
)
from omnibase_core.models.core.model_data_action_payload import ModelDataActionPayload
from omnibase_core.models.core.model_filesystem_action_payload import (
    ModelFilesystemActionPayload,
)
from omnibase_core.models.core.model_lifecycle_action_payload import (
    ModelLifecycleActionPayload,
)
from omnibase_core.models.core.model_management_action_payload import (
    ModelManagementActionPayload,
)
from omnibase_core.models.core.model_monitoring_action_payload import (
    ModelMonitoringActionPayload,
)
from omnibase_core.models.core.model_node_action_type import ModelNodeActionType
from omnibase_core.models.core.model_operational_action_payload import (
    ModelOperationalActionPayload,
)
from omnibase_core.models.core.model_predefined_categories import (
    LIFECYCLE,
    MANAGEMENT,
    OPERATION,
    QUERY,
    TRANSFORMATION,
    VALIDATION,
)
from omnibase_core.models.core.model_registry_action_payload import (
    ModelRegistryActionPayload,
)
from omnibase_core.models.core.model_transformation_action_payload import (
    ModelTransformationActionPayload,
)
from omnibase_core.models.core.model_validation_action_payload import (
    ModelValidationActionPayload,
)

__all__ = [
    # Type alias for ModelAction.payload field
    "ActionPayloadType",
    # Factory functions
    "create_action_payload",
    "get_recommended_payloads_for_action_type",
    "get_payload_type_for_semantic_action",
    # Re-exported payload types (for convenience)
    "ModelCustomActionPayload",
    "ModelDataActionPayload",
    "ModelFilesystemActionPayload",
    "ModelLifecycleActionPayload",
    "ModelManagementActionPayload",
    "ModelMonitoringActionPayload",
    "ModelOperationalActionPayload",
    "ModelRegistryActionPayload",
    "ModelTransformationActionPayload",
    "ModelValidationActionPayload",
    # Union type
    "SpecificActionPayload",
]

# Type alias for typed payloads in ModelAction
# union-ok: discriminated_model_union - Type alias representing all valid payload types
ActionPayloadType = SpecificActionPayload

# Mapping from EnumActionType to commonly used semantic payload types
# This is informational - the actual payload type depends on the semantic operation
_ACTION_TYPE_TO_PAYLOAD_RECOMMENDATIONS: dict[
    EnumActionType, list[type[SpecificActionPayload]]
] = {
    EnumActionType.COMPUTE: [
        ModelTransformationActionPayload,  # transform, convert, parse
        ModelValidationActionPayload,  # validate, verify, check
        ModelOperationalActionPayload,  # process, execute, run
    ],
    EnumActionType.EFFECT: [
        ModelDataActionPayload,  # read, write, create, update, delete
        ModelFilesystemActionPayload,  # scan, watch, sync
        ModelRegistryActionPayload,  # register, unregister, discover
        ModelLifecycleActionPayload,  # health_check, initialize, shutdown
    ],
    EnumActionType.REDUCE: [
        ModelOperationalActionPayload,  # aggregate, reduce
        ModelMonitoringActionPayload,  # collect, report
        ModelDataActionPayload,  # query, search
    ],
    EnumActionType.ORCHESTRATE: [
        ModelManagementActionPayload,  # configure, deploy, migrate
        ModelOperationalActionPayload,  # execute, run
        ModelLifecycleActionPayload,  # initialize, shutdown
    ],
    EnumActionType.CUSTOM: [
        ModelCustomActionPayload,  # any custom operations
    ],
}

# Default categories for each EnumActionType when semantic_action is not specified
_ACTION_TYPE_TO_DEFAULT_CATEGORY: dict[EnumActionType, ModelActionCategory] = {
    EnumActionType.COMPUTE: TRANSFORMATION,
    EnumActionType.EFFECT: OPERATION,
    EnumActionType.REDUCE: OPERATION,
    EnumActionType.ORCHESTRATE: MANAGEMENT,
    EnumActionType.CUSTOM: OPERATION,
}


def get_recommended_payloads_for_action_type(
    action_type: EnumActionType,
) -> list[type[SpecificActionPayload]]:
    """
    Get recommended payload types for a given EnumActionType.

    This is a guide for developers to understand which payload types are
    commonly used with each action type. The actual payload type should be
    chosen based on the semantic operation being performed.

    Args:
        action_type: The EnumActionType (COMPUTE, EFFECT, REDUCE, etc.)

    Returns:
        List of payload types commonly used with this action type

    Example:
        >>> payloads = get_recommended_payloads_for_action_type(EnumActionType.EFFECT)
        >>> print([p.__name__ for p in payloads])
        ['ModelDataActionPayload', 'ModelFilesystemActionPayload', ...]
    """
    return _ACTION_TYPE_TO_PAYLOAD_RECOMMENDATIONS.get(action_type, [])


def create_action_payload(
    action_type: EnumActionType,
    semantic_action: str | None = None,
    **kwargs: object,
) -> SpecificActionPayload:
    """
    Create a typed payload for an action based on action type and semantic operation.

    This factory function bridges EnumActionType with the semantic-category-based
    payload system. It creates a ModelNodeActionType internally and uses the
    existing create_specific_action_payload factory.

    Args:
        action_type: The EnumActionType (COMPUTE, EFFECT, REDUCE, ORCHESTRATE, CUSTOM)
        semantic_action: Optional semantic action name (e.g., "read", "transform").
                         If not provided or empty, a default based on action_type is used.
                         Empty string is treated as None for convenience.
        **kwargs: Additional keyword arguments passed to the payload constructor

    Returns:
        Appropriate SpecificActionPayload instance

    Example:
        >>> # Create a data payload for an EFFECT action
        >>> payload = create_action_payload(
        ...     action_type=EnumActionType.EFFECT,
        ...     semantic_action="read",
        ...     target_path="/data/users.json",
        ... )
        >>> assert isinstance(payload, ModelDataActionPayload)

        >>> # Create a transformation payload for a COMPUTE action
        >>> payload = create_action_payload(
        ...     action_type=EnumActionType.COMPUTE,
        ...     semantic_action="transform",
        ...     input_format="json",
        ...     output_format="yaml",
        ... )
        >>> assert isinstance(payload, ModelTransformationActionPayload)
    """
    # Treat empty string as None for convenience - use default action for type
    # This handles edge case where semantic_action="" is passed
    if semantic_action is None or semantic_action == "":
        # Use default based on action type
        default_names = {
            EnumActionType.COMPUTE: "process",
            EnumActionType.EFFECT: "execute",
            EnumActionType.REDUCE: "aggregate",
            EnumActionType.ORCHESTRATE: "coordinate",
            EnumActionType.CUSTOM: "custom",
        }
        semantic_action = default_names.get(action_type, "process")

    # Determine category
    category = _ACTION_TYPE_TO_DEFAULT_CATEGORY.get(action_type, OPERATION)

    # Override category based on well-known semantic actions
    category_overrides: dict[str, ModelActionCategory] = {
        # Lifecycle actions
        "health_check": LIFECYCLE,
        "initialize": LIFECYCLE,
        "shutdown": LIFECYCLE,
        "start": LIFECYCLE,
        "stop": LIFECYCLE,
        # Validation actions
        "validate": VALIDATION,
        "verify": VALIDATION,
        "check": VALIDATION,
        "test": VALIDATION,
        # Transformation actions
        "transform": TRANSFORMATION,
        "convert": TRANSFORMATION,
        "parse": TRANSFORMATION,
        "serialize": TRANSFORMATION,
        # Management actions
        "configure": MANAGEMENT,
        "deploy": MANAGEMENT,
        "migrate": MANAGEMENT,
        # Query actions
        "monitor": QUERY,
        "collect": QUERY,
        "report": QUERY,
        "alert": QUERY,
    }

    if semantic_action in category_overrides:
        category = category_overrides[semantic_action]

    # Create rich action type model
    node_action_type = ModelNodeActionType(
        name=semantic_action,
        category=category,
        display_name=semantic_action.replace("_", " ").title(),
        description=f"Action: {semantic_action} (via {action_type.value})",
    )

    # Use existing factory to create the specific payload
    return create_specific_action_payload(node_action_type, **kwargs)


# Mapping from semantic action names to their corresponding payload types
# Using a flat dict is more efficient and maintainable than nested if/elif chains
_SEMANTIC_ACTION_TO_PAYLOAD_TYPE: dict[str, type[SpecificActionPayload]] = {
    # Data actions
    "read": ModelDataActionPayload,
    "write": ModelDataActionPayload,
    "create": ModelDataActionPayload,
    "update": ModelDataActionPayload,
    "delete": ModelDataActionPayload,
    "search": ModelDataActionPayload,
    "query": ModelDataActionPayload,
    # Registry actions
    "register": ModelRegistryActionPayload,
    "unregister": ModelRegistryActionPayload,
    "discover": ModelRegistryActionPayload,
    # Filesystem actions
    "scan": ModelFilesystemActionPayload,
    "watch": ModelFilesystemActionPayload,
    "sync": ModelFilesystemActionPayload,
    # Custom action
    "custom": ModelCustomActionPayload,
    # Lifecycle actions
    "health_check": ModelLifecycleActionPayload,
    "initialize": ModelLifecycleActionPayload,
    "shutdown": ModelLifecycleActionPayload,
    "start": ModelLifecycleActionPayload,
    "stop": ModelLifecycleActionPayload,
    # Validation actions
    "validate": ModelValidationActionPayload,
    "verify": ModelValidationActionPayload,
    "check": ModelValidationActionPayload,
    "test": ModelValidationActionPayload,
    # Transformation actions
    "transform": ModelTransformationActionPayload,
    "convert": ModelTransformationActionPayload,
    "parse": ModelTransformationActionPayload,
    "serialize": ModelTransformationActionPayload,
    # Management actions
    "configure": ModelManagementActionPayload,
    "deploy": ModelManagementActionPayload,
    "migrate": ModelManagementActionPayload,
    # Monitoring/Query actions
    "monitor": ModelMonitoringActionPayload,
    "collect": ModelMonitoringActionPayload,
    "report": ModelMonitoringActionPayload,
    "alert": ModelMonitoringActionPayload,
}


def get_payload_type_for_semantic_action(
    semantic_action: str,
) -> type[SpecificActionPayload]:
    """
    Get the expected payload type for a semantic action name.

    This is useful for type checking and validation.

    Args:
        semantic_action: The semantic action name (e.g., "read", "transform")

    Returns:
        The payload type class expected for this action

    Note:
        Unknown actions default to ModelOperationalActionPayload rather than
        raising an error, as this allows extensibility for custom actions.
    """
    return _SEMANTIC_ACTION_TO_PAYLOAD_TYPE.get(
        semantic_action, ModelOperationalActionPayload
    )
