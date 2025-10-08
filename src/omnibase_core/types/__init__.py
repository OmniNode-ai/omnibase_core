from datetime import datetime
from typing import Any, Dict, TypedDict

from pydantic import Field

"""
ONEX Types Module.

This module contains TypedDict definitions and type constraints following ONEX patterns.
TypedDicts provide type safety for dict[str, Any]ionary structures without runtime overhead.
Type constraints provide protocols and type variables for better generic programming.
"""

from typing import TYPE_CHECKING, Any, Dict, TypedDict

# Export all type constraints and protocols (except ModelBaseCollection/ModelBaseFactory)
from .constraints import (
    BasicValueType,
    CollectionItemType,
    ComplexContextValueType,
    Configurable,
    ConfigurableType,
    ContextValueType,
    ErrorType,
    Executable,
    ExecutableType,
    Identifiable,
    IdentifiableType,
    MetadataType,
    ModelType,
    Nameable,
    NameableType,
    NumericType,
    PrimitiveValueType,
    ProtocolMetadataProvider,
    ProtocolValidatable,
    Serializable,
    SerializableType,
    SimpleValueType,
    SuccessType,
    ValidatableType,
    is_complex_context_value,
    is_configurable,
    is_context_value,
    is_executable,
    is_identifiable,
    is_metadata_provider,
    is_nameable,
    is_primitive_value,
    is_serializable,
    is_validatable,
    validate_context_value,
    validate_primitive_value,
)

# ModelBaseCollection and ModelBaseFactory are lazily imported to avoid circular imports
if TYPE_CHECKING:
    from .constraints import ModelBaseCollection, ModelBaseFactory

# Core types for breaking circular dependencies
from .converter_error_details_to_typed_dict import convert_error_details_to_typed_dict
from .converter_health_to_typed_dict import convert_health_to_typed_dict

# Converter functions
from .converter_stats_to_typed_dict import convert_stats_to_typed_dict
from .core_types import ProtocolSchemaValue, TypedDictBasicErrorContext
from .typed_dict_audit_info import TypedDictAuditInfo
from .typed_dict_batch_processing_info import TypedDictBatchProcessingInfo
from .typed_dict_cache_info import TypedDictCacheInfo
from .typed_dict_capability_factory_kwargs import TypedDictCapabilityFactoryKwargs
from .typed_dict_cli_input_dict import TypedDictCliInputDict
from .typed_dict_collection_kwargs import (
    TypedDictCollectionCreateKwargs,
    TypedDictCollectionFromItemsKwargs,
)
from .typed_dict_configuration_settings import TypedDictConfigurationSettings
from .typed_dict_connection_info import TypedDictConnectionInfo
from .typed_dict_debug_info_data import TypedDictDebugInfoData
from .typed_dict_dependency_info import TypedDictDependencyInfo
from .typed_dict_error_details import TypedDictErrorDetails
from .typed_dict_event_info import TypedDictEventInfo
from .typed_dict_execution_stats import TypedDictExecutionStats
from .typed_dict_factory_kwargs import (
    TypedDictExecutionParams,
    TypedDictFactoryKwargs,
    TypedDictMessageParams,
    TypedDictMetadataParams,
)
from .typed_dict_feature_flags import TypedDictFeatureFlags
from .typed_dict_field_value import TypedDictFieldValue
from .typed_dict_health_status import TypedDictHealthStatus
from .typed_dict_legacy_error import TypedDictLegacyError
from .typed_dict_legacy_health import TypedDictLegacyHealth
from .typed_dict_legacy_stats import TypedDictLegacyStats
from .typed_dict_metrics import TypedDictMetrics
from .typed_dict_node_configuration_summary import TypedDictNodeConfigurationSummary
from .typed_dict_node_resource_constraint_kwargs import (
    TypedDictNodeResourceConstraintKwargs,
)
from .typed_dict_operation_result import TypedDictOperationResult
from .typed_dict_output_format_options_kwargs import TypedDictOutputFormatOptionsKwargs
from .typed_dict_performance_metric_data import TypedDictPerformanceMetricData
from .typed_dict_property_metadata import TypedDictPropertyMetadata
from .typed_dict_resource_usage import TypedDictResourceUsage
from .typed_dict_result_factory_kwargs import TypedDictResultFactoryKwargs
from .typed_dict_security_context import TypedDictSecurityContext

# New individual TypedDict classes extracted from typed_dict_structured_definitions.py
from .typed_dict_sem_ver import TypedDictSemVer
from .typed_dict_service_info import TypedDictServiceInfo
from .typed_dict_ssl_context_options import TypedDictSSLContextOptions
from .typed_dict_stats_collection import TypedDictStatsCollection
from .typed_dict_system_state import TypedDictSystemState
from .typed_dict_trace_info_data import TypedDictTraceInfoData
from .typed_dict_validation_result import TypedDictValidationResult
from .typed_dict_workflow_state import TypedDictWorkflowState

# Utility functions
from .util_datetime_parser import parse_datetime

__all__ = [
    # Core types (no dependencies)
    "TypedDictBasicErrorContext",
    "ProtocolErrorContext",
    "ProtocolSchemaValue",
    # Type constraints and protocols
    "ModelBaseCollection",
    "ModelBaseFactory",
    "BasicValueType",
    "CollectionItemType",
    "ComplexContextValueType",
    "Configurable",
    "ConfigurableType",
    "ContextValueType",
    "ErrorType",
    "Executable",
    "ExecutableType",
    "Identifiable",
    "IdentifiableType",
    "MetadataType",
    "ModelType",
    "Nameable",
    "NameableType",
    "NumericType",
    "PrimitiveValueType",
    "ProtocolMetadataProvider",
    "ProtocolValidatable",
    "Serializable",
    "SerializableType",
    "SimpleValueType",
    "SuccessType",
    "ValidatableType",
    "is_complex_context_value",
    "is_configurable",
    "is_context_value",
    "is_executable",
    "is_identifiable",
    "is_metadata_provider",
    "is_nameable",
    "is_primitive_value",
    "is_serializable",
    "is_validatable",
    "validate_context_value",
    "validate_primitive_value",
    # TypedDict definitions
    "TypedDictCapabilityFactoryKwargs",
    "TypedDictCliInputDict",
    "TypedDictCollectionCreateKwargs",
    "TypedDictCollectionFromItemsKwargs",
    "TypedDictDebugInfoData",
    "TypedDictExecutionParams",
    "TypedDictFactoryKwargs",
    "TypedDictFieldValue",
    "TypedDictMessageParams",
    "TypedDictMetadataParams",
    "TypedDictNodeConfigurationSummary",
    "TypedDictNodeResourceConstraintKwargs",
    "TypedDictOutputFormatOptionsKwargs",
    "TypedDictPerformanceMetricData",
    "TypedDictPropertyMetadata",
    "TypedDictResultFactoryKwargs",
    "TypedDictSSLContextOptions",
    "TypedDictTraceInfoData",
    # New individual TypedDict classes extracted from typed_dict_structured_definitions.py
    "TypedDictSemVer",
    "TypedDictExecutionStats",
    "TypedDictHealthStatus",
    "TypedDictResourceUsage",
    "TypedDictConfigurationSettings",
    "TypedDictValidationResult",
    "TypedDictMetrics",
    "TypedDictErrorDetails",
    "TypedDictOperationResult",
    "TypedDictWorkflowState",
    "TypedDictEventInfo",
    "TypedDictConnectionInfo",
    "TypedDictServiceInfo",
    "TypedDictDependencyInfo",
    "TypedDictCacheInfo",
    "TypedDictBatchProcessingInfo",
    "TypedDictSecurityContext",
    "TypedDictAuditInfo",
    "TypedDictFeatureFlags",
    "TypedDictStatsCollection",
    "TypedDictSystemState",
    "TypedDictLegacyStats",
    "TypedDictLegacyHealth",
    "TypedDictLegacyError",
    # Converter functions
    "convert_stats_to_typed_dict",
    "convert_health_to_typed_dict",
    "convert_error_details_to_typed_dict",
    # Utility functions
    "parse_datetime",
]


def __getattr__(name: str) -> object:
    """Lazy import for ModelBaseCollection and ModelBaseFactory to avoid circular imports."""
    if name in ("ModelBaseCollection", "ModelBaseFactory"):
        from omnibase_core.models.base import ModelBaseCollection, ModelBaseFactory

        globals()["ModelBaseCollection"] = ModelBaseCollection
        globals()["ModelBaseFactory"] = ModelBaseFactory
        return globals()[name]
    msg = f"module {__name__!r} has no attribute {name!r}"
    # error-ok: AttributeError is standard Python pattern for __getattr__
    raise AttributeError(msg)
