"""
Omnibase Core - Enumerations

Enumeration definitions for ONEX architecture with strong typing support.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.errors import OnexError

from .enum_action_category import EnumActionCategory
from .enum_artifact_type import EnumArtifactType
from .enum_auth_type import EnumAuthType

# Unified Status Hierarchy (v2)
from .enum_base_status import EnumBaseStatus
from .enum_category import EnumCategory
from .enum_category_filter import EnumCategoryFilter
from .enum_cell_type import EnumCellType
from .enum_cli_action import EnumCliAction
from .enum_cli_context_value_type import EnumCliContextValueType
from .enum_cli_input_value_type import EnumCliInputValueType
from .enum_cli_option_value_type import EnumCliOptionValueType
from .enum_cli_status import EnumCliStatus
from .enum_cli_value_type import EnumCliValueType
from .enum_color_scheme import EnumColorScheme
from .enum_compensation_strategy import EnumCompensationStrategy
from .enum_complexity import EnumComplexity
from .enum_complexity_level import EnumComplexityLevel
from .enum_conceptual_complexity import EnumConceptualComplexity
from .enum_config_category import EnumConfigCategory
from .enum_config_type import EnumConfigType
from .enum_connection_state import EnumConnectionState
from .enum_connection_type import EnumConnectionType
from .enum_context_type import EnumContextType
from .enum_contract_data_type import EnumContractDataType
from .enum_core_error_code import EnumCoreErrorCode
from .enum_data_classification import EnumDataClassification
from .enum_data_format import EnumDataFormat
from .enum_data_type import EnumDataType
from .enum_debug_level import EnumDebugLevel
from .enum_difficulty_level import EnumDifficultyLevel
from .enum_document_freshness_errors import EnumDocumentFreshnessErrorCodes
from .enum_edit_mode import EnumEditMode
from .enum_effect_parameter_type import EnumEffectParameterType
from .enum_entity_type import EnumEntityType
from .enum_environment import EnumEnvironment
from .enum_error_value_type import EnumErrorValueType
from .enum_event_type import EnumEventType
from .enum_example_category import EnumExampleCategory
from .enum_execution_mode import EnumExecutionMode
from .enum_execution_order import EnumExecutionOrder
from .enum_execution_phase import EnumExecutionPhase
from .enum_execution_status_v2 import EnumExecutionStatusV2

# Legacy enum removed - use EnumExecutionStatusV2 instead
from .enum_fallback_strategy_type import EnumFallbackStrategyType
from .enum_field_type import EnumFieldType
from .enum_filter_type import EnumFilterType
from .enum_flexible_value_type import EnumFlexibleValueType
from .enum_function_lifecycle_status import EnumFunctionLifecycleStatus
from .enum_function_status import EnumFunctionStatus
from .enum_function_type import EnumFunctionType
from .enum_general_status import EnumGeneralStatus
from .enum_instance_type import EnumInstanceType
from .enum_io_type import EnumIOType
from .enum_item_type import EnumItemType
from .enum_log_level import EnumLogLevel
from .enum_memory_usage import EnumMemoryUsage
from .enum_metadata_node_complexity import EnumMetadataNodeComplexity
from .enum_metadata_node_status import EnumMetadataNodeStatus
from .enum_metadata_node_type import EnumMetadataNodeType
from .enum_metric_data_type import EnumMetricDataType
from .enum_metric_type import EnumMetricType
from .enum_metrics_category import EnumMetricsCategory
from .enum_migration_conflict_type import EnumMigrationConflictType
from .enum_namespace_strategy import EnumNamespaceStrategy
from .enum_node_architecture_type import EnumNodeArchitectureType
from .enum_node_capability import EnumNodeCapability
from .enum_node_health_status import EnumNodeHealthStatus
from .enum_node_type import EnumNodeType
from .enum_node_union_type import EnumNodeUnionType
from .enum_numeric_type import EnumNumericType
from .enum_onex_status import EnumOnexStatus
from .enum_operation_parameter_type import EnumOperationParameterType
from .enum_operation_type import EnumOperationType
from .enum_operational_complexity import EnumOperationalComplexity
from .enum_output_format import EnumOutputFormat
from .enum_output_mode import EnumOutputMode
from .enum_output_type import EnumOutputType
from .enum_parameter_type import EnumParameterType
from .enum_performance_impact import EnumPerformanceImpact
from .enum_property_type import EnumPropertyType
from .enum_protocol_type import EnumProtocolType
from .enum_regex_flag_type import EnumRegexFlagType
from .enum_registry_status import EnumRegistryStatus
from .enum_result_category import EnumResultCategory
from .enum_result_type import EnumResultType
from .enum_retry_backoff_strategy import EnumRetryBackoffStrategy
from .enum_return_type import EnumReturnType
from .enum_runtime_category import EnumRuntimeCategory
from .enum_scenario_status import EnumScenarioStatus
from .enum_scenario_status_v2 import EnumScenarioStatusV2
from .enum_security_level import EnumSecurityLevel
from .enum_severity_level import EnumSeverityLevel
from .enum_status import EnumStatus
from .enum_status_message import EnumStatusMessage

# Lazy import to avoid circular dependency with error_codes
# from .enum_status_migration import (
#     EnumStatusMigrationValidator,
#     EnumStatusMigrator,
# )
from .enum_stop_reason import EnumStopReason


def __getattr__(name: str) -> type:
    """Lazy import for enum_status_migration to avoid circular dependency."""
    if name in ("EnumStatusMigrationValidator", "EnumStatusMigrator"):
        from .enum_status_migration import (
            EnumStatusMigrationValidator,
            EnumStatusMigrator,
        )

        return (
            EnumStatusMigrationValidator
            if name == "EnumStatusMigrationValidator"
            else EnumStatusMigrator
        )
    # Lazy import to avoid circular dependency
    from omnibase_core.errors import OnexError

    msg = f"module {__name__!r} has no attribute {name!r}"
    raise OnexError(msg, EnumCoreErrorCode.VALIDATION_ERROR)


from .enum_table_alignment import EnumTableAlignment
from .enum_time_period import EnumTimePeriod
from .enum_time_unit import EnumTimeUnit
from .enum_trend_type import EnumTrendType
from .enum_type_name import EnumTypeName
from .enum_uri_type import EnumUriType
from .enum_validation_level import EnumValidationLevel
from .enum_validation_rules_input_type import EnumValidationRulesInputType
from .enum_validation_severity import EnumValidationSeverity
from .enum_version_union_type import EnumVersionUnionType
from .enum_workflow_coordination import (
    EnumAssignmentStatus,
    EnumExecutionPattern,
    EnumFailureRecoveryStrategy,
    EnumWorkflowStatus,
)
from .enum_workflow_dependency_type import EnumWorkflowDependencyType
from .enum_workflow_parameter_type import EnumWorkflowParameterType
from .enum_workflow_type import EnumWorkflowType
from .enum_yaml_option_type import EnumYamlOptionType
from .enum_yaml_value_type import EnumYamlValueType

__all__ = [
    "EnumActionCategory",
    "EnumArtifactType",
    "EnumAssignmentStatus",
    "EnumAuthType",
    "EnumBaseStatus",
    "EnumCategory",
    "EnumCategoryFilter",
    "EnumCellType",
    "EnumCliAction",
    "EnumCliContextValueType",
    "EnumCliInputValueType",
    "EnumCliOptionValueType",
    "EnumCliStatus",
    "EnumCliValueType",
    "EnumColorScheme",
    "EnumCompensationStrategy",
    "EnumComplexity",
    "EnumComplexityLevel",
    "EnumConceptualComplexity",
    "EnumConfigCategory",
    "EnumConfigType",
    "EnumConnectionState",
    "EnumConnectionType",
    "EnumContextType",
    "EnumContractDataType",
    "EnumCoreErrorCode",
    "EnumDataClassification",
    "EnumDataFormat",
    "EnumDataType",
    "EnumDebugLevel",
    "EnumDifficultyLevel",
    "EnumDocumentFreshnessErrorCodes",
    "EnumEditMode",
    "EnumEffectParameterType",
    "EnumEntityType",
    "EnumEnvironment",
    "EnumErrorValueType",
    "EnumEventType",
    "EnumExampleCategory",
    "EnumExecutionMode",
    "EnumExecutionOrder",
    "EnumExecutionPattern",
    "EnumExecutionPhase",
    # "EnumExecutionStatus",  # Legacy - use EnumExecutionStatusV2
    "EnumExecutionStatusV2",
    "EnumFailureRecoveryStrategy",
    "EnumFallbackStrategyType",
    "EnumFieldType",
    "EnumFilterType",
    "EnumFlexibleValueType",
    "EnumFunctionLifecycleStatus",
    "EnumFunctionStatus",
    "EnumFunctionType",
    "EnumGeneralStatus",
    "EnumIOType",
    "EnumInstanceType",
    "EnumItemType",
    "EnumLogLevel",
    "EnumMemoryUsage",
    "EnumMetadataNodeComplexity",
    "EnumMetadataNodeStatus",
    "EnumMetadataNodeType",
    "EnumMetricDataType",
    "EnumMetricType",
    "EnumMetricsCategory",
    "EnumMigrationConflictType",
    "EnumNamespaceStrategy",
    "EnumNodeArchitectureType",
    "EnumNodeCapability",
    "EnumNodeHealthStatus",
    "EnumNodeType",
    "EnumNodeUnionType",
    "EnumNumericType",
    "EnumOnexStatus",
    "EnumOperationParameterType",
    "EnumOperationType",
    "EnumOperationalComplexity",
    "EnumOutputFormat",
    "EnumOutputMode",
    "EnumOutputType",
    "EnumParameterType",
    "EnumPerformanceImpact",
    "EnumPropertyType",
    "EnumProtocolType",
    "EnumRegexFlagType",
    "EnumRegistryStatus",
    "EnumResultCategory",
    "EnumResultType",
    "EnumRetryBackoffStrategy",
    "EnumReturnType",
    "EnumRuntimeCategory",
    "EnumScenarioStatus",
    "EnumScenarioStatusV2",
    "EnumSecurityLevel",
    "EnumSeverityLevel",
    "EnumStatus",
    "EnumStatusMessage",
    "EnumStatusMigrationValidator",
    "EnumStatusMigrator",
    "EnumStopReason",
    "EnumTableAlignment",
    "EnumTimePeriod",
    "EnumTimeUnit",
    "EnumTrendType",
    "EnumTypeName",
    "EnumUriType",
    "EnumValidationLevel",
    "EnumValidationRulesInputType",
    "EnumValidationSeverity",
    "EnumVersionUnionType",
    "EnumWorkflowDependencyType",
    "EnumWorkflowParameterType",
    "EnumWorkflowStatus",
    "EnumWorkflowType",
    "EnumYamlOptionType",
    "EnumYamlValueType",
]
