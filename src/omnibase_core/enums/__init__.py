"""
Shared enums for ONEX ecosystem.

Domain-grouped enums used across multiple ONEX packages (omnibase_core, omnibase_spi, etc.)
organized by functional domains for better maintainability.
"""

# Artifact-related enums
from .enum_artifact_type import ArtifactTypeEnum

# Security-related enums
from .enum_data_classification import EnumDataClassification

# File pattern enums
from .enum_ignore_pattern_source import IgnorePatternSourceEnum, TraversalModeEnum

# Log level enum
from .enum_log_level import EnumLogLevel

# Metadata-related enums
from .enum_metadata import (
    Lifecycle,
    MetaTypeEnum,
    ProtocolVersionEnum,
    RuntimeLanguageEnum,
)

# Namespace-related enums
from .enum_namespace_strategy import NamespaceStrategyEnum

# URI-related enums
from .enum_uri_type import UriTypeEnum

# Workflow-related enums
from .enum_workflow_dependency_type import EnumWorkflowDependencyType

# Execution-related enums
from .execution import EnumExecutionMode, EnumOperationStatus

# Node-related enums
from .node import EnumHealthStatus, EnumNodeStatus, EnumNodeType

# Validation-related enums
from .validation import EnumErrorSeverity, EnumValidationLevel, EnumValidationMode

# Event and logging enums
# from .events import EnumLogLevel  # Conflicts with enum_log_level.EnumLogLevel


__all__ = [
    # Artifact domain
    "ArtifactTypeEnum",
    # Security domain
    "EnumDataClassification",
    # Validation domain
    "EnumErrorSeverity",
    # Execution domain
    "EnumExecutionMode",
    "EnumHealthStatus",
    # Events domain
    "EnumLogLevel",
    "EnumNodeStatus",
    # Node domain
    "EnumNodeType",
    "EnumOperationStatus",
    "EnumValidationLevel",
    "EnumValidationMode",
    # File pattern domain
    "IgnorePatternSourceEnum",
    # Metadata domain
    "Lifecycle",
    "MetaTypeEnum",
    # Namespace domain
    "NamespaceStrategyEnum",
    "TraversalModeEnum",
    # URI domain
    "UriTypeEnum",
    # Workflow domain
    "EnumWorkflowDependencyType",
]
