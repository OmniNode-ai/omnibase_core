"""
Action Payload Type Hierarchies.

Re-exports all payload types from their individual files and provides factory functions.
"""

from typing import Any, Union

# Import all payload types from their individual files
from omnibase_core.model.core.model_custom_action_payload import \
    ModelCustomActionPayload
from omnibase_core.model.core.model_data_action_payload import \
    ModelDataActionPayload
from omnibase_core.model.core.model_filesystem_action_payload import \
    ModelFilesystemActionPayload
from omnibase_core.model.core.model_lifecycle_action_payload import \
    ModelLifecycleActionPayload
from omnibase_core.model.core.model_management_action_payload import \
    ModelManagementActionPayload
from omnibase_core.model.core.model_monitoring_action_payload import \
    ModelMonitoringActionPayload
from omnibase_core.model.core.model_node_action_type import ModelNodeActionType
from omnibase_core.model.core.model_operational_action_payload import \
    ModelOperationalActionPayload
from omnibase_core.model.core.model_registry_action_payload import \
    ModelRegistryActionPayload
from omnibase_core.model.core.model_transformation_action_payload import \
    ModelTransformationActionPayload
from omnibase_core.model.core.model_validation_action_payload import \
    ModelValidationActionPayload

# Union type for all payload types
SpecificActionPayload = Union[
    ModelLifecycleActionPayload,
    ModelOperationalActionPayload,
    ModelDataActionPayload,
    ModelValidationActionPayload,
    ModelManagementActionPayload,
    ModelTransformationActionPayload,
    ModelMonitoringActionPayload,
    ModelRegistryActionPayload,
    ModelFilesystemActionPayload,
    ModelCustomActionPayload,
]


def create_specific_action_payload(
    action_type: ModelNodeActionType, **kwargs: Any
) -> SpecificActionPayload:
    """
    Create the appropriate specific payload type for an action.

    Args:
        action_type: The rich action type model
        **kwargs: Additional parameters for the payload

    Returns:
        Appropriate specific payload instance for the action type
    """
    from omnibase_core.model.core.predefined_categories import (LIFECYCLE,
                                                                MANAGEMENT,
                                                                OPERATION,
                                                                QUERY,
                                                                TRANSFORMATION,
                                                                VALIDATION)

    category_to_payload_map = {
        LIFECYCLE: ModelLifecycleActionPayload,
        OPERATION: ModelOperationalActionPayload,
        VALIDATION: ModelValidationActionPayload,
        MANAGEMENT: ModelManagementActionPayload,
        TRANSFORMATION: ModelTransformationActionPayload,
        QUERY: ModelMonitoringActionPayload,
    }

    # Special handling for certain action types
    if action_type.name in [
        "read",
        "write",
        "create",
        "update",
        "delete",
        "list",
        "search",
        "query",
    ]:
        return ModelDataActionPayload(action_type=action_type, **kwargs)
    elif action_type.name in ["register", "unregister", "discover"]:
        return ModelRegistryActionPayload(action_type=action_type, **kwargs)
    elif action_type.name in ["scan", "watch", "sync"]:
        return ModelFilesystemActionPayload(action_type=action_type, **kwargs)
    elif action_type.name == "custom":
        return ModelCustomActionPayload(action_type=action_type, **kwargs)

    # Use category-based mapping
    payload_class = category_to_payload_map.get(action_type.category)
    if payload_class:
        return payload_class(action_type=action_type, **kwargs)  # type: ignore

    raise ValueError(f"Unknown action type: {action_type.name}")
