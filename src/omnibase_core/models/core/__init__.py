# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Core domain models — configuration, envelopes, flags, topology, metadata.

Circular-dependency boundary: imports from this package must not reference
transport, infra, or Kafka modules. For ModelSemVer import directly:
``from omnibase_core.models.primitives.model_semver import ModelSemVer``.
"""

from __future__ import annotations

# Configuration base classes
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Node models - migrated from archived
    from omnibase_core.models.core.model_node_info import ModelNodeInfo
    from omnibase_core.models.node_metadata.model_node_metadata_info import (
        ModelNodeMetadataInfo,
    )

    # Generic factory pattern
    from .model_capability_factory import ModelCapabilityFactory
    from .model_configuration_base import ModelConfigurationBase

    # Generic container pattern
    from .model_container import ModelContainer
    from .model_custom_fields_accessor import ModelCustomFieldsAccessor

    # Custom properties pattern
    from .model_custom_properties import ModelCustomProperties

    # Deployment topology models (OMN-3490)
    from .model_deployment_topology import ModelDeploymentTopology
    from .model_deployment_topology_database import ModelDeploymentTopologyDatabase
    from .model_deployment_topology_database_binding import (
        ModelDeploymentTopologyDatabaseBinding,
    )
    from .model_deployment_topology_database_grant import (
        ModelDeploymentTopologyDatabaseGrant,
    )
    from .model_deployment_topology_database_migration_ledger import (
        ModelDeploymentTopologyDatabaseMigrationLedger,
    )
    from .model_deployment_topology_database_owner import (
        ModelDeploymentTopologyDatabaseOwner,
    )
    from .model_deployment_topology_database_principal import (
        ModelDeploymentTopologyDatabasePrincipal,
    )
    from .model_deployment_topology_database_schema import (
        ModelDeploymentTopologyDatabaseSchema,
    )
    from .model_deployment_topology_local_config import (
        ModelDeploymentTopologyLocalConfig,
    )
    from .model_deployment_topology_service import ModelDeploymentTopologyService

    # Event envelope patterns
    from .model_envelope_metadata import ModelEnvelopeMetadata
    from .model_environment_accessor import ModelEnvironmentAccessor

    # Error details model
    from .model_error_details import ErrorContext, ModelErrorDetails, TContext

    # Feature flags pattern
    from .model_feature_flag_definition import ModelFeatureFlagDefinition
    from .model_feature_flag_metadata import ModelFeatureFlagMetadata
    from .model_feature_flag_resolution import ModelFeatureFlagResolution
    from .model_feature_flag_summary import ModelFeatureFlagSummary
    from .model_feature_flags import ModelFeatureFlags

    # Field accessor patterns
    from .model_field_accessor import ModelFieldAccessor

    # Generic collection pattern
    from .model_generic_collection import ModelGenericCollection
    from .model_generic_collection_summary import ModelGenericCollectionSummary
    from .model_generic_factory import ModelGenericFactory
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
    from .model_node_action import ModelNodeAction
    from .model_node_action_type import ModelNodeActionType
    from .model_node_action_validator import ModelNodeActionValidator
    from .model_node_announce_metadata import ModelNodeAnnounceMetadata
    from .model_node_base import ModelNodeBase
    from .model_node_contract_data import ModelNodeContractData
    from .model_node_data import ModelNodeData
    from .model_node_discovery import ModelNodeDiscovery
    from .model_node_discovery_result import ModelNodeDiscoveryResult
    from .model_node_execution_result import (
        ModelExecutionData,
        ModelNodeExecutionResult,
    )
    from .model_node_info_result import ModelNodeInfoResult
    from .model_node_instance import ModelNodeInstance
    from .model_node_introspection_response import ModelNodeIntrospectionResponse
    from .model_node_metadata import ModelNodeMetadata
    from .model_node_metadata_block import ModelNodeMetadataBlock
    from .model_node_reference import ModelNodeReference
    from .model_node_reference_metadata import ModelNodeReferenceMetadata
    from .model_node_status import ModelNodeStatus
    from .model_node_template import ModelNodeTemplateConfig
    from .model_node_version_constraints import ModelNodeVersionConstraints

    # Version information
    from .model_onex_version import ModelOnexVersionInfo

    # Generic metadata pattern
    from .model_protocol_metadata import ModelGenericMetadata
    from .model_result_accessor import ModelResultAccessor
    from .model_result_factory import ModelResultFactory

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
    from .model_validation_error_factory import ModelValidationErrorFactory

    # Workflow models
    from .model_workflow import ModelWorkflow


__all__ = [
    # Storage checkpoint metadata pattern
    "ModelStorageCheckpointMetadata",
    # Deployment topology models (OMN-3490)
    "ModelDeploymentTopology",
    "ModelDeploymentTopologyDatabase",
    "ModelDeploymentTopologyDatabaseBinding",
    "ModelDeploymentTopologyDatabaseGrant",
    "ModelDeploymentTopologyDatabaseMigrationLedger",
    "ModelDeploymentTopologyDatabaseOwner",
    "ModelDeploymentTopologyDatabasePrincipal",
    "ModelDeploymentTopologyDatabaseSchema",
    "ModelDeploymentTopologyLocalConfig",
    "ModelDeploymentTopologyService",
    # Configuration base classes
    "ModelConfigurationBase",
    "ModelTypedConfiguration",
    # Custom properties pattern
    "ModelCustomProperties",
    # Error details model
    "ErrorContext",
    "ModelErrorDetails",
    "TContext",
    # Feature flags pattern
    "ModelFeatureFlagDefinition",
    "ModelFeatureFlagMetadata",
    "ModelFeatureFlagResolution",
    "ModelFeatureFlagSummary",
    "ModelFeatureFlags",
    # Version information
    "ModelOnexVersionInfo",
    # Event envelope patterns
    "ModelEnvelopeMetadata",
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
    "ModelNodeContractData",
    "ModelNodeData",
    "ModelExecutionData",
    "ModelNodeDiscovery",
    "ModelNodeDiscoveryResult",
    "ModelNodeExecutionResult",
    "ModelNodeInfo",
    "ModelNodeInfoResult",
    "ModelNodeInstance",
    "ModelNodeIntrospectionResponse",
    "ModelNodeMetadata",
    "ModelNodeMetadataBlock",
    "ModelNodeMetadataInfo",
    "ModelNodeReference",
    "ModelNodeReferenceMetadata",
    "ModelNodeStatus",
    "ModelNodeTemplateConfig",
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelConfigurationBase": (
        "omnibase_core.models.core.model_configuration_base",
        "ModelConfigurationBase",
    ),
    "ModelContainer": ("omnibase_core.models.core.model_container", "ModelContainer"),
    "ModelCustomFieldsAccessor": (
        "omnibase_core.models.core.model_custom_fields_accessor",
        "ModelCustomFieldsAccessor",
    ),
    "ModelCustomProperties": (
        "omnibase_core.models.core.model_custom_properties",
        "ModelCustomProperties",
    ),
    "ModelDeploymentTopology": (
        "omnibase_core.models.core.model_deployment_topology",
        "ModelDeploymentTopology",
    ),
    "ModelDeploymentTopologyDatabase": (
        "omnibase_core.models.core.model_deployment_topology_database",
        "ModelDeploymentTopologyDatabase",
    ),
    "ModelDeploymentTopologyDatabaseBinding": (
        "omnibase_core.models.core.model_deployment_topology_database_binding",
        "ModelDeploymentTopologyDatabaseBinding",
    ),
    "ModelDeploymentTopologyDatabaseGrant": (
        "omnibase_core.models.core.model_deployment_topology_database_grant",
        "ModelDeploymentTopologyDatabaseGrant",
    ),
    "ModelDeploymentTopologyDatabaseMigrationLedger": (
        "omnibase_core.models.core.model_deployment_topology_database_migration_ledger",
        "ModelDeploymentTopologyDatabaseMigrationLedger",
    ),
    "ModelDeploymentTopologyDatabaseOwner": (
        "omnibase_core.models.core.model_deployment_topology_database_owner",
        "ModelDeploymentTopologyDatabaseOwner",
    ),
    "ModelDeploymentTopologyDatabasePrincipal": (
        "omnibase_core.models.core.model_deployment_topology_database_principal",
        "ModelDeploymentTopologyDatabasePrincipal",
    ),
    "ModelDeploymentTopologyDatabaseSchema": (
        "omnibase_core.models.core.model_deployment_topology_database_schema",
        "ModelDeploymentTopologyDatabaseSchema",
    ),
    "ModelDeploymentTopologyLocalConfig": (
        "omnibase_core.models.core.model_deployment_topology_local_config",
        "ModelDeploymentTopologyLocalConfig",
    ),
    "ModelDeploymentTopologyService": (
        "omnibase_core.models.core.model_deployment_topology_service",
        "ModelDeploymentTopologyService",
    ),
    "ModelEnvelopeMetadata": (
        "omnibase_core.models.core.model_envelope_metadata",
        "ModelEnvelopeMetadata",
    ),
    "ModelEnvironmentAccessor": (
        "omnibase_core.models.core.model_environment_accessor",
        "ModelEnvironmentAccessor",
    ),
    "ErrorContext": ("omnibase_core.models.core.model_error_details", "ErrorContext"),
    "ModelErrorDetails": (
        "omnibase_core.models.core.model_error_details",
        "ModelErrorDetails",
    ),
    "TContext": ("omnibase_core.models.core.model_error_details", "TContext"),
    "ModelFeatureFlagDefinition": (
        "omnibase_core.models.core.model_feature_flag_definition",
        "ModelFeatureFlagDefinition",
    ),
    "ModelFeatureFlagMetadata": (
        "omnibase_core.models.core.model_feature_flag_metadata",
        "ModelFeatureFlagMetadata",
    ),
    "ModelFeatureFlagResolution": (
        "omnibase_core.models.core.model_feature_flag_resolution",
        "ModelFeatureFlagResolution",
    ),
    "ModelFeatureFlagSummary": (
        "omnibase_core.models.core.model_feature_flag_summary",
        "ModelFeatureFlagSummary",
    ),
    "ModelFeatureFlags": (
        "omnibase_core.models.core.model_feature_flags",
        "ModelFeatureFlags",
    ),
    "ModelFieldAccessor": (
        "omnibase_core.models.core.model_field_accessor",
        "ModelFieldAccessor",
    ),
    "ModelGenericCollection": (
        "omnibase_core.models.core.model_generic_collection",
        "ModelGenericCollection",
    ),
    "ModelGenericCollectionSummary": (
        "omnibase_core.models.core.model_generic_collection_summary",
        "ModelGenericCollectionSummary",
    ),
    "ModelGenericProperties": (
        "omnibase_core.models.core.model_generic_properties",
        "ModelGenericProperties",
    ),
    "ModelMixinCodePatterns": (
        "omnibase_core.models.core.model_mixin_code_patterns",
        "ModelMixinCodePatterns",
    ),
    "ModelMixinConfigField": (
        "omnibase_core.models.core.model_mixin_config_field",
        "ModelMixinConfigField",
    ),
    "ModelMixinMetadata": (
        "omnibase_core.models.core.model_mixin_metadata",
        "ModelMixinMetadata",
    ),
    "ModelMixinMetadataCollection": (
        "omnibase_core.models.core.model_mixin_metadata_collection",
        "ModelMixinMetadataCollection",
    ),
    "ModelMixinMethod": (
        "omnibase_core.models.core.model_mixin_method",
        "ModelMixinMethod",
    ),
    "ModelMixinPerformance": (
        "omnibase_core.models.core.model_mixin_performance",
        "ModelMixinPerformance",
    ),
    "ModelMixinPreset": (
        "omnibase_core.models.core.model_mixin_preset",
        "ModelMixinPreset",
    ),
    "ModelMixinProperty": (
        "omnibase_core.models.core.model_mixin_property",
        "ModelMixinProperty",
    ),
    "ModelMixinVersion": (
        "omnibase_core.models.core.model_mixin_version",
        "ModelMixinVersion",
    ),
    "ModelOnexVersionInfo": (
        "omnibase_core.models.core.model_onex_version",
        "ModelOnexVersionInfo",
    ),
    "ModelGenericMetadata": (
        "omnibase_core.models.core.model_protocol_metadata",
        "ModelGenericMetadata",
    ),
    "ModelResultAccessor": (
        "omnibase_core.models.core.model_result_accessor",
        "ModelResultAccessor",
    ),
    "ModelStorageCheckpointMetadata": (
        "omnibase_core.models.core.model_storage_checkpoint_metadata",
        "ModelStorageCheckpointMetadata",
    ),
    "ModelToolIntegration": (
        "omnibase_core.models.core.model_tool_integration",
        "ModelToolIntegration",
    ),
    "ModelToolIntegrationSummary": (
        "omnibase_core.models.core.model_tool_integration_summary",
        "ModelToolIntegrationSummary",
    ),
    "ModelToolResourceRequirements": (
        "omnibase_core.models.core.model_tool_resource_requirements",
        "ModelToolResourceRequirements",
    ),
    "ModelToolTimeoutSettings": (
        "omnibase_core.models.core.model_tool_timeout_settings",
        "ModelToolTimeoutSettings",
    ),
    "ModelToolVersionSummary": (
        "omnibase_core.models.core.model_tool_version_summary",
        "ModelToolVersionSummary",
    ),
    "ModelTypedAccessor": (
        "omnibase_core.models.core.model_typed_accessor",
        "ModelTypedAccessor",
    ),
    "ModelTypedConfiguration": (
        "omnibase_core.models.core.model_typed_configuration",
        "ModelTypedConfiguration",
    ),
    "ModelCapabilityFactory": (
        "omnibase_core.models.core.model_capability_factory",
        "ModelCapabilityFactory",
    ),
    "ModelGenericFactory": (
        "omnibase_core.models.core.model_generic_factory",
        "ModelGenericFactory",
    ),
    "ModelResultFactory": (
        "omnibase_core.models.core.model_result_factory",
        "ModelResultFactory",
    ),
    "ModelValidationErrorFactory": (
        "omnibase_core.models.core.model_validation_error_factory",
        "ModelValidationErrorFactory",
    ),
    "ModelNodeInfo": ("omnibase_core.models.core.model_node_info", "ModelNodeInfo"),
    "ModelNodeMetadataInfo": (
        "omnibase_core.models.node_metadata.model_node_metadata_info",
        "ModelNodeMetadataInfo",
    ),
    "ModelNodeAction": (
        "omnibase_core.models.core.model_node_action",
        "ModelNodeAction",
    ),
    "ModelNodeActionType": (
        "omnibase_core.models.core.model_node_action_type",
        "ModelNodeActionType",
    ),
    "ModelNodeActionValidator": (
        "omnibase_core.models.core.model_node_action_validator",
        "ModelNodeActionValidator",
    ),
    "ModelNodeAnnounceMetadata": (
        "omnibase_core.models.core.model_node_announce_metadata",
        "ModelNodeAnnounceMetadata",
    ),
    "ModelNodeBase": ("omnibase_core.models.core.model_node_base", "ModelNodeBase"),
    "ModelNodeContractData": (
        "omnibase_core.models.core.model_node_contract_data",
        "ModelNodeContractData",
    ),
    "ModelNodeData": ("omnibase_core.models.core.model_node_data", "ModelNodeData"),
    "ModelNodeDiscovery": (
        "omnibase_core.models.core.model_node_discovery",
        "ModelNodeDiscovery",
    ),
    "ModelNodeDiscoveryResult": (
        "omnibase_core.models.core.model_node_discovery_result",
        "ModelNodeDiscoveryResult",
    ),
    "ModelExecutionData": (
        "omnibase_core.models.core.model_node_execution_result",
        "ModelExecutionData",
    ),
    "ModelNodeExecutionResult": (
        "omnibase_core.models.core.model_node_execution_result",
        "ModelNodeExecutionResult",
    ),
    "ModelNodeInfoResult": (
        "omnibase_core.models.core.model_node_info_result",
        "ModelNodeInfoResult",
    ),
    "ModelNodeInstance": (
        "omnibase_core.models.core.model_node_instance",
        "ModelNodeInstance",
    ),
    "ModelNodeIntrospectionResponse": (
        "omnibase_core.models.core.model_node_introspection_response",
        "ModelNodeIntrospectionResponse",
    ),
    "ModelNodeMetadata": (
        "omnibase_core.models.core.model_node_metadata",
        "ModelNodeMetadata",
    ),
    "ModelNodeMetadataBlock": (
        "omnibase_core.models.core.model_node_metadata_block",
        "ModelNodeMetadataBlock",
    ),
    "ModelNodeReference": (
        "omnibase_core.models.core.model_node_reference",
        "ModelNodeReference",
    ),
    "ModelNodeReferenceMetadata": (
        "omnibase_core.models.core.model_node_reference_metadata",
        "ModelNodeReferenceMetadata",
    ),
    "ModelNodeStatus": (
        "omnibase_core.models.core.model_node_status",
        "ModelNodeStatus",
    ),
    "ModelNodeTemplateConfig": (
        "omnibase_core.models.core.model_node_template",
        "ModelNodeTemplateConfig",
    ),
    "ModelNodeVersionConstraints": (
        "omnibase_core.models.core.model_node_version_constraints",
        "ModelNodeVersionConstraints",
    ),
    "ModelWorkflow": ("omnibase_core.models.core.model_workflow", "ModelWorkflow"),
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
