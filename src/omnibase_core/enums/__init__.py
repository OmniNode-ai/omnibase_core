"""
Shared enums for ONEX ecosystem.

Domain-grouped enums used across multiple ONEX packages (omnibase_core, omnibase_spi, etc.)
organized by functional domains for better maintainability.
"""

# Architecture and system enums
from .enum_architecture import EnumArchitecture

# Artifact-related enums
from .enum_artifact_type import EnumArtifactType

# Audit and governance enums
from .enum_audit_action import EnumAuditAction

# Infrastructure-related enums
from .enum_auth_type import EnumAuthType
from .enum_authentication_method import EnumAuthenticationMethod
from .enum_backoff_strategy import EnumBackoffStrategy
from .enum_business_logic_pattern import EnumBusinessLogicPattern

# Case mode enums (contract-driven NodeCompute v1.0)
from .enum_case_mode import EnumCaseMode

# Category filter enums
from .enum_category_filter import EnumCategoryFilter

# Circuit breaker state enum (standalone for cross-repo standardization)
from .enum_circuit_breaker_state import EnumCircuitBreakerState

# Error code enums
from .enum_cli_exit_code import EnumCLIExitCode

# Computation and processing enums
from .enum_computation_type import EnumComputationType

# Capability enums (handler capabilities)
from .enum_compute_capability import EnumComputeCapability

# Compute step type enums (contract-driven NodeCompute v1.0)
from .enum_compute_step_type import EnumComputeStepType
from .enum_contract_compliance import EnumContractCompliance
from .enum_coordination_mode import EnumCoordinationMode
from .enum_core_error_code import (
    CORE_ERROR_CODE_TO_EXIT_CODE,
    EnumCoreErrorCode,
    get_core_error_description,
    get_exit_code_for_core_error,
)

# Security-related enums
from .enum_data_classification import EnumDataClassification

# Detection and security enums
from .enum_detection_type import EnumDetectionType

# Value type enums
from .enum_discriminated_value_type import EnumDiscriminatedValueType

# Effect-related enums (from nodes)
from .enum_effect_capability import EnumEffectCapability
from .enum_effect_handler_type import EnumEffectHandlerType
from .enum_effect_types import (
    EnumEffectType,
    EnumTransactionState,
)

# Validation-related enums
from .enum_environment_validation_rule_type import EnumEnvironmentValidationRuleType

# Execution-related enums
from .enum_execution_mode import EnumExecutionMode
from .enum_execution_trigger import EnumExecutionTrigger

# Function-related enums
from .enum_function_language import EnumFunctionLanguage

# GitHub Actions enums
from .enum_github_action_event import EnumGithubActionEvent
from .enum_github_runner_os import EnumGithubRunnerOs

# Group and organization enums
from .enum_group_status import EnumGroupStatus

# Handler type enums (runtime handler registry)
from .enum_handler_type import EnumHandlerType

# Header and query parameter transformation enums
from .enum_header_transformation_type import EnumHeaderTransformationType

# Health and status enums
from .enum_health_check_type import EnumHealthCheckType
from .enum_health_detail_type import EnumHealthDetailType
from .enum_health_status_type import EnumHealthStatusType

# Hub and coordination enums
from .enum_hub_capability import EnumHubCapability

# File pattern enums
from .enum_ignore_pattern_source import EnumIgnorePatternSource, EnumTraversalMode

# Import status enum
from .enum_import_status import EnumImportStatus

# Language and localization enums
from .enum_language_code import EnumLanguageCode
from .enum_log_format import EnumLogFormat

# Log level enum
from .enum_log_level import EnumLogLevel

# Communication enums
from .enum_mapping_type import EnumMappingType
from .enum_message_type import EnumMessageType

# Metadata-related enums
from .enum_metadata import (
    EnumLifecycle,
    EnumMetaType,
    EnumNodeMetadataField,
    EnumProtocolVersion,
    EnumRuntimeLanguage,
)

# Metadata tool enums
from .enum_metadata_tool_complexity import EnumMetadataToolComplexity
from .enum_metadata_tool_status import EnumMetadataToolStatus
from .enum_metadata_tool_type import EnumMetadataToolType

# Namespace-related enums
from .enum_namespace_strategy import EnumNamespaceStrategy
from .enum_node_architecture_type import EnumNodeArchitectureType
from .enum_node_health_status import EnumNodeHealthStatus

# Node-related enums
from .enum_node_kind import EnumNodeKind
from .enum_node_requirement import EnumNodeRequirement
from .enum_node_status import EnumNodeStatus
from .enum_node_type import EnumNodeType
from .enum_notification_method import EnumNotificationMethod
from .enum_numeric_value_type import EnumNumericValueType
from .enum_onex_error_code import EnumOnexErrorCode

# Response and reply enums
from .enum_onex_reply_status import EnumOnexReplyStatus
from .enum_operation_status import EnumOperationStatus

# Orchestrator-related enums (from nodes)
from .enum_orchestrator_capability import EnumOrchestratorCapability
from .enum_orchestrator_types import (
    EnumActionType,
    EnumBranchCondition,
    EnumWorkflowState,
)

# Parameter and return type enums
from .enum_parameter_type import EnumParameterType
from .enum_query_parameter_transformation_type import (
    EnumQueryParameterTransformationType,
)

# Reducer-related enums (from nodes)
from .enum_reducer_capability import EnumReducerCapability
from .enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)

# Regex flag enums (contract-driven NodeCompute v1.0)
from .enum_regex_flag import EnumRegexFlag
from .enum_registry_error_code import EnumRegistryErrorCode

# Registry-related enums
from .enum_registry_health_status import EnumRegistryHealthStatus
from .enum_registry_type import EnumRegistryType

# Resource-related enums
from .enum_resource_unit import EnumResourceUnit
from .enum_response_header_transformation_type import (
    EnumResponseHeaderTransformationType,
)
from .enum_return_type import EnumReturnType

# Security-related enums
from .enum_security_profile import EnumSecurityProfile
from .enum_security_risk_level import EnumSecurityRiskLevel

# Service-related enums
from .enum_service_health_status import EnumServiceHealthStatus
from .enum_service_mode import EnumServiceMode
from .enum_service_status import EnumServiceStatus

# Service architecture enums
from .enum_service_tier import EnumServiceTier
from .enum_service_type_category import EnumServiceTypeCategory
from .enum_state_update_operation import EnumStateUpdateOperation

# Tool-related enums
from .enum_tool_category import EnumToolCategory

# Tool lifecycle enums
from .enum_tool_status import EnumToolStatus
from .enum_tool_type import EnumToolType

# Transformation types (contract-driven NodeCompute v1.0)
from .enum_transformation_type import EnumTransformationType

# State management enums
from .enum_transition_type import EnumTransitionType

# Tree sync enums
from .enum_tree_sync_status import EnumTreeSyncStatus

# Trim mode enums (contract-driven NodeCompute v1.0)
from .enum_trim_mode import EnumTrimMode

# Unicode form enums (contract-driven NodeCompute v1.0)
from .enum_unicode_form import EnumUnicodeForm

# URI-related enums
from .enum_uri_type import EnumUriType
from .enum_validation import EnumErrorSeverity, EnumValidationLevel, EnumValidationMode
from .enum_validation_rule_type import EnumValidationRuleType
from .enum_value_type import EnumValueType

# Version and contract enums
from .enum_version_status import EnumVersionStatus

# Workflow-related enums
from .enum_workflow_coordination import EnumFailureRecoveryStrategy
from .enum_workflow_dependency_type import EnumWorkflowDependencyType

# NOTE: ModelEnumStatusMigrator is defined in models.core.model_status_migrator
# It was moved from enums to eliminate circular imports
# Users should import it directly: from omnibase_core.models.core.model_status_migrator import ModelEnumStatusMigrator

# NOTE: The following enums are referenced but their module files don't exist:
# - enum_tool_criticality.py (referenced by model_missing_tool.py)
# - enum_tool_health_status.py (referenced by model_tool_health.py)
# - enum_tool_missing_reason.py (referenced by model_missing_tool.py)
# - enum_tree_sync_status.py
# - enum_registry_type.py
# These need to be created or their references need to be updated.


__all__ = [
    # Error code domain
    "EnumCLIExitCode",
    "EnumOnexErrorCode",
    "EnumCoreErrorCode",
    "EnumRegistryErrorCode",
    "CORE_ERROR_CODE_TO_EXIT_CODE",
    "get_core_error_description",
    "get_exit_code_for_core_error",
    # Artifact domain
    "EnumArtifactType",
    # Category filter domain
    "EnumCategoryFilter",
    # Security domain
    "EnumDataClassification",
    "EnumSecurityProfile",
    "EnumAuthenticationMethod",
    "EnumSecurityRiskLevel",
    # Validation domain
    "EnumEnvironmentValidationRuleType",
    "EnumErrorSeverity",
    "EnumValidationRuleType",
    # Circuit breaker domain (standalone for cross-repo standardization)
    "EnumCircuitBreakerState",
    # Effect domain (from nodes)
    "EnumEffectHandlerType",
    "EnumEffectType",
    "EnumTransactionState",
    # Execution domain
    "EnumExecutionMode",
    "EnumExecutionTrigger",
    # Log level domain
    "EnumLogLevel",
    # Health and status domain
    "EnumHealthCheckType",
    "EnumHealthDetailType",
    "EnumHealthStatusType",
    "EnumNodeHealthStatus",
    "EnumNodeStatus",
    # Node domain
    "EnumNodeArchitectureType",
    "EnumNodeKind",
    "EnumNodeType",
    "EnumOperationStatus",
    "EnumValidationLevel",
    "EnumValidationMode",
    "EnumValueType",
    "EnumNumericValueType",
    # Orchestrator domain (from nodes)
    "EnumActionType",
    "EnumBranchCondition",
    "EnumWorkflowState",
    # Reducer domain (from nodes)
    "EnumConflictResolution",
    "EnumReductionType",
    "EnumStreamingMode",
    # Parameter and return type domain
    "EnumParameterType",
    "EnumReturnType",
    # File pattern domain
    "EnumIgnorePatternSource",
    "EnumTraversalMode",
    # Import status domain
    "EnumImportStatus",
    # Metadata domain
    "EnumLifecycle",
    "EnumMetaType",
    "EnumNodeMetadataField",
    "EnumProtocolVersion",
    "EnumRuntimeLanguage",
    "EnumMetadataToolComplexity",
    "EnumMetadataToolStatus",
    "EnumMetadataToolType",
    # Namespace domain
    "EnumNamespaceStrategy",
    # Resource domain
    "EnumResourceUnit",
    # URI domain
    "EnumUriType",
    # Workflow domain
    "EnumFailureRecoveryStrategy",
    "EnumWorkflowDependencyType",
    # Infrastructure domain
    "EnumAuthType",
    "EnumBackoffStrategy",
    "EnumNotificationMethod",
    # Audit and governance domain
    "EnumAuditAction",
    # Architecture and system domain
    "EnumArchitecture",
    "EnumLogFormat",
    # Communication domain
    "EnumMappingType",
    "EnumMessageType",
    # Group and organization domain
    "EnumGroupStatus",
    # Handler type domain (runtime handler registry)
    "EnumHandlerType",
    # Version and contract domain
    "EnumVersionStatus",
    "EnumContractCompliance",
    # State management domain
    "EnumTransitionType",
    "EnumStateUpdateOperation",
    # Tree sync domain
    "EnumTreeSyncStatus",
    # Response and reply domain
    "EnumOnexReplyStatus",
    # Capability enums (handler capabilities)
    "EnumComputeCapability",
    "EnumEffectCapability",
    "EnumNodeRequirement",
    "EnumOrchestratorCapability",
    "EnumReducerCapability",
    # Computation and processing domain
    "EnumComputationType",
    # Contract-driven NodeCompute v1.0 domain
    "EnumCaseMode",
    "EnumComputeStepType",
    "EnumRegexFlag",
    "EnumTransformationType",
    "EnumTrimMode",
    "EnumUnicodeForm",
    # Tool lifecycle domain
    "EnumToolStatus",
    "EnumBusinessLogicPattern",
    # Service architecture domain
    "EnumServiceTier",
    # Hub and coordination domain
    "EnumHubCapability",
    "EnumCoordinationMode",
    # Language and localization domain
    "EnumLanguageCode",
    # Detection and security domain
    "EnumDetectionType",
    # Function-related domain
    "EnumFunctionLanguage",
    # Registry-related domain
    "EnumRegistryHealthStatus",
    "EnumRegistryType",
    # Service-related domain
    "EnumServiceHealthStatus",
    "EnumServiceMode",
    "EnumServiceStatus",
    "EnumServiceTypeCategory",
    # Tool-related domain
    "EnumToolCategory",
    "EnumToolType",
    # GitHub Actions domain
    "EnumGithubActionEvent",
    "EnumGithubRunnerOs",
    # Header and query parameter transformation domain
    "EnumHeaderTransformationType",
    "EnumQueryParameterTransformationType",
    "EnumResponseHeaderTransformationType",
    # NOTE: Removed from __all__ due to missing module files or circular imports:
    # - "EnumRegistryType" (module doesn't exist)
    # - "ModelServiceModeEnum" (replaced with correct "EnumServiceMode")
    # - "ModelEnumStatusMigrator" (moved to models.core - import from model_status_migrator directly)
    # - "EnumToolCriticality" (module doesn't exist)
    # - "EnumToolHealthStatus" (module doesn't exist)
    # - "EnumToolMissingReason" (module doesn't exist)
    # - "EnumTreeSyncStatus" (module doesn't exist)
]
