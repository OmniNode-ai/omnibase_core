"""
OmniBase Core Domain Models.

Core models that are foundational to the OmniBase ecosystem.
These models provide basic functionality used across all domains.
"""

# Artifact and CLI models
from .model_artifact_type_config import ModelArtifactTypeConfig
from .model_cli_action import ModelCliAction
from .model_cli_output_data import ModelCliOutputData
from .model_cli_result import ModelCliResult
from .model_cli_execution import ModelCliExecution
from .model_cli_execution_result import ModelCliExecutionResult

# Connection and data models
from .model_custom_fields import ModelCustomFields
from .model_custom_filters import ModelCustomFilters
from .model_data_handling_declaration import ModelDataHandlingDeclaration

# Generic collection and container models
from .model_generic_collection import (
    ModelGenericCollection,
    ModelIdentifiableCollection,
    ModelSearchableCollection,
    Identifiable,
    SearchableItem,
    create_collection,
    create_identifiable_collection,
    create_searchable_collection,
)
from .model_generic_container import (
    ModelGenericContainer,
    ModelKeyValueContainer,
    ModelCachingContainer,
    Serializable,
    Cacheable,
    create_container,
    create_key_value_container,
    create_caching_container,
)
# TODO: Temporarily disabled due to missing dependencies
# from .model_connection_info import ModelConnectionInfo
# from .model_custom_connection_properties import ModelCustomConnectionProperties

# Environment and configuration
from .model_environment_properties import ModelEnvironmentProperties
from .model_examples_collection import ModelExamples
from .model_fallback_strategy import ModelFallbackStrategy
from .model_file_filter import ModelFileFilter

# Function and advanced models
from .model_advanced_params import ModelAdvancedParams
# TODO: Temporarily disabled due to missing dependencies
# from .model_function_node import ModelFunctionNode

# Generic and metadata models
# TODO: Temporarily disabled due to import dependencies
# from .model_generic_metadata import ModelGenericMetadata
# from .model_metadata_field_info import ModelMetadataFieldInfo
# from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
# from .model_metadata_node_info import (
#     ModelMetadataNodeComplexity,
#     ModelMetadataNodeInfo,
#     ModelMetadataNodeStatus,
#     ModelMetadataNodeType,
#     ModelMetadataUsageMetrics,
# )
# from .model_metadata_usage_metrics import (
#     ModelMetadataUsageMetrics as ModelMetadataUsageMetricsStandalone,
# )

# Configuration and namespace models
# TODO: Temporarily disabled due to import dependencies
# from .model_namespace_config import ModelNamespaceConfig
# from .model_node_configuration import ModelNodeConfiguration

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

# Schema models with enhanced generics
from .model_schema_value import (
    ModelSchemaValue,
    ModelSchemaValueFactory,
    ModelSchemaValueString,
    ModelSchemaValueNumber,
    ModelSchemaValueBoolean,
    ModelSchemaValueNull,
    ConvertibleToSchema,
    ModelSchemaValueArray,
    ModelSchemaValueObject,
    from_value,
    to_value,
)

# Testing and analysis
from .model_test_result import ModelTestResult
from .model_test_results import ModelTestResults
from .model_trend_data import ModelTrendData
from .model_trend_metrics import ModelTrendMetrics
from .model_trend_point import ModelTrendPoint

# Examples and error handling
from .model_error_context import ModelErrorContext
from .model_example import ModelExample
from .model_example_input import ModelExampleInput
from .model_example_metadata import ModelExampleMetadata
from .model_example_output import ModelExampleOutput
from .model_onex_error import ModelOnexError

# Utility models
from .model_uri import ModelOnexUri

__all__ = [
    # Artifact and CLI models
    "ModelArtifactTypeConfig",
    "ModelCliAction",
    "ModelCliOutputData",
    "ModelCliResult",
    "ModelCliExecution",
    "ModelCliExecutionResult",

    # Connection and data models
    "ModelCustomFields",
    "ModelCustomFilters",
    "ModelDataHandlingDeclaration",
    # TODO: Temporarily disabled due to missing dependencies
    # "ModelConnectionInfo",
    # "ModelCustomConnectionProperties",

    # Environment and configuration
    "ModelEnvironmentProperties",
    "ModelExamples",
    "ModelFallbackStrategy",
    "ModelFileFilter",

    # Function and advanced models
    "ModelAdvancedParams",
    # TODO: Temporarily disabled due to missing dependencies
    # "ModelFunctionNode",

    # Generic and metadata models
    # TODO: Temporarily disabled due to import dependencies
    # "ModelGenericMetadata",
    # "ModelMetadataFieldInfo",
    # "ModelMetadataNodeAnalytics",
    # "ModelMetadataNodeComplexity",
    # "ModelMetadataNodeInfo",
    # "ModelMetadataNodeStatus",
    # "ModelMetadataNodeType",
    # "ModelMetadataUsageMetrics",
    # "ModelMetadataUsageMetricsStandalone",

    # Configuration and namespace models
    # TODO: Temporarily disabled due to import dependencies
    # "ModelNamespaceConfig",
    # "ModelNodeConfiguration",

    # Schema models
    "ModelSchemaValue",
    "ModelSchemaValueFactory",
    "ModelSchemaValueString",
    "ModelSchemaValueNumber",
    "ModelSchemaValueBoolean",
    "ModelSchemaValueNull",
    "ModelSchemaValueArray",
    "ModelSchemaValueObject",
    "from_value",
    "to_value",

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
    "ModelTestResult",
    "ModelTestResults",
    "ModelTrendData",
    "ModelTrendMetrics",
    "ModelTrendPoint",

    # Examples and error handling
    "ModelErrorContext",
    "ModelExample",
    "ModelExampleInput",
    "ModelExampleMetadata",
    "ModelExampleOutput",
    "ModelOnexError",

    # Utility models
    "ModelOnexUri",
]
