# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Typed Payloads for ModelAction.

Typed payload support for ModelAction, replacing the
untyped `dict[str, Any]` payload field with structured, validated payloads.

The payload system is organized by **semantic operation type** (what the action
does) rather than by node type (where it executes). This is intentional:
- A COMPUTE node might perform "transform", "validate", or "aggregate" operations
- An EFFECT node might perform "read", "write", or "sync" operations
- The semantic categorization provides more precise type safety

Re-exports all payload types from omnibase_core.models.core for convenience.
"""

from __future__ import annotations

# Re-export base class
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.core.model_action_payload_base import (
        ModelActionPayloadBase,
    )

    # Re-export union and factory from types module
    from omnibase_core.models.core.model_action_payload_types import (
        SpecificActionPayload,
        create_specific_action_payload,
    )

    # Re-export all specific payload types
    from omnibase_core.models.core.model_custom_action_payload import (
        ModelCustomActionPayload,
    )
    from omnibase_core.models.core.model_data_action_payload import (
        ModelDataActionPayload,
    )
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelActionPayloadBase": (
        "omnibase_core.models.core.model_action_payload_base",
        "ModelActionPayloadBase",
    ),
    "SpecificActionPayload": (
        "omnibase_core.models.core.model_action_payload_types",
        "SpecificActionPayload",
    ),
    "create_specific_action_payload": (
        "omnibase_core.models.core.model_action_payload_types",
        "create_specific_action_payload",
    ),
    "ModelCustomActionPayload": (
        "omnibase_core.models.core.model_custom_action_payload",
        "ModelCustomActionPayload",
    ),
    "ModelDataActionPayload": (
        "omnibase_core.models.core.model_data_action_payload",
        "ModelDataActionPayload",
    ),
    "ModelFilesystemActionPayload": (
        "omnibase_core.models.core.model_filesystem_action_payload",
        "ModelFilesystemActionPayload",
    ),
    "ModelLifecycleActionPayload": (
        "omnibase_core.models.core.model_lifecycle_action_payload",
        "ModelLifecycleActionPayload",
    ),
    "ModelManagementActionPayload": (
        "omnibase_core.models.core.model_management_action_payload",
        "ModelManagementActionPayload",
    ),
    "ModelMonitoringActionPayload": (
        "omnibase_core.models.core.model_monitoring_action_payload",
        "ModelMonitoringActionPayload",
    ),
    "ModelOperationalActionPayload": (
        "omnibase_core.models.core.model_operational_action_payload",
        "ModelOperationalActionPayload",
    ),
    "ModelRegistryActionPayload": (
        "omnibase_core.models.core.model_registry_action_payload",
        "ModelRegistryActionPayload",
    ),
    "ModelTransformationActionPayload": (
        "omnibase_core.models.core.model_transformation_action_payload",
        "ModelTransformationActionPayload",
    ),
    "ModelValidationActionPayload": (
        "omnibase_core.models.core.model_validation_action_payload",
        "ModelValidationActionPayload",
    ),
    "ActionPayloadType": (
        "omnibase_core.models.orchestrator.payloads.model_action_typed_payload",
        "ActionPayloadType",
    ),
    "create_action_payload": (
        "omnibase_core.models.orchestrator.payloads.model_action_typed_payload",
        "create_action_payload",
    ),
    "get_recommended_payloads_for_action_type": (
        "omnibase_core.models.orchestrator.payloads.model_action_typed_payload",
        "get_recommended_payloads_for_action_type",
    ),
    "ActionPayloadList": (
        "omnibase_core.models.orchestrator.payloads.model_protocol_action_payload",
        "ActionPayloadList",
    ),
    "ProtocolActionPayload": (
        "omnibase_core.models.orchestrator.payloads.model_protocol_action_payload",
        "ProtocolActionPayload",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
