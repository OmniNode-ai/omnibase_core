"""Core models for OmniBase - Re-exports from domain-specific directories."""

# CLI models
from omnibase_spi.protocols.types import ProtocolSupportedMetadataType

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
from ..infrastructure.model_retry_policy import ModelRetryPolicy
from ..infrastructure.model_time_based import ModelTimeBased
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
from .model_configuration_base import ModelConfigurationBase

# Generic container pattern
from .model_container import (
    ModelContainer,

)
from .model_custom_fields_accessor import ModelCustomFieldsAccessor

# Custom properties pattern
from .model_custom_properties import ModelCustomProperties
from .model_environment_accessor import ModelEnvironmentAccessor

# Field accessor patterns
from .model_field_accessor import ModelFieldAccessor

# Generic collection pattern
from .model_generic_collection import ModelGenericCollection
from .model_generic_collection_summary import ModelGenericCollectionSummary
from .model_result_accessor import ModelResultAccessor
from .model_typed_accessor import ModelTypedAccessor
from .model_typed_configuration import ModelTypedConfiguration

# Generic factory pattern
try:
    from .model_capability_factory import CapabilityFactory
    from .model_generic_factory import ModelGenericFactory
    from .model_result_factory import ResultFactory
    from .model_validation_error_factory import ValidationErrorFactory

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
    "ModelTimeout",
    "ProtocolSupportedMetadataType",
    "Result",
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
    "ModelGenericCollectionSummary",
    # Generic container pattern
    "ModelContainer",


    # Configuration base classes
    "ModelConfigurationBase",
    "ModelTypedConfiguration",
    # Custom properties pattern
    "ModelCustomProperties",
]

# Add factory classes to __all__ if available
if _FACTORY_AVAILABLE:
    __all__.extend(
        [
            "CapabilityFactory",
            "ModelGenericFactory",
            "ResultFactory",
            "ValidationErrorFactory",
        ],
    )
