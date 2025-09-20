"""Core models for OmniBase - Re-exports from domain-specific directories."""

# CLI models
from ..cli.model_cli_execution import ModelCliExecution
from ..cli.model_cli_execution_result import ModelCliExecutionResult

# Connection models
from ..connections.model_custom_connection_properties import (
    ModelCustomConnectionProperties,
)

# Data models
from ..data.model_custom_fields import ModelCustomFields

# Infrastructure models
from ..infrastructure.model_duration import ModelDuration
from ..infrastructure.model_environment_variables import ModelEnvironmentVariables
from ..infrastructure.model_progress import ModelProgress
from ..infrastructure.model_result import (
    Result,
    collect_results,
    err,
    ok,
    try_result,
)
from ..infrastructure.model_retry_policy import ModelRetryPolicy, RetryBackoffStrategy
from ..infrastructure.model_time_based import (
    ModelTimeBased,
    TimeUnit,
)
from ..infrastructure.model_timeout import ModelTimeout

# Metadata models
from ..metadata.model_generic_metadata import ModelGenericMetadata
from ..metadata.model_metadata_node_analytics import ModelMetadataNodeAnalytics
from ..metadata.model_metadata_node_info import (
    ModelMetadataNodeComplexity,
    ModelMetadataNodeInfo,
    ModelMetadataNodeStatus,
    ModelMetadataNodeType,
    ModelMetadataUsageMetrics,
)
from ..metadata.model_metadata_usage_metrics import (
    ModelMetadataUsageMetrics as ModelMetadataUsageMetricsStandalone,
)

# Node models - removed ModelFunctionNode to avoid circular import with ModelCustomProperties
from ..nodes.model_node_configuration import ModelNodeConfiguration

# Configuration base classes
from .model_configuration_base import (
    ModelConfigurationBase,
    ModelTypedConfiguration,
)

# Custom properties pattern
from .model_custom_properties import ModelCustomProperties

# Field accessor patterns
from .model_field_accessor import (
    ModelCustomFieldsAccessor,
    ModelEnvironmentAccessor,
    ModelFieldAccessor,
    ModelResultAccessor,
    ModelTypedAccessor,
)

# Generic collection pattern
from .model_generic_collection import ModelGenericCollection

# Generic factory pattern
try:
    from .model_generic_factory import (
        CapabilityFactory,
        ModelGenericFactory,
        ResultFactory,
        ValidationErrorFactory,
    )

    _FACTORY_AVAILABLE = True
except ImportError:
    # Graceful degradation if circular imports prevent loading
    _FACTORY_AVAILABLE = False

__all__ = [
    "ModelCliExecution",
    "ModelCliExecutionResult",
    "ModelCustomConnectionProperties",
    "ModelCustomFields",
    "ModelDuration",
    "ModelEnvironmentVariables",
    "ModelFunctionNode",
    "ModelGenericMetadata",
    "ModelMetadataNodeAnalytics",
    "ModelMetadataNodeComplexity",
    "ModelMetadataNodeInfo",
    "ModelMetadataNodeStatus",
    "ModelMetadataNodeType",
    "ModelMetadataUsageMetrics",
    "ModelMetadataUsageMetricsStandalone",
    "ModelNodeConfiguration",
    "ModelProgress",
    "ModelRetryPolicy",
    "ModelTimeBased",
    "TimeUnit",
    "ModelTimeout",
    "Result",
    "RetryBackoffStrategy",
    "ok",
    "err",
    "try_result",
    "collect_results",
    # Field accessor patterns
    "ModelFieldAccessor",
    "ModelTypedAccessor",
    "ModelEnvironmentAccessor",
    "ModelResultAccessor",
    "ModelCustomFieldsAccessor",
    # Generic collection pattern
    "ModelGenericCollection",
    # Configuration base classes
    "ModelConfigurationBase",
    "ModelTypedConfiguration",
    "ModelSimpleConfiguration",
    # Custom properties pattern
    "ModelCustomProperties",
]

# Add factory classes to __all__ if available
if _FACTORY_AVAILABLE:
    __all__.extend(
        [
            "ModelGenericFactory",
            "ResultFactory",
            "CapabilityFactory",
            "ValidationErrorFactory",
        ]
    )
