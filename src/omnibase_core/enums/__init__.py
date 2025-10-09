from pydantic import Field

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

# Category filter enums
from .enum_category_filter import EnumCategoryFilter

# Computation and processing enums
from .enum_computation_type import EnumComputationType
from .enum_contract_compliance import EnumContractCompliance
from .enum_coordination_mode import EnumCoordinationMode

# Security-related enums
from .enum_data_classification import EnumDataClassification

# Detection and security enums
from .enum_detection_type import EnumDetectionType

# Execution-related enums
from .enum_execution import EnumExecutionMode, EnumOperationStatus

# GitHub Actions enums
from .enum_github_action_event import EnumGitHubActionEvent
from .enum_github_runner_os import EnumGitHubRunnerOS

# Group and organization enums
from .enum_group_status import EnumGroupStatus

# Health and status enums
from .enum_health_status_type import EnumHealthStatusType

# Hub and coordination enums
from .enum_hub_capability import EnumHubCapability

# File pattern enums
from .enum_ignore_pattern_source import EnumIgnorePatternSource, EnumTraversalMode

# Language and localization enums
from .enum_language_code import EnumLanguageCode
from .enum_log_format import EnumLogFormat

# Log level enum
from .enum_log_level import EnumLogLevel

# Communication enums
from .enum_message_type import EnumMessageType

# Metadata-related enums
# Function-related enums
from .enum_metadata import (
    EnumFunctionLanguage,
    EnumLifecycle,
    EnumMetaType,
    EnumNodeMetadataField,
    EnumProtocolVersion,
    EnumRuntimeLanguage,
)

# Namespace-related enums
from .enum_namespace_strategy import EnumNamespaceStrategy
from .enum_node_health_status import EnumNodeHealthStatus
from .enum_node_status import EnumNodeStatus

# Node-related enums
from .enum_node_type import EnumNodeType
from .enum_notification_method import EnumNotificationMethod

# Response and reply enums
from .enum_onex_reply_status import EnumOnexReplyStatus

# Parameter and return type enums
from .enum_parameter_type import EnumParameterType

# Registry-related enums
from .enum_registry_health_status import EnumRegistryHealthStatus
from .enum_return_type import EnumReturnType

# from .enum_registry_type import EnumRegistryType  # MISSING MODULE
from .enum_security_profile import EnumSecurityProfile

# Service-related enums
from .enum_service_health_status import EnumServiceHealthStatus
from .enum_service_mode import EnumServiceMode
from .enum_service_status import EnumServiceStatus

# Service architecture enums
from .enum_service_tier import EnumServiceTier
from .enum_service_type_category import EnumServiceTypeCategory
from .enum_state_update_operation import EnumStateUpdateOperation

# Tool lifecycle enums
from .enum_tool_status import EnumToolStatus
from .enum_tool_type import EnumToolType

# State management enums
from .enum_transition_type import EnumTransitionType

# URI-related enums
from .enum_uri_type import EnumUriType

# Validation-related enums
from .enum_validation import EnumErrorSeverity, EnumValidationLevel, EnumValidationMode

# Version and contract enums
from .enum_version_status import EnumVersionStatus

# Workflow-related enums
from .enum_workflow_dependency_type import EnumWorkflowDependencyType

# Status migration enums
# from .enum_status_migrator import ModelEnumStatusMigrator  # MISSING MODULE

# Tool-related enums
# from .enum_tool_category import EnumToolCategory  # MISSING MODULE
# from .enum_tool_criticality import EnumToolCriticality  # MISSING MODULE
# from .enum_tool_health_status import EnumToolHealthStatus  # MISSING MODULE
# from .enum_tool_missing_reason import EnumToolMissingReason  # MISSING MODULE


# Tree sync enums
# from .enum_tree_sync_status import EnumTreeSyncStatus  # MISSING MODULE


# Event and logging enums
# from .events import EnumLogLevel  # Conflicts with enum_log_level.EnumLogLevel


__all__ = [
    # Artifact domain
    "EnumArtifactType",
    # Category filter domain
    "EnumCategoryFilter",
    # Security domain
    "EnumDataClassification",
    "EnumSecurityProfile",
    "EnumAuthenticationMethod",
    # Validation domain
    "EnumErrorSeverity",
    # Execution domain
    "EnumExecutionMode",
    # Events domain
    "EnumLogLevel",
    # Health and status domain
    "EnumHealthStatusType",
    "EnumNodeHealthStatus",
    "EnumNodeStatus",
    # Node domain
    "EnumNodeType",
    "EnumOperationStatus",
    "EnumValidationLevel",
    "EnumValidationMode",
    # Parameter and return type domain
    "EnumParameterType",
    "EnumReturnType",
    # File pattern domain
    "EnumIgnorePatternSource",
    "EnumTraversalMode",
    # Metadata domain
    "EnumLifecycle",
    "EnumMetaType",
    "EnumNodeMetadataField",
    "EnumProtocolVersion",
    "EnumRuntimeLanguage",
    # Namespace domain
    "EnumNamespaceStrategy",
    # URI domain
    "EnumUriType",
    # Workflow domain
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
    "EnumMessageType",
    # Group and organization domain
    "EnumGroupStatus",
    # Version and contract domain
    "EnumVersionStatus",
    "EnumContractCompliance",
    # State management domain
    "EnumTransitionType",
    "EnumStateUpdateOperation",
    # Response and reply domain
    "EnumOnexReplyStatus",
    # Computation and processing domain
    "EnumComputationType",
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
    "ModelServiceModeEnum",
    "EnumServiceStatus",
    "EnumServiceTypeCategory",
    # Status migration domain
    "ModelEnumStatusMigrator",
    # Tool-related domain
    "EnumToolCategory",
    "EnumToolCriticality",
    "EnumToolHealthStatus",
    "EnumToolMissingReason",
    "EnumToolType",
    # Tree sync domain
    "EnumTreeSyncStatus",
    # GitHub Actions domain
    "EnumGitHubActionEvent",
    "EnumGitHubRunnerOS",
]
