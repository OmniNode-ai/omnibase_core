"""
Shared enums for ONEX ecosystem.

Domain-grouped enums used across multiple ONEX packages (omnibase-core, omnibase-spi, etc.)
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

# Event and logging enums
from .events import EnumLogLevel

# Execution-related enums
from .execution import EnumExecutionMode, EnumOperationStatus

# Node-related enums
from .node import EnumHealthStatus, EnumNodeStatus, EnumNodeType

# Validation-related enums
from .validation import EnumErrorSeverity, EnumValidationLevel, EnumValidationMode

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
    # Namespace domain
    "NamespaceStrategyEnum",
    # Metadata domain
    "Lifecycle",
    "MetaTypeEnum",
    # File pattern domain
    "IgnorePatternSourceEnum",
    "TraversalModeEnum",
]
