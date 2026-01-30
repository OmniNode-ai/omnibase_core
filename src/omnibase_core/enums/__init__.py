"""Shared enums for ONEX ecosystem.

Domain-grouped enums used across multiple ONEX packages (omnibase_core, omnibase_spi, etc.)
organized by functional domains for better maintainability.
"""

# Action status enum (OMN-1309)
from .enum_action_status import EnumActionStatus

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

# Binding function enums (Operation Bindings DSL - OMN-1410)
from .enum_binding_function import EnumBindingFunction
from .enum_business_logic_pattern import EnumBusinessLogicPattern

# Case mode enums (contract-driven NodeCompute v1.0)
from .enum_case_mode import EnumCaseMode

# Category filter enums
from .enum_category_filter import EnumCategoryFilter

# Change type enums (OMN-1196)
from .enum_change_type import EnumChangeType

# Checkpoint-related enums
from .enum_checkpoint_type import EnumCheckpointType

# Circuit breaker state enum (standalone for cross-repo standardization)
from .enum_circuit_breaker_state import EnumCircuitBreakerState

# Error code enums
from .enum_cli_exit_code import EnumCLIExitCode

# Comparison type enum (OMN-1207)
from .enum_comparison_type import EnumComparisonType

# Computation and processing enums
from .enum_computation_type import EnumComputationType

# Capability enums (handler capabilities)
from .enum_compute_capability import EnumComputeCapability

# Compute step type enums (contract-driven NodeCompute v1.0)
from .enum_compute_step_type import EnumComputeStepType
from .enum_contract_compliance import EnumContractCompliance

# Contract diff change type enum (semantic contract diffing)
from .enum_contract_diff_change_type import EnumContractDiffChangeType
from .enum_coordination_mode import EnumCoordinationMode
from .enum_core_error_code import (
    CORE_ERROR_CODE_TO_EXIT_CODE,
    EnumCoreErrorCode,
    get_core_error_description,
    get_exit_code_for_core_error,
)

# Customer tier enum (OMN-1395 demo)
from .enum_customer_tier import EnumCustomerTier

# Dashboard enums (OMN-1284)
from .enum_dashboard_status import EnumDashboardStatus
from .enum_dashboard_theme import EnumDashboardTheme

# Security-related enums
from .enum_data_classification import EnumDataClassification

# Decision type enums (OMN-1235)
from .enum_decision_type import EnumDecisionType

# Demo enums (OMN-1397)
from .enum_demo_recommendation import EnumDemoRecommendation
from .enum_demo_verdict import EnumDemoVerdict

# Detection and security enums
from .enum_detection_type import EnumDetectionType

# Directive type enum (runtime-internal)
from .enum_directive_type import EnumDirectiveType

# Dispatch status enum
from .enum_dispatch_status import EnumDispatchStatus

# Effect-related enums (from nodes)
from .enum_effect_capability import EnumEffectCapability

# Effect classification enums (OMN-1147)
from .enum_effect_category import EnumEffectCategory
from .enum_effect_handler_type import EnumEffectHandlerType
from .enum_effect_policy_level import EnumEffectPolicyLevel
from .enum_effect_types import EnumEffectType, EnumTransactionState

# Validation-related enums
from .enum_environment_validation_rule_type import EnumEnvironmentValidationRuleType

# Event priority enum (OMN-1308)
from .enum_event_priority import EnumEventPriority

# Event sink type enum (OMN-1151)
from .enum_event_sink_type import EnumEventSinkType

# Execution-related enums
from .enum_execution_mode import EnumExecutionMode
from .enum_execution_shape import EnumExecutionShape, EnumMessageCategory

# Execution status enum (canonical for execution lifecycle - OMN-1310)
from .enum_execution_status import EnumExecutionStatus
from .enum_execution_trigger import EnumExecutionTrigger

# Failure type enums (OMN-1236)
from .enum_failure_type import EnumFailureType

# Function-related enums
from .enum_function_language import EnumFunctionLanguage

# GitHub Actions enums
from .enum_github_action_event import EnumGithubActionEvent
from .enum_github_runner_os import EnumGithubRunnerOs

# Group and organization enums
from .enum_group_status import EnumGroupStatus
from .enum_handler_capability import EnumHandlerCapability

# Handler command type enums (OMN-1085)
from .enum_handler_command_type import EnumHandlerCommandType

# Handler execution phase enums (OMN-1108)
from .enum_handler_execution_phase import EnumHandlerExecutionPhase

# Handler role enums (OMN-1086)
from .enum_handler_role import EnumHandlerRole

# Handler routing strategy enums (OMN-1295)
from .enum_handler_routing_strategy import EnumHandlerRoutingStrategy

# Handler type enums (runtime handler registry)
from .enum_handler_type import EnumHandlerType
from .enum_handler_type_category import EnumHandlerTypeCategory

# Hash algorithm enum (handler packaging OMN-1119)
from .enum_hash_algorithm import EnumHashAlgorithm

# Header and query parameter transformation enums
from .enum_header_transformation_type import EnumHeaderTransformationType

# Health and status enums
from .enum_health_check_type import EnumHealthCheckType
from .enum_health_detail_type import EnumHealthDetailType
from .enum_health_status import EnumHealthStatus

# Hub and coordination enums
from .enum_hub_capability import EnumHubCapability

# File pattern enums
from .enum_ignore_pattern_source import EnumIgnorePatternSource, EnumTraversalMode

# Impact severity enum (business impact scale - OMN-1311)
from .enum_impact_severity import EnumImpactSeverity

# Import status enum
from .enum_import_status import EnumImportStatus

# Injection scope enum (DI container scoping)
from .enum_injection_scope import EnumInjectionScope

# Invariant-related enums (OMN-1192, OMN-1206)
from .enum_invariant_report_status import EnumInvariantReportStatus
from .enum_invariant_type import EnumInvariantType

# Label violation type enum (OMN-1367 - observability cardinality)
from .enum_label_violation_type import EnumLabelViolationType

# Language and localization enums
from .enum_language_code import EnumLanguageCode
from .enum_likelihood import EnumLikelihood
from .enum_log_format import EnumLogFormat

# Log level enum
from .enum_log_level import EnumLogLevel

# Communication enums
from .enum_mapping_type import EnumMappingType

# MCP (Model Context Protocol) enums (OMN-1286)
from .enum_mcp_parameter_type import EnumMCPParameterType
from .enum_mcp_status import EnumMCPStatus
from .enum_mcp_tool_type import EnumMCPToolType

# Merge-related enums (OMN-1127)
from .enum_merge_conflict_type import EnumMergeConflictType
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

# Metrics policy enums (OMN-1367 - observability cardinality)
from .enum_metrics_policy_violation_action import EnumMetricsPolicyViolationAction

# Namespace-related enums
from .enum_namespace_strategy import EnumNamespaceStrategy

# Node-related enums
from .enum_node_archetype import EnumNodeArchetype
from .enum_node_architecture_type import EnumNodeArchitectureType
from .enum_node_kind import EnumNodeKind
from .enum_node_requirement import EnumNodeRequirement
from .enum_node_status import EnumNodeStatus
from .enum_node_type import EnumNodeType
from .enum_notification_method import EnumNotificationMethod
from .enum_numeric_value_type import EnumNumericValueType
from .enum_onex_error_code import EnumOnexErrorCode

# Response and reply enums
from .enum_onex_reply_status import EnumOnexReplyStatus

# Operation status enum (canonical for operation results - OMN-1310)
from .enum_operation_status import EnumOperationStatus

# Orchestrator-related enums (from nodes)
from .enum_orchestrator_capability import EnumOrchestratorCapability
from .enum_orchestrator_types import EnumActionType, EnumBranchCondition

# Parameter and return type enums
from .enum_parameter_type import EnumParameterType

# Patch validation error codes (OMN-1126)
from .enum_patch_validation_error_code import EnumPatchValidationErrorCode

# Pattern extraction enums (OMN-1587)
from .enum_pattern_kind import EnumPatternKind

# Pipeline validation mode enum (pipeline processing OMN-1308)
from .enum_pipeline_validation_mode import EnumPipelineValidationMode
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

# Registration status enum (DI container registration)
from .enum_registration_status import EnumRegistrationStatus
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

# Sentiment enum (OMN-1395 demo)
from .enum_sentiment import EnumSentiment

# Service-related enums
from .enum_service_health_status import EnumServiceHealthStatus
from .enum_service_lifecycle import EnumServiceLifecycle
from .enum_service_mode import EnumServiceMode
from .enum_service_resolution_status import EnumServiceResolutionStatus
from .enum_service_status import EnumServiceStatus

# Service architecture enums
from .enum_service_tier import EnumServiceTier
from .enum_service_type_category import EnumServiceTypeCategory

# Severity enum (canonical - replaces EnumViolationSeverity, OMN-1311)
from .enum_severity import EnumSeverity

# Event enums (contract registration - OMN-1651)
from .events.enum_deregistration_reason import EnumDeregistrationReason

# Hook event enums (Claude Code integration - OMN-1474)
from .hooks.claude_code.enum_claude_code_hook_event_type import (
    EnumClaudeCodeHookEventType,
)
from .hooks.claude_code.enum_claude_code_session_status import (
    EnumClaudeCodeSessionStatus,
)
from .hooks.claude_code.enum_claude_code_tool_name import (
    EnumClaudeCodeToolName,
)

# Intelligence enums (OMN-1490)
from .intelligence.enum_intent_category import EnumIntentCategory

# Pattern learning enums (OMN-1683)
from .pattern_learning.enum_pattern_learning_status import EnumPatternLearningStatus
from .pattern_learning.enum_pattern_lifecycle_state import EnumPatternLifecycleState
from .pattern_learning.enum_pattern_type import EnumPatternType

# Deprecated aliases for EnumSeverity (OMN-1311 consolidation)
# Use EnumSeverity directly in new code.
EnumInvariantSeverity: type[EnumSeverity] = EnumSeverity
EnumValidationSeverity: type[EnumSeverity] = EnumSeverity
EnumViolationSeverity: type[EnumSeverity] = EnumSeverity
from .enum_state_update_operation import EnumStateUpdateOperation

# Step type enum (workflow step types)
from .enum_step_type import EnumStepType

# Subject type enums (OMN-1237)
from .enum_subject_type import EnumSubjectType

# Support enums (OMN-1395 demo)
from .enum_support_category import EnumSupportCategory
from .enum_support_channel import EnumSupportChannel

# Token and authentication context enums (OMN-1054)
from .enum_token_type import EnumTokenType

# Tool-related enums
from .enum_tool_category import EnumToolCategory

# Tool lifecycle enums
from .enum_tool_status import EnumToolStatus
from .enum_tool_type import EnumToolType

# Topic taxonomy enums (OMN-939)
from .enum_topic_taxonomy import EnumCleanupPolicy, EnumTopicType

# Transformation types (contract-driven NodeCompute v1.0)
from .enum_transformation_type import EnumTransformationType

# State management enums
from .enum_transition_type import EnumTransitionType

# Tree sync enums
from .enum_tree_sync_status import EnumTreeSyncStatus
from .enum_trigger_event import EnumTriggerEvent

# Trim mode enums (contract-driven NodeCompute v1.0)
from .enum_trim_mode import EnumTrimMode

# Unicode form enums (contract-driven NodeCompute v1.0)
from .enum_unicode_form import EnumUnicodeForm

# URI-related enums
from .enum_uri_type import EnumUriType
from .enum_validation import EnumValidationLevel
from .enum_validation_mode import EnumValidationMode
from .enum_validation_rule_type import EnumValidationRuleType
from .enum_value_type import EnumValueType

# Vector store enums
from .enum_vector_distance_metric import EnumVectorDistanceMetric
from .enum_vector_filter_operator import EnumVectorFilterOperator

# Version and contract enums
from .enum_version_status import EnumVersionStatus
from .enum_widget_type import EnumWidgetType

# Workflow-related enums
from .enum_workflow_coordination import EnumFailureRecoveryStrategy
from .enum_workflow_dependency_type import EnumWorkflowDependencyType
from .enum_workflow_status import EnumWorkflowStatus

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
    "EnumPatchValidationErrorCode",
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
    "EnumValidationRuleType",
    # Circuit breaker domain (standalone for cross-repo standardization)
    "EnumCircuitBreakerState",
    # Effect domain (from nodes)
    "EnumEffectHandlerType",
    "EnumEffectType",
    "EnumTransactionState",
    # Effect classification domain (OMN-1147)
    "EnumEffectCategory",
    "EnumEffectPolicyLevel",
    # Execution domain
    "EnumExecutionMode",
    "EnumExecutionShape",
    "EnumExecutionTrigger",
    "EnumMessageCategory",
    # Log level domain
    "EnumLogLevel",
    # Health and status domain
    "EnumHealthCheckType",
    "EnumHealthDetailType",
    "EnumHealthStatus",  # Canonical health status (OMN-1310)
    "EnumNodeStatus",
    # Node domain
    "EnumNodeArchetype",
    "EnumNodeArchitectureType",
    "EnumNodeKind",
    "EnumNodeType",
    "EnumOperationStatus",  # Canonical operation status (OMN-1310)
    "EnumExecutionStatus",  # Canonical execution status (OMN-1310)
    "EnumValidationLevel",
    "EnumValidationMode",
    "EnumValueType",
    "EnumNumericValueType",
    # Orchestrator domain (from nodes)
    "EnumActionStatus",
    "EnumActionType",
    "EnumBranchCondition",
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
    # Merge domain (OMN-1127)
    "EnumMergeConflictType",
    # Namespace domain
    "EnumNamespaceStrategy",
    # Resource domain
    "EnumResourceUnit",
    # URI domain
    "EnumUriType",
    # Workflow domain
    "EnumFailureRecoveryStrategy",
    "EnumWorkflowDependencyType",
    "EnumWorkflowStatus",
    # Infrastructure domain
    "EnumAuthType",
    "EnumBackoffStrategy",
    "EnumNotificationMethod",
    # Binding function domain (Operation Bindings DSL - OMN-1410)
    "EnumBindingFunction",
    # Audit and governance domain
    "EnumAuditAction",
    # Architecture and system domain
    "EnumArchitecture",
    "EnumLogFormat",
    # Communication domain
    "EnumMappingType",
    "EnumMessageType",
    # MCP (Model Context Protocol) domain (OMN-1286)
    "EnumMCPParameterType",
    "EnumMCPStatus",
    "EnumMCPToolType",
    # Group and organization domain
    "EnumGroupStatus",
    # Handler command type domain (OMN-1085)
    "EnumHandlerCommandType",
    # Handler execution phase domain (OMN-1108)
    "EnumHandlerExecutionPhase",
    # Handler routing strategy domain (OMN-1295)
    "EnumHandlerRoutingStrategy",
    # Handler role domain (OMN-1086)
    "EnumHandlerRole",
    # Handler type domain (runtime handler registry)
    "EnumHandlerType",
    "EnumHandlerTypeCategory",
    # Hash algorithm domain (handler packaging OMN-1119)
    "EnumHashAlgorithm",
    # Version and contract domain
    "EnumVersionStatus",
    "EnumContractCompliance",
    # Contract diff domain (semantic contract diffing)
    "EnumContractDiffChangeType",
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
    "EnumHandlerCapability",
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
    # Directive type domain (runtime-internal)
    "EnumDirectiveType",
    # Dispatch status domain
    "EnumDispatchStatus",
    # Function-related domain
    "EnumFunctionLanguage",
    # Registration status domain (DI container OMN-1308)
    "EnumRegistrationStatus",
    # Registry-related domain
    "EnumRegistryHealthStatus",
    "EnumRegistryType",
    # Service-related domain (includes DI container OMN-1308)
    "EnumInjectionScope",
    "EnumServiceHealthStatus",
    "EnumServiceLifecycle",
    "EnumServiceMode",
    "EnumServiceResolutionStatus",
    "EnumServiceStatus",
    "EnumServiceTypeCategory",
    # Tool-related domain
    "EnumToolCategory",
    "EnumToolType",
    # Topic taxonomy domain (OMN-939)
    "EnumCleanupPolicy",
    "EnumTopicType",
    # GitHub Actions domain
    "EnumGithubActionEvent",
    "EnumGithubRunnerOs",
    # Header and query parameter transformation domain
    "EnumHeaderTransformationType",
    "EnumQueryParameterTransformationType",
    "EnumResponseHeaderTransformationType",
    # Vector store domain
    "EnumVectorDistanceMetric",
    "EnumVectorFilterOperator",
    # Checkpoint domain
    "EnumCheckpointType",
    # Change type domain (OMN-1196)
    "EnumChangeType",
    # Token and authentication context domain (OMN-1054)
    "EnumTokenType",
    "EnumTriggerEvent",
    "EnumLikelihood",
    # Invariant domain (OMN-1192, OMN-1206, OMN-1207)
    "EnumComparisonType",
    "EnumInvariantReportStatus",
    "EnumInvariantType",
    # Severity domain (OMN-1311 - canonical, replaces EnumViolationSeverity)
    "EnumSeverity",
    # Deprecated aliases for EnumSeverity (OMN-1311 consolidation)
    "EnumInvariantSeverity",
    "EnumValidationSeverity",
    "EnumViolationSeverity",
    # Impact severity domain (OMN-1311 - business impact scale)
    "EnumImpactSeverity",
    # Dashboard domain (OMN-1284)
    "EnumDashboardStatus",
    "EnumDashboardTheme",
    "EnumWidgetType",
    # Event priority domain (OMN-1308)
    "EnumEventPriority",
    # Event sink type domain (OMN-1151)
    "EnumEventSinkType",
    # Hook event domain (Claude Code integration - OMN-1474, OMN-1701)
    "EnumClaudeCodeHookEventType",
    "EnumClaudeCodeSessionStatus",
    "EnumClaudeCodeToolName",
    # Intelligence domain (OMN-1490)
    "EnumIntentCategory",
    # Contract registration domain (OMN-1651)
    "EnumDeregistrationReason",
    # Pattern extraction domain (OMN-1587)
    "EnumPatternKind",
    # Pattern learning domain (OMN-1683)
    "EnumPatternLearningStatus",
    "EnumPatternLifecycleState",
    "EnumPatternType",
    # Omnimemory domain (OMN-1235, OMN-1236, OMN-1237)
    "EnumDecisionType",
    "EnumFailureType",
    "EnumSubjectType",
    # Step type domain (workflow steps OMN-1308)
    "EnumStepType",
    # Pipeline validation mode domain (OMN-1308)
    "EnumPipelineValidationMode",
    # Observability cardinality domain (OMN-1367)
    "EnumLabelViolationType",
    "EnumMetricsPolicyViolationAction",
    # Demo/sample artifact enums (OMN-1395, OMN-1397)
    "EnumCustomerTier",
    "EnumDemoRecommendation",
    "EnumDemoVerdict",
    "EnumSentiment",
    "EnumSupportCategory",
    "EnumSupportChannel",
    # NOTE: Removed from __all__ due to missing module files or circular imports:
    # - "EnumRegistryType" (module doesn't exist)
    # - "ModelServiceModeEnum" (replaced with correct "EnumServiceMode")
    # - "ModelEnumStatusMigrator" (moved to models.core - import from model_status_migrator directly)
    # - "EnumToolCriticality" (module doesn't exist)
    # - "EnumToolHealthStatus" (module doesn't exist)
    # - "EnumToolMissingReason" (module doesn't exist)
    # - "EnumTreeSyncStatus" (module doesn't exist)
]
