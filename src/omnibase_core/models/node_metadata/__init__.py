"""Node metadata models.

This module contains models related to node metadata, configuration, and status.
These models describe nodes themselves rather than implementing node functionality.
"""

# Function node metadata models
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
from omnibase_core.models.node_metadata.model_node_capability import ModelNodeCapability

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
from omnibase_core.models.node_metadata.model_node_core_info import ModelNodeCoreInfo
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
