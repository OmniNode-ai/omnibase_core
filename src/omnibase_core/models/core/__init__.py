from typing import Generic

from pydantic import Field

from omnibase_core.models.core.model_custom_fields import ModelCustomFields

"""Core models for OmniBase - Core domain models only.

This module contains only core domain models to prevent circular dependencies.
Other domains should import from their respective modules directly.
"""

# Configuration base classes
from .model_configuration_base import ModelConfigurationBase

# Generic container pattern
from .model_container import ModelContainer
from .model_custom_fields_accessor import ModelCustomFieldsAccessor

# Custom properties pattern
from .model_custom_properties import ModelCustomProperties
from .model_environment_accessor import ModelEnvironmentAccessor

# Field accessor patterns
from .model_field_accessor import ModelFieldAccessor

# Generic collection pattern
from .model_generic_collection import ModelGenericCollection
from .model_generic_collection_summary import ModelGenericCollectionSummary

# Generic metadata pattern
from .model_generic_metadata import ModelGenericMetadata
from .model_generic_properties import ModelGenericProperties

# Version information
from .model_onex_version import ModelOnexVersionInfo
from .model_result_accessor import ModelResultAccessor
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
    from .model_node_info import ModelNodeInfo
    from .model_node_info_result import ModelNodeInfoResult
    from .model_node_information import ModelNodeConfiguration, ModelNodeInformation
    from .model_node_instance import ModelNodeInstance
    from .model_node_introspection_response import ModelNodeIntrospectionResponse
    from .model_node_metadata import ModelNodeMetadata
    from .model_node_metadata_block import ModelNodeMetadataBlock
    from .model_node_metadata_info import ModelNodeMetadataInfo
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
    # Configuration base classes
    "ModelConfigurationBase",
    "ModelTypedConfiguration",
    # Custom properties pattern
    "ModelCustomProperties",
    # Version information
    "ModelOnexVersionInfo",
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
]
