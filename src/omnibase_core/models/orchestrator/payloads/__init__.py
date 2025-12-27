"""
Typed Payloads for ModelAction.

This module provides typed payload support for ModelAction, replacing the
untyped `dict[str, Any]` payload field with structured, validated payloads.

The payload system is organized by **semantic operation type** (what the action
does) rather than by node type (where it executes). This is intentional:
- A COMPUTE node might perform "transform", "validate", or "aggregate" operations
- An EFFECT node might perform "read", "write", or "sync" operations
- The semantic categorization provides more precise type safety

Re-exports all payload types from omnibase_core.models.core for convenience.
"""

# Re-export base class
from omnibase_core.models.core.model_action_payload_base import ModelActionPayloadBase

# Re-export union and factory from types module
from omnibase_core.models.core.model_action_payload_types import (
    SpecificActionPayload,
    create_specific_action_payload,
)

# Re-export all specific payload types
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
from omnibase_core.models.core.model_operational_action_payload import (
    ModelOperationalActionPayload,
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

# Import integration utilities
from omnibase_core.models.orchestrator.payloads.model_action_typed_payload import (
    ActionPayloadType,
    create_action_payload,
    get_recommended_payloads_for_action_type,
)

# Protocol for structural typing
from omnibase_core.models.orchestrator.payloads.model_protocol_action_payload import (
    ActionPayloadList,
    ProtocolActionPayload,
)

__all__ = [
    # Protocol for structural typing
    "ProtocolActionPayload",
    "ActionPayloadList",
    # Base class
    "ModelActionPayloadBase",
    # Specific payload types
    "ModelLifecycleActionPayload",
    "ModelOperationalActionPayload",
    "ModelDataActionPayload",
    "ModelValidationActionPayload",
    "ModelManagementActionPayload",
    "ModelTransformationActionPayload",
    "ModelMonitoringActionPayload",
    "ModelRegistryActionPayload",
    "ModelFilesystemActionPayload",
    "ModelCustomActionPayload",
    # Union type
    "SpecificActionPayload",
    # Type alias for ModelAction
    "ActionPayloadType",
    # Factory functions
    "create_specific_action_payload",
    "create_action_payload",
    "get_recommended_payloads_for_action_type",
]
