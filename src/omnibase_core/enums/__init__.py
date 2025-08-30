"""
Shared enums for ONEX ecosystem.

Domain-grouped enums used across multiple ONEX packages (omnibase-core, omnibase-spi, etc.)
organized by functional domains for better maintainability.
"""

# Artifact-related enums
from .enum_artifact_type import ArtifactTypeEnum
# Security-related enums
from .enum_data_classification import EnumDataClassification
# Metadata-related enums
from .enum_metadata import Lifecycle, MetaTypeEnum
# Event and logging enums
from .events import EnumLogLevel
# Execution-related enums
from .execution import EnumExecutionMode, EnumOperationStatus
# Node-related enums
from .node import EnumHealthStatus, EnumNodeStatus, EnumNodeType
# Validation-related enums
from .validation import (EnumErrorSeverity, EnumValidationLevel,
                         EnumValidationMode)

__all__ = [
    # Node domain
    "EnumNodeType",
    "EnumNodeStatus",
    "EnumHealthStatus",
    # Execution domain
    "EnumExecutionMode",
    "EnumOperationStatus",
    # Validation domain
    "EnumErrorSeverity",
    "EnumValidationLevel",
    "EnumValidationMode",
    # Events domain
    "EnumLogLevel",
    # Security domain
    "EnumDataClassification",
    # Metadata domain
    "Lifecycle",
    "MetaTypeEnum",
    # Artifact domain
    "ArtifactTypeEnum",
]
