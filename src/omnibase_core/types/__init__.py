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

# Constraint imports are direct at module level for IDE support and import performance.
# The __getattr__ fallback at the bottom provides lazy-loading as a backup mechanism.
# Core types for breaking circular dependencies
# Converter functions
from .converter_error_details import convert_error_details_to_typed_dict
from .converter_health import convert_health_to_typed_dict
from .converter_stats import convert_stats_to_typed_dict

# Compute pipeline type aliases (for pipeline data flows)
from .type_compute_pipeline import (
    PathResolvedValue,
    PipelineData,
    PipelineDataDict,
    StepResultMapping,
    TransformInputT,
)
from .type_constraints import (
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
from .type_core import ProtocolSchemaValue, TypedDictBasicErrorContext

# Effect result type aliases (centralized to avoid primitive soup unions)
from .type_effect_result import DbParamType, EffectResultType

# JSON type aliases (centralized to avoid primitive soup unions)
from .type_json import (
    JsonPrimitive,
    JsonType,
    PrimitiveContainer,
    PrimitiveValue,
    StrictJsonPrimitive,
    StrictJsonType,
    ToolParameterValue,
)

# Schema type aliases (for type-safe schema patterns)
from .type_schema_aliases import SchemaDict, StepOutputs

# Serializable value types (for JSON-compatible data)
from .type_serializable_value import SerializableValue, SerializedDict
from .typed_dict_access_control_config import TypedDictAccessControlConfig
from .typed_dict_action_validation_context import TypedDictActionValidationContext
from .typed_dict_action_validation_statistics import TypedDictActionValidationStatistics
from .typed_dict_active_summary import TypedDictActiveSummary
from .typed_dict_additional_fields import TypedDictAdditionalFields
from .typed_dict_alert_data import TypedDictAlertData
from .typed_dict_alert_metadata import TypedDictAlertMetadata

# TypedDict classes
from .typed_dict_analytics_summary_data import TypedDictAnalyticsSummaryData
from .typed_dict_audit_change import TypedDictAuditChange
from .typed_dict_audit_info import TypedDictAuditInfo
from .typed_dict_batch_processing_info import TypedDictBatchProcessingInfo

# Computation output summary TypedDicts
from .typed_dict_binary_computation_summary import TypedDictBinaryComputationSummary
from .typed_dict_cache_info import TypedDictCacheInfo
from .typed_dict_capability_factory_kwargs import TypedDictCapabilityFactoryKwargs
from .typed_dict_categorization_update_data import TypedDictCategorizationUpdateData

# CLI model serialization TypedDict definitions
from .typed_dict_cli_action_serialized import TypedDictCliActionSerialized
from .typed_dict_cli_advanced_params_serialized import (
    TypedDictCliAdvancedParamsSerialized,
)
from .typed_dict_cli_command_option_serialized import (
    TypedDictCliCommandOptionSerialized,
)
from .typed_dict_cli_execution_context_serialized import (
    TypedDictCliExecutionContextSerialized,
)
from .typed_dict_cli_execution_core_serialized import (
    TypedDictCliExecutionCoreSerialized,
)
from .typed_dict_cli_execution_metadata_serialized import (
    TypedDictCliExecutionMetadataSerialized,
)
from .typed_dict_cli_input_dict import TypedDictCliInputDict
from .typed_dict_cli_node_execution_input_serialized import (
    TypedDictCliNodeExecutionInputSerialized,
)
from .typed_dict_collection_kwargs import (
    TypedDictCollectionCreateKwargs,
    TypedDictCollectionFromItemsKwargs,
)

# Metadata tool collection TypedDict definitions
from .typed_dict_collection_metadata import TypedDictCollectionMetadata
from .typed_dict_collection_validation import TypedDictCollectionValidation

# Node infrastructure TypedDict definitions
from .typed_dict_comprehensive_health import TypedDictComprehensiveHealth
from .typed_dict_computation_output_data_summary import (
    TypedDictComputationOutputDataSummary,
)
from .typed_dict_computation_output_summary import TypedDictComputationOutputSummary
from .typed_dict_conditional_branch import TypedDictConditionalBranch
from .typed_dict_configuration_settings import TypedDictConfigurationSettings
from .typed_dict_connection_info import TypedDictConnectionInfo
from .typed_dict_consumed_event_entry import TypedDictConsumedEventEntry

# Contract validation TypedDict definitions
from .typed_dict_contract_data import TypedDictContractData
from .typed_dict_conversation_message import TypedDictConversationMessage
from .typed_dict_converted_health import TypedDictConvertedHealth
from .typed_dict_core_analytics import TypedDictCoreAnalytics
from .typed_dict_core_data import TypedDictCoreData
from .typed_dict_core_summary import TypedDictCoreSummary

# Custom fields, policy value, and model-specific TypedDict definitions
from .typed_dict_custom_fields import CustomFieldsDict, TypedDictCustomFieldsDict
from .typed_dict_debug_info_data import TypedDictDebugInfoData
from .typed_dict_default_output_state import TypedDictDefaultOutputState
from .typed_dict_dependency_info import TypedDictDependencyInfo
from .typed_dict_deprecation_summary import TypedDictDeprecationSummary
from .typed_dict_discovery_stats import TypedDictDiscoveryStats
from .typed_dict_documentation_summary_filtered import (
    TypedDictDocumentationSummaryFiltered,
)
from .typed_dict_error_analysis import TypedDictErrorAnalysis
from .typed_dict_error_data import TypedDictErrorData
from .typed_dict_error_details import TypedDictErrorDetails
from .typed_dict_error_summary import TypedDictErrorSummary
from .typed_dict_event_envelope import TypedDictEventEnvelopeDict
from .typed_dict_event_info import TypedDictEventInfo
from .typed_dict_event_type import TypedDictEventType
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
from .typed_dict_function_metadata_summary import TypedDictFunctionMetadataSummary
from .typed_dict_function_relationships_summary import (
    TypedDictFunctionRelationshipsSummary,
)
from .typed_dict_generic_metadata_dict import TypedDictGenericMetadataDict
from .typed_dict_handler_metadata import TypedDictHandlerMetadata
from .typed_dict_health_status import TypedDictHealthStatus
from .typed_dict_input_state_fields import TypedDictInputStateFields
from .typed_dict_input_state_source_type import TypedDictInputStateSourceType
from .typed_dict_intent_context import TypedDictIntentContext
from .typed_dict_intent_metadata import TypedDictIntentMetadata

# Kubernetes resource TypedDict definitions
from .typed_dict_k8s_resources import (
    TypedDictK8sConfigMap,
    TypedDictK8sContainer,
    TypedDictK8sContainerPort,
    TypedDictK8sDeployment,
    TypedDictK8sDeploymentSpec,
    TypedDictK8sEnvVar,
    TypedDictK8sHttpGetProbe,
    TypedDictK8sLabelSelector,
    TypedDictK8sMetadata,
    TypedDictK8sPodSpec,
    TypedDictK8sPodTemplateSpec,
    TypedDictK8sProbe,
    TypedDictK8sResourceLimits,
    TypedDictK8sResourceRequirements,
    TypedDictK8sService,
    TypedDictK8sServicePort,
    TypedDictK8sServiceSpec,
)
from .typed_dict_legacy_dispatch_metrics import TypedDictLegacyDispatchMetrics
from .typed_dict_legacy_error import TypedDictLegacyError
from .typed_dict_legacy_health import TypedDictLegacyHealth
from .typed_dict_legacy_stats import TypedDictLegacyStats
from .typed_dict_lifecycle_event_fields import TypedDictLifecycleEventFields
from .typed_dict_lifecycle_event_metadata import TypedDictLifecycleEventMetadata
from .typed_dict_load_balancer_stats import TypedDictLoadBalancerStats
from .typed_dict_log_context import TypedDictLogContext
from .typed_dict_maintenance_summary import TypedDictMaintenanceSummary

# YAML and path resolution TypedDict definitions
from .typed_dict_mapping_result import MappingResultDict
from .typed_dict_metadata_dict import TypedDictMetadataDict
from .typed_dict_metadata_tool_analytics_report import (
    TypedDictMetadataToolAnalyticsReport,
)
from .typed_dict_metadata_tool_analytics_summary_data import (
    TypedDictMetadataToolAnalyticsSummaryData,
)
from .typed_dict_metrics import TypedDictMetrics
from .typed_dict_migration_conflict_base_dict import TypedDictMigrationConflictBaseDict
from .typed_dict_migration_duplicate_conflict_dict import (
    TypedDictMigrationDuplicateConflictDict,
)
from .typed_dict_migration_name_conflict_dict import TypedDictMigrationNameConflictDict
from .typed_dict_migration_report import (
    TypedDictMigrationReport,
    TypedDictMigrationReportSummary,
)
from .typed_dict_migration_step_dict import TypedDictMigrationStepDict

# Mixin-specific TypedDict definitions
from .typed_dict_mixin_types import (
    TypedDictCacheStats,
    TypedDictDiscoveryExtendedStats,
    TypedDictEventMetadata,
    TypedDictExecutorHealth,
    TypedDictFilterCriteria,
    TypedDictFSMContext,
    TypedDictIntrospectionData,
    TypedDictLazyCacheStats,
    TypedDictMetricEntry,
    TypedDictNodeExecutorHealth,
    TypedDictPerformanceProfile,
    TypedDictRedactedData,
    TypedDictReducerFSMContext,
    TypedDictRegistryStats,
    TypedDictSerializedResult,
    TypedDictServiceHealth,
    TypedDictToolExecutionResponse,
    TypedDictToolExecutionResult,
    TypedDictWorkflowStepConfig,
)
from .typed_dict_mixin_types import (
    TypedDictDiscoveryStats as TypedDictMixinDiscoveryStats,
)
from .typed_dict_model_class_info import TypedDictModelClassInfo
from .typed_dict_model_field_info import TypedDictModelFieldInfo
from .typed_dict_model_value_serialized import TypedDictModelValueSerialized
from .typed_dict_monitoring_dashboard import TypedDictMonitoringDashboard
from .typed_dict_monitoring_metrics import TypedDictMonitoringMetrics
from .typed_dict_node_capabilities import TypedDictNodeCapabilities
from .typed_dict_node_capabilities_summary import TypedDictNodeCapabilitiesSummary
from .typed_dict_node_configuration_summary import TypedDictNodeConfigurationSummary
from .typed_dict_node_connection_summary_type import TypedDictNodeConnectionSummaryType
from .typed_dict_node_core import TypedDictNodeCore
from .typed_dict_node_core_update_data import TypedDictNodeCoreUpdateData
from .typed_dict_node_execution_summary import TypedDictNodeExecutionSummary
from .typed_dict_node_feature_summary_type import TypedDictNodeFeatureSummaryType
from .typed_dict_node_info_summary_data import TypedDictNodeInfoSummaryData
from .typed_dict_node_introspection import TypedDictNodeIntrospection
from .typed_dict_node_metadata_summary import TypedDictNodeMetadataSummary
from .typed_dict_node_resource_constraint_kwargs import (
    TypedDictNodeResourceConstraintKwargs,
)
from .typed_dict_node_resource_summary_type import TypedDictNodeResourceSummaryType
from .typed_dict_node_rule_structure import TypedDictNodeRuleStructure
from .typed_dict_node_state import TypedDictNodeState
from .typed_dict_numeric_precision_summary import TypedDictNumericPrecisionSummary
from .typed_dict_operation_result import TypedDictOperationResult
from .typed_dict_operation_summary import TypedDictOperationSummary
from .typed_dict_operational_impact import TypedDictOperationalImpact
from .typed_dict_output_format_options_kwargs import TypedDictOutputFormatOptionsKwargs
from .typed_dict_output_format_options_serialized import (
    TypedDictOutputFormatOptionsSerialized,
)
from .typed_dict_path_resolution_context import TypedDictPathResolutionContext
from .typed_dict_performance_checkpoint_result import (
    TypedDictPerformanceCheckpointResult,
)
from .typed_dict_performance_data import TypedDictPerformanceData
from .typed_dict_performance_metric_data import TypedDictPerformanceMetricData
from .typed_dict_performance_metrics import TypedDictPerformanceMetrics
from .typed_dict_performance_metrics_report import TypedDictPerformanceMetricsReport
from .typed_dict_performance_update_data import TypedDictPerformanceUpdateData
from .typed_dict_policy_value_data import (
    TypedDictPolicyValueData,
    TypedDictPolicyValueInput,
)
from .typed_dict_property_metadata import TypedDictPropertyMetadata
from .typed_dict_published_event_entry import TypedDictPublishedEventEntry
from .typed_dict_quality_data import TypedDictQualityData
from .typed_dict_quality_update_data import TypedDictQualityUpdateData

# Schema reference types
from .typed_dict_ref_parts import TypedDictRefParts
from .typed_dict_resolution_context import TypedDictResolutionContext
from .typed_dict_resource_usage import TypedDictResourceUsage
from .typed_dict_result_factory_kwargs import TypedDictResultFactoryKwargs
from .typed_dict_routing_alternative import TypedDictRoutingAlternative
from .typed_dict_routing_info import TypedDictRoutingInfo

# New individual TypedDict classes extracted from typed_dict_structured_definitions.py
from .typed_dict_secondary_intent import TypedDictSecondaryIntent
from .typed_dict_security_context import TypedDictSecurityContext
from .typed_dict_security_policy_config import TypedDictSecurityPolicyConfig
from .typed_dict_sem_ver import TypedDictSemVer
from .typed_dict_serialized_model import TypedDictSerializedModel
from .typed_dict_service_info import TypedDictServiceInfo
from .typed_dict_signature_optional_params import TypedDictSignatureOptionalParams
from .typed_dict_ssl_context_options import TypedDictSSLContextOptions
from .typed_dict_stats_collection import TypedDictStatsCollection
from .typed_dict_status_migration_result import TypedDictStatusMigrationResult
from .typed_dict_structured_computation_summary import (
    TypedDictStructuredComputationSummary,
)
from .typed_dict_system_state import TypedDictSystemState
from .typed_dict_text_computation_summary import TypedDictTextComputationSummary
from .typed_dict_timestamp_data import TypedDictTimestampData
from .typed_dict_timestamp_update_data import TypedDictTimestampUpdateData
from .typed_dict_tool_breakdown import TypedDictToolBreakdown

# Tool manifest TypedDict definitions
from .typed_dict_tool_comprehensive_summary import TypedDictToolComprehensiveSummary
from .typed_dict_tool_details import TypedDictToolDetails
from .typed_dict_tool_performance_summary import TypedDictToolPerformanceSummary
from .typed_dict_tool_resource_summary import TypedDictToolResourceSummary
from .typed_dict_tool_testing_config_summary import TypedDictToolTestingConfigSummary
from .typed_dict_tool_testing_summary import TypedDictToolTestingSummary
from .typed_dict_tool_validation import TypedDictToolValidation
from .typed_dict_trace_info_data import TypedDictTraceInfoData
from .typed_dict_transition_config import TypedDictTransitionConfig
from .typed_dict_usage_metadata import TypedDictUsageMetadata
from .typed_dict_validation_base_serialized import TypedDictValidationBaseSerialized
from .typed_dict_validation_container_serialized import (
    TypedDictValidationContainerSerialized,
)
from .typed_dict_validation_error_serialized import TypedDictValidationErrorSerialized
from .typed_dict_validation_metadata_type import TypedDictValidationMetadataType
from .typed_dict_validation_result import TypedDictValidationResult
from .typed_dict_validation_value_serialized import TypedDictValidationValueSerialized
from .typed_dict_validator_info import TypedDictValidatorInfo
from .typed_dict_workflow_context import TypedDictWorkflowContext
from .typed_dict_workflow_outputs import TypedDictWorkflowOutputsDict
from .typed_dict_workflow_state import TypedDictWorkflowState
from .typed_dict_yaml_dump_kwargs import TypedDictYamlDumpKwargs
from .typed_dict_yaml_dump_options import TypedDictYamlDumpOptions

__all__ = [
    # Core types (no dependencies)
    "TypedDictBasicErrorContext",
    "ProtocolSchemaValue",
    "TypedDictCoreSummary",
    # Computation output summary TypedDicts
    "TypedDictBinaryComputationSummary",
    "TypedDictComputationOutputDataSummary",
    "TypedDictComputationOutputSummary",
    "TypedDictEventType",
    "TypedDictNumericPrecisionSummary",
    "TypedDictStructuredComputationSummary",
    "TypedDictTextComputationSummary",
    # Effect result type aliases
    "EffectResultType",
    "DbParamType",
    # Schema type aliases
    "SchemaDict",
    "StepOutputs",
    # Compute pipeline type aliases
    "PathResolvedValue",
    "PipelineData",
    "PipelineDataDict",
    "StepResultMapping",
    "TransformInputT",
    # JSON type aliases
    "JsonPrimitive",
    "JsonType",
    "PrimitiveValue",
    "PrimitiveContainer",
    "StrictJsonPrimitive",
    "StrictJsonType",
    "ToolParameterValue",
    # Serializable value types
    "SerializableValue",
    "SerializedDict",
    "TypedDictAdditionalFields",
    "TypedDictSerializedModel",
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
    # CLI model serialization TypedDict definitions
    "TypedDictCliActionSerialized",
    "TypedDictCliAdvancedParamsSerialized",
    "TypedDictCliCommandOptionSerialized",
    "TypedDictCliExecutionContextSerialized",
    "TypedDictCliExecutionCoreSerialized",
    "TypedDictCliExecutionMetadataSerialized",
    "TypedDictCliNodeExecutionInputSerialized",
    "TypedDictModelValueSerialized",
    "TypedDictOutputFormatOptionsSerialized",
    "TypedDictCollectionCreateKwargs",
    "TypedDictCollectionFromItemsKwargs",
    "TypedDictCoreAnalytics",
    "TypedDictDebugInfoData",
    "TypedDictDefaultOutputState",
    "TypedDictDeprecationSummary",
    "TypedDictDiscoveryStats",
    "TypedDictDocumentationSummaryFiltered",
    "TypedDictExecutionParams",
    "TypedDictFactoryKwargs",
    "TypedDictFieldValue",
    "TypedDictFunctionDocumentationSummaryType",
    "TypedDictFunctionMetadataSummary",
    "TypedDictFunctionRelationshipsSummary",
    "TypedDictGenericMetadataDict",
    "TypedDictHandlerMetadata",
    "TypedDictInputStateSourceType",
    "TypedDictMessageParams",
    "TypedDictMetadataParams",
    "TypedDictMigrationConflictBaseDict",
    "TypedDictMigrationDuplicateConflictDict",
    "TypedDictMigrationNameConflictDict",
    # Missing tool analysis types
    "TypedDictAlertData",
    "TypedDictAlertMetadata",
    "TypedDictErrorAnalysis",
    "TypedDictMonitoringDashboard",
    "TypedDictMonitoringMetrics",
    "TypedDictOperationalImpact",
    "TypedDictToolDetails",
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
    "TypedDictRoutingAlternative",
    "TypedDictRoutingInfo",
    "TypedDictSSLContextOptions",
    "TypedDictTimestampUpdateData",
    "TypedDictTraceInfoData",
    "TypedDictTransitionConfig",
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
    "TypedDictOperationSummary",
    "TypedDictWorkflowContext",
    "TypedDictWorkflowState",
    "TypedDictValidatorInfo",
    "TypedDictEventInfo",
    "TypedDictConsumedEventEntry",
    "TypedDictPublishedEventEntry",
    "TypedDictConditionalBranch",
    "TypedDictConnectionInfo",
    "TypedDictConvertedHealth",
    "TypedDictServiceInfo",
    "TypedDictDependencyInfo",
    "TypedDictCacheInfo",
    "TypedDictBatchProcessingInfo",
    "TypedDictSecurityContext",
    "TypedDictSecurityPolicyConfig",
    "TypedDictSignatureOptionalParams",
    "TypedDictAccessControlConfig",
    "TypedDictAuditChange",
    "TypedDictAuditInfo",
    "TypedDictFeatureFlags",
    "TypedDictStatsCollection",
    "TypedDictSystemState",
    "TypedDictLegacyDispatchMetrics",
    "TypedDictLegacyStats",
    "TypedDictLegacyHealth",
    "TypedDictLegacyError",
    "TypedDictLogContext",
    "TypedDictMigrationStepDict",
    "TypedDictNodeCoreUpdateData",
    "TypedDictPerformanceData",
    "TypedDictPerformanceUpdateData",
    "TypedDictQualityUpdateData",
    "TypedDictStatusMigrationResult",
    "TypedDictTimestampData",
    # Schema reference types
    "TypedDictRefParts",
    "TypedDictResolutionContext",
    # Converter functions
    "convert_stats_to_typed_dict",
    "convert_health_to_typed_dict",
    "convert_error_details_to_typed_dict",
    # Mixin-specific TypedDict definitions
    "TypedDictCacheStats",
    "TypedDictDiscoveryExtendedStats",
    "TypedDictMixinDiscoveryStats",
    "TypedDictEventMetadata",
    "TypedDictExecutorHealth",
    "TypedDictFilterCriteria",
    "TypedDictFSMContext",
    "TypedDictIntrospectionData",
    "TypedDictLazyCacheStats",
    "TypedDictMetricEntry",
    "TypedDictNodeExecutorHealth",
    "TypedDictPerformanceProfile",
    "TypedDictRedactedData",
    "TypedDictReducerFSMContext",
    "TypedDictRegistryStats",
    "TypedDictSerializedResult",
    "TypedDictServiceHealth",
    "TypedDictToolExecutionResponse",
    "TypedDictToolExecutionResult",
    "TypedDictWorkflowStepConfig",
    # Tool manifest TypedDict definitions
    "TypedDictToolComprehensiveSummary",
    "TypedDictToolPerformanceSummary",
    "TypedDictToolResourceSummary",
    "TypedDictToolTestingConfigSummary",
    "TypedDictToolTestingSummary",
    # Contract validation TypedDict definitions
    "TypedDictContractData",
    "TypedDictModelClassInfo",
    "TypedDictModelFieldInfo",
    # Node infrastructure TypedDict definitions
    "TypedDictComprehensiveHealth",
    "TypedDictLifecycleEventFields",
    "TypedDictLifecycleEventMetadata",
    "TypedDictNodeCapabilities",
    "TypedDictNodeIntrospection",
    "TypedDictNodeState",
    # Node status summary TypedDict definitions
    "TypedDictActiveSummary",
    "TypedDictErrorSummary",
    "TypedDictMaintenanceSummary",
    # YAML and path resolution types
    "MappingResultDict",
    "TypedDictPathResolutionContext",
    "TypedDictYamlDumpKwargs",
    "TypedDictYamlDumpOptions",
    # Metadata tool collection types
    "TypedDictCollectionMetadata",
    "TypedDictCollectionValidation",
    "TypedDictMetadataToolAnalyticsReport",
    "TypedDictMetadataToolAnalyticsSummaryData",
    "TypedDictPerformanceMetricsReport",
    "TypedDictToolBreakdown",
    "TypedDictToolValidation",
    # Action validation TypedDict definitions
    "TypedDictActionValidationContext",
    "TypedDictActionValidationStatistics",
    # Validation serialization TypedDict definitions
    "TypedDictMigrationReport",
    "TypedDictMigrationReportSummary",
    "TypedDictValidationBaseSerialized",
    "TypedDictValidationContainerSerialized",
    "TypedDictValidationErrorSerialized",
    "TypedDictValidationValueSerialized",
    # Custom fields, policy value, and model-specific TypedDict definitions
    "CustomFieldsDict",
    "TypedDictCustomFieldsDict",
    "TypedDictEventEnvelopeDict",
    "TypedDictLoadBalancerStats",
    "TypedDictPerformanceCheckpointResult",
    "TypedDictPolicyValueData",
    "TypedDictPolicyValueInput",
    "TypedDictWorkflowOutputsDict",
    # Intent classification TypedDict definitions
    "TypedDictConversationMessage",
    "TypedDictIntentContext",
    "TypedDictIntentMetadata",
    "TypedDictSecondaryIntent",
    # Kubernetes resource TypedDict definitions
    "TypedDictK8sConfigMap",
    "TypedDictK8sContainer",
    "TypedDictK8sContainerPort",
    "TypedDictK8sDeployment",
    "TypedDictK8sDeploymentSpec",
    "TypedDictK8sEnvVar",
    "TypedDictK8sHttpGetProbe",
    "TypedDictK8sLabelSelector",
    "TypedDictK8sMetadata",
    "TypedDictK8sPodSpec",
    "TypedDictK8sPodTemplateSpec",
    "TypedDictK8sProbe",
    "TypedDictK8sResourceLimits",
    "TypedDictK8sResourceRequirements",
    "TypedDictK8sService",
    "TypedDictK8sServicePort",
    "TypedDictK8sServiceSpec",
]


# =============================================================================
# Lazy loading: Avoid circular imports during module initialization.
# This defers imports that would cause circular dependency chains:
#   error_codes -> types.__init__ -> constraints -> models -> error_codes
# =============================================================================
def __getattr__(name: str) -> object:
    """
    Lazy import for constraints module to avoid circular imports.

    All constraint imports are lazy-loaded to prevent circular dependency:
    error_codes -> types.__init__ -> constraints -> models -> error_codes
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
        from omnibase_core.types import type_constraints as constraints

        attr = getattr(constraints, name)
        globals()[name] = attr
        return attr

    msg = f"module {__name__!r} has no attribute {name!r}"
    # error-ok: AttributeError is standard Python pattern for __getattr__
    raise AttributeError(msg)
