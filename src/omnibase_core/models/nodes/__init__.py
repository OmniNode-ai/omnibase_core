"""
Node Management Models

Models for node definitions, capabilities, configurations, and information.
"""

from omnibase_core.models.core.model_node_info import ModelNodeInfo
from omnibase_core.models.nodes.model_node_metadata_info import ModelNodeMetadataInfo
from omnibase_core.types.typed_dict_deprecation_summary import (
    TypedDictDeprecationSummary,
)

from .model_function_deprecation_info import ModelFunctionDeprecationInfo
from .model_function_documentation import ModelFunctionDocumentation
from .model_function_node import ModelFunctionNode
from .model_function_relationships import ModelFunctionRelationships
from .model_node_capabilities_info import ModelNodeCapabilitiesInfo

# Node summary models
from .model_node_capabilities_summary import ModelNodeCapabilitiesSummary
from .model_node_capability import ModelNodeCapability
from .model_node_configuration import ModelNodeConfiguration
from .model_node_configuration_summary import ModelNodeConfigurationSummary
from .model_node_connection_settings import ModelNodeConnectionSettings
from .model_node_core_info import ModelNodeCoreInfo
from .model_node_core_info_summary import ModelNodeCoreInfoSummary

# New restructured sub-models
from .model_node_core_metadata import ModelNodeCoreMetadata
from .model_node_execution_settings import ModelNodeExecutionSettings
from .model_node_feature_flags import ModelNodeFeatureFlags
from .model_node_information import ModelNodeInformation
from .model_node_information_summary import ModelNodeInformationSummary
from .model_node_organization_metadata import ModelNodeOrganizationMetadata
from .model_node_resource_limits import ModelNodeResourceLimits
from .model_node_type import ModelNodeType

__all__ = [
    "ModelFunctionNode",
    "ModelNodeCapability",
    "ModelNodeConfiguration",
    "ModelNodeInfo",
    "ModelNodeInformation",
    "ModelNodeInformationSummary",
    "ModelNodeMetadataInfo",
    # New restructured sub-models
    "ModelNodeCoreMetadata",
    "ModelNodeOrganizationMetadata",
    "ModelNodeExecutionSettings",
    "ModelNodeResourceLimits",
    "ModelNodeFeatureFlags",
    "ModelNodeConnectionSettings",
    "ModelFunctionDocumentation",
    "TypedDictDeprecationSummary",
    "ModelFunctionDeprecationInfo",
    "ModelFunctionRelationships",
    "ModelNodeCoreInfo",
    "ModelNodeCapabilitiesInfo",
    # Node summary models
    "ModelNodeCapabilitiesSummary",
    "ModelNodeConfigurationSummary",
    "ModelNodeCoreInfoSummary",
    "ModelNodeType",
]

# NOTE: model_rebuild() calls removed - Pydantic v2 handles forward references automatically
# The explicit rebuilds at module level caused import failures for forward references
# Pydantic will rebuild models lazily when first accessed
