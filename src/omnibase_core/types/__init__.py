from datetime import datetime
from typing import Any, TypedDict

from pydantic import Field

"""
ONEX Types Module.

This module contains TypedDict definitions and type constraints following ONEX patterns.
TypedDicts provide type safety for dictionary structures without runtime overhead.
Type constraints provide protocols and type variables for better generic programming.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module's __init__.py is loaded whenever ANY submodule is imported (e.g., types.core_types).
To avoid circular dependencies, imports from .constraints are now LAZY-LOADED.

Import Chain:
1. types.core_types (minimal types, no external deps)
2. errors.error_codes → imports types.core_types → loads THIS __init__.py
3. models.common.model_schema_value → imports errors.error_codes
4. types.constraints → TYPE_CHECKING import of errors.error_codes
5. models.* → imports types.constraints

If this module directly imports from .constraints at module level, it creates:
error_codes → types.__init__ → constraints → (circular back to error_codes via models)

Solution: Use TYPE_CHECKING and __getattr__ for lazy loading, similar to ModelBaseCollection.
"""

from typing import TYPE_CHECKING

# All constraint imports are now lazy-loaded via __getattr__ to prevent circular imports
# Core types for breaking circular dependencies
# Converter functions
from .constraints import (
    BaseCollection,
    BaseFactory,
    BasicValueType,
    CollectionItemType,
    ComplexContextValueType,
    Configurable,
    ConfigurableType,
    ContextValueType,
    ErrorType,
    Executable,
    ExecutableType,
    Identifiable,
    IdentifiableType,
    MetadataType,
    ModelBaseCollection,
    ModelBaseFactory,
    ModelType,
    Nameable,
    NameableType,
    NumericType,
    PrimitiveValueType,
    ProtocolMetadataProvider,
    ProtocolValidatable,
    Serializable,
    SerializableType,
    SimpleValueType,
    SuccessType,
    ValidatableType,
    is_complex_context_value,
    is_configurable,
    is_context_value,
    is_executable,
    is_identifiable,
    is_metadata_provider,
    is_nameable,
    is_primitive_value,
    is_serializable,
    is_validatable,
    validate_context_value,
    validate_primitive_value,
)
from .converter_error_details_to_typed_dict import convert_error_details_to_typed_dict
from .converter_health_to_typed_dict import convert_health_to_typed_dict
from .converter_stats_to_typed_dict import convert_stats_to_typed_dict
from .core_types import ProtocolSchemaValue, TypedDictBasicErrorContext

# TypedDict classes
from .typed_dict_analytics_summary_data import TypedDictAnalyticsSummaryData
from .typed_dict_audit_info import TypedDictAuditInfo
from .typed_dict_batch_processing_info import TypedDictBatchProcessingInfo
from .typed_dict_cache_info import TypedDictCacheInfo
from .typed_dict_capability_factory_kwargs import TypedDictCapabilityFactoryKwargs
from .typed_dict_categorization_update_data import TypedDictCategorizationUpdateData
from .typed_dict_cli_input_dict import TypedDictCliInputDict
from .typed_dict_collection_kwargs import (
    TypedDictCollectionCreateKwargs,
    TypedDictCollectionFromItemsKwargs,
)
from .typed_dict_configuration_settings import TypedDictConfigurationSettings
from .typed_dict_connection_info import TypedDictConnectionInfo
from .typed_dict_core_analytics import TypedDictCoreAnalytics
from .typed_dict_core_data import TypedDictCoreData
from .typed_dict_core_summary import TypedDictCoreSummary
from .typed_dict_debug_info_data import TypedDictDebugInfoData
from .typed_dict_dependency_info import TypedDictDependencyInfo
from .typed_dict_deprecation_summary import TypedDictDeprecationSummary
from .typed_dict_discovery_stats import TypedDictDiscoveryStats
from .typed_dict_documentation_summary_filtered import (
    TypedDictDocumentationSummaryFiltered,
)
from .typed_dict_error_data import TypedDictErrorData
from .typed_dict_error_details import TypedDictErrorDetails
from .typed_dict_event_info import TypedDictEventInfo
from .typed_dict_execution_stats import TypedDictExecutionStats
from .typed_dict_factory_kwargs import (
    TypedDictExecutionParams,
    TypedDictFactoryKwargs,
    TypedDictMessageParams,
    TypedDictMetadataParams,
)
from .typed_dict_feature_flags import TypedDictFeatureFlags
from .typed_dict_field_value import TypedDictFieldValue
from .typed_dict_function_documentation_summary_type import (
    TypedDictFunctionDocumentationSummaryType,
)
from .typed_dict_function_relationships_summary import (
    TypedDictFunctionRelationshipsSummary,
)
from .typed_dict_generic_metadata_dict import TypedDictGenericMetadataDict
from .typed_dict_health_status import TypedDictHealthStatus
from .typed_dict_input_state_fields import TypedDictInputStateFields
from .typed_dict_input_state_source_type import TypedDictInputStateSourceType
from .typed_dict_legacy_error import TypedDictLegacyError
from .typed_dict_legacy_health import TypedDictLegacyHealth
from .typed_dict_legacy_stats import TypedDictLegacyStats
from .typed_dict_metadata_dict import TypedDictMetadataDict
from .typed_dict_metrics import TypedDictMetrics
from .typed_dict_migration_conflict_base_dict import TypedDictMigrationConflictBaseDict
from .typed_dict_migration_duplicate_conflict_dict import (
    TypedDictMigrationDuplicateConflictDict,
)
from .typed_dict_migration_name_conflict_dict import TypedDictMigrationNameConflictDict
from .typed_dict_migration_step_dict import TypedDictMigrationStepDict
from .typed_dict_node_capabilities_summary import TypedDictNodeCapabilitiesSummary
from .typed_dict_node_configuration_summary import TypedDictNodeConfigurationSummary
from .typed_dict_node_connection_summary_type import TypedDictNodeConnectionSummaryType
from .typed_dict_node_core import TypedDictNodeCore
from .typed_dict_node_core_update_data import TypedDictNodeCoreUpdateData
from .typed_dict_node_execution_summary import TypedDictNodeExecutionSummary
from .typed_dict_node_feature_summary_type import TypedDictNodeFeatureSummaryType
from .typed_dict_node_info_summary_data import TypedDictNodeInfoSummaryData
from .typed_dict_node_metadata_summary import TypedDictNodeMetadataSummary
from .typed_dict_node_resource_constraint_kwargs import (
    TypedDictNodeResourceConstraintKwargs,
)
from .typed_dict_node_resource_summary_type import TypedDictNodeResourceSummaryType
from .typed_dict_node_rule_structure import TypedDictNodeRuleStructure
from .typed_dict_operation_result import TypedDictOperationResult
from .typed_dict_output_format_options_kwargs import TypedDictOutputFormatOptionsKwargs
from .typed_dict_performance_data import TypedDictPerformanceData
from .typed_dict_performance_metric_data import TypedDictPerformanceMetricData
from .typed_dict_performance_metrics import TypedDictPerformanceMetrics
from .typed_dict_performance_update_data import TypedDictPerformanceUpdateData
from .typed_dict_property_metadata import TypedDictPropertyMetadata
from .typed_dict_quality_data import TypedDictQualityData
from .typed_dict_quality_update_data import TypedDictQualityUpdateData
from .typed_dict_resource_usage import TypedDictResourceUsage
from .typed_dict_result_factory_kwargs import TypedDictResultFactoryKwargs
from .typed_dict_security_context import TypedDictSecurityContext

# New individual TypedDict classes extracted from typed_dict_structured_definitions.py
from .typed_dict_sem_ver import TypedDictSemVer
from .typed_dict_service_info import TypedDictServiceInfo
from .typed_dict_ssl_context_options import TypedDictSSLContextOptions
from .typed_dict_stats_collection import TypedDictStatsCollection
from .typed_dict_status_migration_result import TypedDictStatusMigrationResult
from .typed_dict_system_state import TypedDictSystemState
from .typed_dict_timestamp_data import TypedDictTimestampData
from .typed_dict_timestamp_update_data import TypedDictTimestampUpdateData
from .typed_dict_trace_info_data import TypedDictTraceInfoData
from .typed_dict_usage_metadata import TypedDictUsageMetadata
from .typed_dict_validation_metadata_type import TypedDictValidationMetadataType
from .typed_dict_validation_result import TypedDictValidationResult
from .typed_dict_validator_info import TypedDictValidatorInfo
from .typed_dict_workflow_state import TypedDictWorkflowState

# Utility functions
from .util_datetime_parser import parse_datetime

__all__ = [
    # Core types (no dependencies)
    "TypedDictBasicErrorContext",
    "ProtocolSchemaValue",
    "TypedDictCoreSummary",
    # Type constraints and protocols
    "ModelBaseCollection",
    "ModelBaseFactory",
    "BaseCollection",
    "BaseFactory",
    "BasicValueType",
    "CollectionItemType",
    "ComplexContextValueType",
    "Configurable",
    "ConfigurableType",
    "ContextValueType",
    "ErrorType",
    "Executable",
    "ExecutableType",
    "Identifiable",
    "IdentifiableType",
    "MetadataType",
    "ModelType",
    "Nameable",
    "NameableType",
    "NumericType",
    "PrimitiveValueType",
    "ProtocolMetadataProvider",
    "ProtocolValidatable",
    "Serializable",
    "SerializableType",
    "SimpleValueType",
    "SuccessType",
    "ValidatableType",
    "is_complex_context_value",
    "is_configurable",
    "is_context_value",
    "is_executable",
    "is_identifiable",
    "is_metadata_provider",
    "is_nameable",
    "is_primitive_value",
    "is_serializable",
    "is_validatable",
    "validate_context_value",
    "validate_primitive_value",
    # TypedDict definitions
    "TypedDictAnalyticsSummaryData",
    "TypedDictCapabilityFactoryKwargs",
    "TypedDictCategorizationUpdateData",
    "TypedDictCliInputDict",
    "TypedDictCollectionCreateKwargs",
    "TypedDictCollectionFromItemsKwargs",
    "TypedDictCoreAnalytics",
    "TypedDictDebugInfoData",
    "TypedDictDeprecationSummary",
    "TypedDictDiscoveryStats",
    "TypedDictDocumentationSummaryFiltered",
    "TypedDictExecutionParams",
    "TypedDictFactoryKwargs",
    "TypedDictFieldValue",
    "TypedDictFunctionDocumentationSummaryType",
    "TypedDictFunctionRelationshipsSummary",
    "TypedDictGenericMetadataDict",
    "TypedDictInputStateSourceType",
    "TypedDictMessageParams",
    "TypedDictMetadataParams",
    "TypedDictMigrationConflictBaseDict",
    "TypedDictMigrationDuplicateConflictDict",
    "TypedDictMigrationNameConflictDict",
    "TypedDictNodeCapabilitiesSummary",
    "TypedDictNodeConfigurationSummary",
    "TypedDictNodeConnectionSummaryType",
    "TypedDictNodeCore",
    "TypedDictNodeExecutionSummary",
    "TypedDictNodeFeatureSummaryType",
    "TypedDictNodeInfoSummaryData",
    "TypedDictNodeMetadataSummary",
    "TypedDictNodeResourceConstraintKwargs",
    "TypedDictNodeResourceSummaryType",
    "TypedDictNodeRuleStructure",
    "TypedDictOutputFormatOptionsKwargs",
    "TypedDictPerformanceMetricData",
    "TypedDictPerformanceMetrics",
    "TypedDictPropertyMetadata",
    "TypedDictQualityData",
    "TypedDictResultFactoryKwargs",
    "TypedDictSSLContextOptions",
    "TypedDictTimestampUpdateData",
    "TypedDictTraceInfoData",
    "TypedDictUsageMetadata",
    "TypedDictValidationMetadataType",
    # New individual TypedDict classes extracted from typed_dict_structured_definitions.py
    "TypedDictSemVer",
    "TypedDictExecutionStats",
    "TypedDictHealthStatus",
    "TypedDictInputStateFields",
    "TypedDictResourceUsage",
    "TypedDictConfigurationSettings",
    "TypedDictCoreData",
    "TypedDictValidationResult",
    "TypedDictMetrics",
    "TypedDictMetadataDict",
    "TypedDictErrorData",
    "TypedDictErrorDetails",
    "TypedDictOperationResult",
    "TypedDictWorkflowState",
    "TypedDictValidatorInfo",
    "TypedDictEventInfo",
    "TypedDictConnectionInfo",
    "TypedDictServiceInfo",
    "TypedDictDependencyInfo",
    "TypedDictCacheInfo",
    "TypedDictBatchProcessingInfo",
    "TypedDictSecurityContext",
    "TypedDictAuditInfo",
    "TypedDictFeatureFlags",
    "TypedDictStatsCollection",
    "TypedDictSystemState",
    "TypedDictLegacyStats",
    "TypedDictLegacyHealth",
    "TypedDictLegacyError",
    "TypedDictMigrationStepDict",
    "TypedDictNodeCoreUpdateData",
    "TypedDictPerformanceData",
    "TypedDictPerformanceUpdateData",
    "TypedDictQualityUpdateData",
    "TypedDictStatusMigrationResult",
    "TypedDictTimestampData",
    # Converter functions
    "convert_stats_to_typed_dict",
    "convert_health_to_typed_dict",
    "convert_error_details_to_typed_dict",
    # Utility functions
    "parse_datetime",
]


def __getattr__(name: str) -> object:
    """
    Lazy import for constraints module to avoid circular imports.

    All constraint imports are lazy-loaded to prevent circular dependency:
    error_codes → types.__init__ → constraints → models → error_codes
    """
    # List of all constraint exports that should be lazy-loaded
    constraint_exports = {
        "BaseCollection",
        "BaseFactory",
        "BasicValueType",
        "CollectionItemType",
        "ComplexContextValueType",
        "Configurable",
        "ConfigurableType",
        "ContextValueType",
        "ErrorType",
        "Executable",
        "ExecutableType",
        "Identifiable",
        "IdentifiableType",
        "MetadataType",
        "ModelType",
        "Nameable",
        "NameableType",
        "NumericType",
        "PrimitiveValueType",
        "ProtocolMetadataProvider",
        "ProtocolValidatable",
        "Serializable",
        "SerializableType",
        "SimpleValueType",
        "SuccessType",
        "ValidatableType",
        "is_complex_context_value",
        "is_configurable",
        "is_context_value",
        "is_executable",
        "is_identifiable",
        "is_metadata_provider",
        "is_nameable",
        "is_primitive_value",
        "is_serializable",
        "is_validatable",
        "validate_context_value",
        "validate_primitive_value",
    }

    # ModelBaseCollection and ModelBaseFactory come from models.base, not constraints
    if name in ("ModelBaseCollection", "ModelBaseFactory"):
        from omnibase_core.models.base import ModelBaseCollection, ModelBaseFactory

        globals()["ModelBaseCollection"] = ModelBaseCollection
        globals()["ModelBaseFactory"] = ModelBaseFactory
        return globals()[name]

    # All other constraint exports come from .constraints
    if name in constraint_exports:
        # Import from constraints module
        from omnibase_core.types import constraints

        attr = getattr(constraints, name)
        globals()[name] = attr
        return attr

    msg = f"module {__name__!r} has no attribute {name!r}"
    # error-ok: AttributeError is standard Python pattern for __getattr__
    raise AttributeError(msg)
