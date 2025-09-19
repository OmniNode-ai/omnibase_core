"""
OmniBase Core Domain Models.

Core models that are foundational to the OmniBase ecosystem.
These models provide basic functionality used across all domains.
"""

# Artifact and CLI models
from .model_artifact_type_config import ModelArtifactTypeConfig
from .model_cli_action import ModelCliAction
from .model_cli_execution import ModelCliExecution
from .model_cli_execution_result import ModelCliExecutionResult
from .model_cli_output_data import ModelCliOutputData
from .model_cli_result import ModelCliResult

# Connection and data models
from .model_connection_info import ModelConnectionInfo
from .model_custom_connection_properties import ModelCustomConnectionProperties
from .model_custom_fields import ModelCustomFields
from .model_custom_filters import ModelCustomFilters
from .model_data_handling_declaration import ModelDataHandlingDeclaration

# Environment and configuration
from .model_environment_properties import ModelEnvironmentProperties
from .model_examples_collection import ModelExamples
from .model_fallback_strategy import ModelFallbackStrategy
from .model_file_filter import ModelFileFilter

# Function and advanced models
from .model_function_node import ModelFunctionNode
from .model_advanced_params import ModelAdvancedParams

# Generic and metadata models
from .model_generic_metadata import ModelGenericMetadata
from .model_metadata_field_info import ModelMetadataFieldInfo
from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_metadata_node_info import (
    ModelMetadataNodeComplexity,
    ModelMetadataNodeInfo,
    ModelMetadataNodeStatus,
    ModelMetadataNodeType,
    ModelMetadataUsageMetrics,
)
from .model_metadata_usage_metrics import (
    ModelMetadataUsageMetrics as ModelMetadataUsageMetricsStandalone,
)

# Configuration and namespace models
from .model_namespace_config import ModelNamespaceConfig
from .model_node_configuration import ModelNodeConfiguration

# Result handling models
from .model_result import (
    BoolResult,
    DictResult,
    IntResult,
    ListResult,
    Result,
    StrResult,
    collect_results,
    err,
    ok,
    try_result,
)

# Testing and analysis
from .model_test_results import ModelTestResults
from .model_trend_data import ModelTrendData

# Utility models
from .model_uri import ModelOnexUri

__all__ = [
    # Artifact and CLI models
    "ModelArtifactTypeConfig",
    "ModelCliAction",
    "ModelCliExecution",
    "ModelCliExecutionResult",
    "ModelCliOutputData",
    "ModelCliResult",

    # Connection and data models
    "ModelConnectionInfo",
    "ModelCustomConnectionProperties",
    "ModelCustomFields",
    "ModelCustomFilters",
    "ModelDataHandlingDeclaration",

    # Environment and configuration
    "ModelEnvironmentProperties",
    "ModelExamples",
    "ModelFallbackStrategy",
    "ModelFileFilter",

    # Function and advanced models
    "ModelFunctionNode",
    "ModelAdvancedParams",

    # Generic and metadata models
    "ModelGenericMetadata",
    "ModelMetadataFieldInfo",
    "ModelMetadataNodeAnalytics",
    "ModelMetadataNodeComplexity",
    "ModelMetadataNodeInfo",
    "ModelMetadataNodeStatus",
    "ModelMetadataNodeType",
    "ModelMetadataUsageMetrics",
    "ModelMetadataUsageMetricsStandalone",

    # Configuration and namespace models
    "ModelNamespaceConfig",
    "ModelNodeConfiguration",

    # Result handling models
    "Result",
    "StrResult",
    "BoolResult",
    "IntResult",
    "DictResult",
    "ListResult",
    "ok",
    "err",
    "try_result",
    "collect_results",

    # Testing and analysis
    "ModelTestResults",
    "ModelTrendData",

    # Utility models
    "ModelOnexUri",
]
