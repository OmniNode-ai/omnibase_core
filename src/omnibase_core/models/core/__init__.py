"""Core models for OmniBase - Core domain models only.

This module contains only core domain models to prevent circular dependencies.
Other domains should import from their respective modules directly.

Note: ModelSemVer is located in omnibase_core.models.primitives.model_semver.
Import directly: from omnibase_core.models.primitives.model_semver import ModelSemVer
"""

# Configuration base classes
from .model_configuration_base import ModelConfigurationBase

# Generic container pattern
from .model_container import ModelContainer
from .model_custom_fields_accessor import ModelCustomFieldsAccessor

# Custom properties pattern
from .model_custom_properties import ModelCustomProperties

# Event envelope patterns
from .model_envelope_metadata import ModelEnvelopeMetadata
from .model_environment_accessor import ModelEnvironmentAccessor

# Feature flags pattern
from .model_feature_flag_metadata import ModelFeatureFlagMetadata
from .model_feature_flag_summary import ModelFeatureFlagSummary
from .model_feature_flags import ModelFeatureFlags

# Field accessor patterns
from .model_field_accessor import ModelFieldAccessor

# Generic collection pattern
from .model_generic_collection import ModelGenericCollection
from .model_generic_collection_summary import ModelGenericCollectionSummary
from .model_generic_properties import ModelGenericProperties

# Mixin metadata pattern
from .model_mixin_code_patterns import ModelMixinCodePatterns
from .model_mixin_config_field import ModelMixinConfigField
from .model_mixin_metadata import ModelMixinMetadata
from .model_mixin_metadata_collection import ModelMixinMetadataCollection
from .model_mixin_method import ModelMixinMethod
from .model_mixin_performance import ModelMixinPerformance
from .model_mixin_preset import ModelMixinPreset
from .model_mixin_property import ModelMixinProperty
from .model_mixin_version import ModelMixinVersion
from .model_onex_envelope import ModelOnexEnvelope
from .model_onex_envelope_v1 import ModelOnexEnvelopeV1

# Version information
from .model_onex_version import ModelOnexVersionInfo

# Generic metadata pattern
from .model_protocol_metadata import ModelGenericMetadata
from .model_result_accessor import ModelResultAccessor

# Storage checkpoint metadata pattern
from .model_storage_checkpoint_metadata import ModelStorageCheckpointMetadata

# Tool integration models
from .model_tool_integration import ModelToolIntegration
from .model_tool_integration_summary import ModelToolIntegrationSummary
from .model_tool_resource_requirements import ModelToolResourceRequirements
from .model_tool_timeout_settings import ModelToolTimeoutSettings
from .model_tool_version_summary import ModelToolVersionSummary
from .model_typed_accessor import ModelTypedAccessor
from .model_typed_configuration import ModelTypedConfiguration

# Generic factory pattern
try:
    from .model_capability_factory import ModelCapabilityFactory
    from .model_generic_factory import ModelGenericFactory
    from .model_result_factory import ModelResultFactory
    from .model_validation_error_factory import ModelValidationErrorFactory

    _FACTORY_AVAILABLE = True
except ImportError:
    # Graceful degradation if circular imports prevent loading
    _FACTORY_AVAILABLE = False

# Node models - migrated from archived
try:
    from omnibase_core.models.core.model_node_info import ModelNodeInfo
    from omnibase_core.models.node_metadata.model_node_metadata_info import (
        ModelNodeMetadataInfo,
    )

    from .model_node_action import ModelNodeAction
    from .model_node_action_type import ModelNodeActionType
    from .model_node_action_validator import ModelNodeActionValidator
    from .model_node_announce_metadata import ModelNodeAnnounceMetadata
    from .model_node_base import ModelNodeBase
    from .model_node_capability import ModelNodeCapability
    from .model_node_contract_data import ModelNodeContractData
    from .model_node_data import ModelNodeData
    from .model_node_discovery import ModelNodeDiscovery
    from .model_node_discovery_result import ModelNodeDiscoveryResult
    from .model_node_execution_result import (
        ModelExecutionData,
        ModelNodeExecutionResult,
    )
    from .model_node_info_result import ModelNodeInfoResult
    from .model_node_information import ModelNodeConfiguration, ModelNodeInformation
    from .model_node_instance import ModelNodeInstance
    from .model_node_introspection_response import ModelNodeIntrospectionResponse
    from .model_node_metadata import ModelNodeMetadata
    from .model_node_metadata_block import ModelNodeMetadataBlock
    from .model_node_reference import ModelNodeReference
    from .model_node_reference_metadata import ModelNodeReferenceMetadata
    from .model_node_status import ModelNodeStatus
    from .model_node_template import ModelNodeTemplateConfig
    from .model_node_type import ModelNodeType
    from .model_node_version_constraints import ModelNodeVersionConstraints

    _NODE_MODELS_AVAILABLE = True
except ImportError:
    # Graceful degradation if circular imports prevent loading
    _NODE_MODELS_AVAILABLE = False

# Workflow models
try:
    from .model_workflow import ModelWorkflow

    _WORKFLOW_MODELS_AVAILABLE = True
except ImportError:
    # Graceful degradation if circular imports prevent loading
    _WORKFLOW_MODELS_AVAILABLE = False

__all__ = [
    # Storage checkpoint metadata pattern
    "ModelStorageCheckpointMetadata",
    # Configuration base classes
    "ModelConfigurationBase",
    "ModelTypedConfiguration",
    # Custom properties pattern
    "ModelCustomProperties",
    # Feature flags pattern
    "ModelFeatureFlagMetadata",
    "ModelFeatureFlagSummary",
    "ModelFeatureFlags",
    # Version information
    "ModelOnexVersionInfo",
    # Event envelope patterns
    "ModelEnvelopeMetadata",
    "ModelOnexEnvelope",
    "ModelOnexEnvelopeV1",
    # Generic container pattern
    "ModelContainer",
    # Field accessor patterns
    "ModelFieldAccessor",
    "ModelTypedAccessor",
    "ModelEnvironmentAccessor",
    "ModelResultAccessor",
    "ModelCustomFieldsAccessor",
    # Generic collection pattern
    "ModelGenericCollection",
    "ModelGenericCollectionSummary",
    # Generic metadata pattern
    "ModelGenericMetadata",
    "ModelGenericProperties",
    # Mixin metadata pattern
    "ModelMixinMetadata",
    "ModelMixinMetadataCollection",
    "ModelMixinVersion",
    "ModelMixinMethod",
    "ModelMixinProperty",
    "ModelMixinConfigField",
    "ModelMixinPreset",
    "ModelMixinPerformance",
    "ModelMixinCodePatterns",
    # Factory patterns (with graceful degradation)
    "ModelCapabilityFactory",
    "ModelGenericFactory",
    "ModelResultFactory",
    "ModelValidationErrorFactory",
    # Node models (migrated from archived)
    "ModelNodeAction",
    "ModelNodeActionType",
    "ModelNodeActionValidator",
    "ModelNodeAnnounceMetadata",
    "ModelNodeBase",
    "ModelNodeCapability",
    "ModelNodeContractData",
    "ModelNodeData",
    "ModelExecutionData",
    "ModelNodeDiscovery",
    "ModelNodeDiscoveryResult",
    "ModelNodeExecutionResult",
    "ModelNodeInfo",
    "ModelNodeInfoResult",
    "ModelNodeInformation",
    "ModelNodeInstance",
    "ModelNodeConfiguration",
    "ModelNodeIntrospectionResponse",
    "ModelNodeMetadata",
    "ModelNodeMetadataBlock",
    "ModelNodeMetadataInfo",
    "ModelNodeReference",
    "ModelNodeReferenceMetadata",
    "ModelNodeStatus",
    "ModelNodeTemplateConfig",
    "ModelNodeType",
    "ModelNodeVersionConstraints",
    # Workflow models
    "ModelWorkflow",
    # Tool integration models
    "ModelToolIntegration",
    "ModelToolIntegrationSummary",
    "ModelToolResourceRequirements",
    "ModelToolTimeoutSettings",
    "ModelToolVersionSummary",
]
