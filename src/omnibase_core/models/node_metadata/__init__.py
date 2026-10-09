# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Node metadata models.

Models related to node metadata, configuration, and status.
These models describe nodes themselves rather than implementing node functionality.
"""

from __future__ import annotations

# Function node metadata models
import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.models.node_metadata.model_function_deprecation_info import (
        ModelFunctionDeprecationInfo,
    )
    from omnibase_core.models.node_metadata.model_function_documentation import (
        ModelFunctionDocumentation,
    )
    from omnibase_core.models.node_metadata.model_function_node import ModelFunctionNode
    from omnibase_core.models.node_metadata.model_function_node_core import (
        ModelFunctionNodeCore,
    )
    from omnibase_core.models.node_metadata.model_function_node_metadata_class import (
        ModelFunctionNodeMetadata,
    )
    from omnibase_core.models.node_metadata.model_function_node_metadata_config import (
        ModelFunctionNodeMetadataConfig,
    )
    from omnibase_core.models.node_metadata.model_function_node_performance import (
        ModelFunctionNodePerformance,
    )
    from omnibase_core.models.node_metadata.model_function_node_summary import (
        ModelFunctionNodeSummary,
    )
    from omnibase_core.models.node_metadata.model_function_relationships import (
        ModelFunctionRelationships,
    )

    # Node capabilities models
    from omnibase_core.models.node_metadata.model_node_capabilities_info import (
        ModelNodeCapabilitiesInfo,
    )
    from omnibase_core.models.node_metadata.model_node_capabilities_summary import (
        ModelNodeCapabilitiesSummary,
    )
    from omnibase_core.models.node_metadata.model_node_capability import (
        ModelNodeCapability,
    )

    # Node configuration models
    from omnibase_core.models.node_metadata.model_node_configuration import (
        ModelNodeConfiguration,
    )
    from omnibase_core.models.node_metadata.model_node_configuration_summary import (
        ModelNodeConfigurationSummary,
    )
    from omnibase_core.models.node_metadata.model_node_configuration_value import (
        ModelNodeConfigurationStringValue,
    )
    from omnibase_core.models.node_metadata.model_node_connection_settings import (
        ModelNodeConnectionSettings,
    )

    # Node core metadata models
    from omnibase_core.models.node_metadata.model_node_core_info import (
        ModelNodeCoreInfo,
    )
    from omnibase_core.models.node_metadata.model_node_core_info_summary import (
        ModelNodeCoreInfoSummary,
    )
    from omnibase_core.models.node_metadata.model_node_core_metadata_class import (
        ModelNodeCoreMetadata,
    )
    from omnibase_core.models.node_metadata.model_node_execution_settings import (
        ModelNodeExecutionSettings,
    )
    from omnibase_core.models.node_metadata.model_node_feature_flags import (
        ModelNodeFeatureFlags,
    )
    from omnibase_core.models.node_metadata.model_node_information import (
        ModelNodeInformation,
    )
    from omnibase_core.models.node_metadata.model_node_information_summary import (
        ModelNodeInformationSummary,
    )
    from omnibase_core.models.node_metadata.model_node_metadata_info import (
        ModelNodeMetadataInfo,
    )
    from omnibase_core.models.node_metadata.model_node_organization_metadata import (
        ModelNodeOrganizationMetadata,
    )
    from omnibase_core.models.node_metadata.model_node_resource_limits import (
        ModelNodeResourceLimits,
    )

    # Node status models
    from omnibase_core.models.node_metadata.model_node_status_active import (
        ModelNodeStatusActive,
    )
    from omnibase_core.models.node_metadata.model_node_status_error import (
        ModelNodeStatusError,
    )
    from omnibase_core.models.node_metadata.model_node_status_maintenance import (
        ModelNodeStatusMaintenance,
    )

    # Node type model
    from omnibase_core.models.node_metadata.model_node_type import ModelNodeType
    from omnibase_core.models.node_metadata.model_nodeconfigurationnumericvalue import (
        ModelNodeConfigurationNumericValue,
    )
    from omnibase_core.types.typed_dict_function_metadata_summary import (
        TypedDictFunctionMetadataSummary,
    )

__all__ = [
    # Function node metadata
    "ModelFunctionDeprecationInfo",
    "ModelFunctionDocumentation",
    "TypedDictFunctionMetadataSummary",
    "ModelFunctionNode",
    "ModelFunctionNodeCore",
    "ModelFunctionNodeMetadata",
    "ModelFunctionNodeMetadataConfig",
    "ModelFunctionNodePerformance",
    "ModelFunctionNodeSummary",
    "ModelFunctionRelationships",
    # Node capabilities
    "ModelNodeCapabilitiesInfo",
    "ModelNodeCapabilitiesSummary",
    "ModelNodeCapability",
    # Node configuration
    "ModelNodeConfiguration",
    "ModelNodeConfigurationNumericValue",
    "ModelNodeConfigurationStringValue",
    "ModelNodeConfigurationSummary",
    "ModelNodeConnectionSettings",
    # Node core metadata
    "ModelNodeCoreInfo",
    "ModelNodeCoreInfoSummary",
    "ModelNodeCoreMetadata",
    "ModelNodeExecutionSettings",
    "ModelNodeFeatureFlags",
    "ModelNodeInformation",
    "ModelNodeInformationSummary",
    "ModelNodeMetadataInfo",
    "ModelNodeOrganizationMetadata",
    "ModelNodeResourceLimits",
    # Node status
    "ModelNodeStatusActive",
    "ModelNodeStatusError",
    "ModelNodeStatusMaintenance",
    # Node type
    "ModelNodeType",
]


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelFunctionDeprecationInfo": (
        "omnibase_core.models.node_metadata.model_function_deprecation_info",
        "ModelFunctionDeprecationInfo",
    ),
    "ModelFunctionDocumentation": (
        "omnibase_core.models.node_metadata.model_function_documentation",
        "ModelFunctionDocumentation",
    ),
    "ModelFunctionNode": (
        "omnibase_core.models.node_metadata.model_function_node",
        "ModelFunctionNode",
    ),
    "ModelFunctionNodeCore": (
        "omnibase_core.models.node_metadata.model_function_node_core",
        "ModelFunctionNodeCore",
    ),
    "ModelFunctionNodeMetadata": (
        "omnibase_core.models.node_metadata.model_function_node_metadata_class",
        "ModelFunctionNodeMetadata",
    ),
    "ModelFunctionNodeMetadataConfig": (
        "omnibase_core.models.node_metadata.model_function_node_metadata_config",
        "ModelFunctionNodeMetadataConfig",
    ),
    "ModelFunctionNodePerformance": (
        "omnibase_core.models.node_metadata.model_function_node_performance",
        "ModelFunctionNodePerformance",
    ),
    "ModelFunctionNodeSummary": (
        "omnibase_core.models.node_metadata.model_function_node_summary",
        "ModelFunctionNodeSummary",
    ),
    "ModelFunctionRelationships": (
        "omnibase_core.models.node_metadata.model_function_relationships",
        "ModelFunctionRelationships",
    ),
    "ModelNodeCapabilitiesInfo": (
        "omnibase_core.models.node_metadata.model_node_capabilities_info",
        "ModelNodeCapabilitiesInfo",
    ),
    "ModelNodeCapabilitiesSummary": (
        "omnibase_core.models.node_metadata.model_node_capabilities_summary",
        "ModelNodeCapabilitiesSummary",
    ),
    "ModelNodeCapability": (
        "omnibase_core.models.node_metadata.model_node_capability",
        "ModelNodeCapability",
    ),
    "ModelNodeConfiguration": (
        "omnibase_core.models.node_metadata.model_node_configuration",
        "ModelNodeConfiguration",
    ),
    "ModelNodeConfigurationSummary": (
        "omnibase_core.models.node_metadata.model_node_configuration_summary",
        "ModelNodeConfigurationSummary",
    ),
    "ModelNodeConfigurationStringValue": (
        "omnibase_core.models.node_metadata.model_node_configuration_value",
        "ModelNodeConfigurationStringValue",
    ),
    "ModelNodeConnectionSettings": (
        "omnibase_core.models.node_metadata.model_node_connection_settings",
        "ModelNodeConnectionSettings",
    ),
    "ModelNodeCoreInfo": (
        "omnibase_core.models.node_metadata.model_node_core_info",
        "ModelNodeCoreInfo",
    ),
    "ModelNodeCoreInfoSummary": (
        "omnibase_core.models.node_metadata.model_node_core_info_summary",
        "ModelNodeCoreInfoSummary",
    ),
    "ModelNodeCoreMetadata": (
        "omnibase_core.models.node_metadata.model_node_core_metadata_class",
        "ModelNodeCoreMetadata",
    ),
    "ModelNodeExecutionSettings": (
        "omnibase_core.models.node_metadata.model_node_execution_settings",
        "ModelNodeExecutionSettings",
    ),
    "ModelNodeFeatureFlags": (
        "omnibase_core.models.node_metadata.model_node_feature_flags",
        "ModelNodeFeatureFlags",
    ),
    "ModelNodeInformation": (
        "omnibase_core.models.node_metadata.model_node_information",
        "ModelNodeInformation",
    ),
    "ModelNodeInformationSummary": (
        "omnibase_core.models.node_metadata.model_node_information_summary",
        "ModelNodeInformationSummary",
    ),
    "ModelNodeMetadataInfo": (
        "omnibase_core.models.node_metadata.model_node_metadata_info",
        "ModelNodeMetadataInfo",
    ),
    "ModelNodeOrganizationMetadata": (
        "omnibase_core.models.node_metadata.model_node_organization_metadata",
        "ModelNodeOrganizationMetadata",
    ),
    "ModelNodeResourceLimits": (
        "omnibase_core.models.node_metadata.model_node_resource_limits",
        "ModelNodeResourceLimits",
    ),
    "ModelNodeStatusActive": (
        "omnibase_core.models.node_metadata.model_node_status_active",
        "ModelNodeStatusActive",
    ),
    "ModelNodeStatusError": (
        "omnibase_core.models.node_metadata.model_node_status_error",
        "ModelNodeStatusError",
    ),
    "ModelNodeStatusMaintenance": (
        "omnibase_core.models.node_metadata.model_node_status_maintenance",
        "ModelNodeStatusMaintenance",
    ),
    "ModelNodeType": (
        "omnibase_core.models.node_metadata.model_node_type",
        "ModelNodeType",
    ),
    "ModelNodeConfigurationNumericValue": (
        "omnibase_core.models.node_metadata.model_nodeconfigurationnumericvalue",
        "ModelNodeConfigurationNumericValue",
    ),
    "TypedDictFunctionMetadataSummary": (
        "omnibase_core.types.typed_dict_function_metadata_summary",
        "TypedDictFunctionMetadataSummary",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
