"""
ONEX Types Module.

This module contains TypedDict definitions and type constraints following ONEX patterns.
TypedDicts provide type safety for dictionary structures without runtime overhead.
Type constraints provide protocols and type variables for better generic programming.
"""

from typing import TYPE_CHECKING

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

from .typed_dict_capability_factory_kwargs import TypedDictCapabilityFactoryKwargs
from .typed_dict_cli_input_dict import TypedDictCliInputDict
from .typed_dict_collection_kwargs import (
    TypedDictCollectionCreateKwargs,
    TypedDictCollectionFromItemsKwargs,
)
from .typed_dict_debug_info_data import TypedDictDebugInfoData
from .typed_dict_factory_kwargs import (
    TypedDictExecutionParams,
    TypedDictFactoryKwargs,
    TypedDictMessageParams,
    TypedDictMetadataParams,
)
from .typed_dict_field_value import TypedDictFieldValue
from .typed_dict_node_configuration_summary import TypedDictNodeConfigurationSummary
from .typed_dict_node_resource_constraint_kwargs import (
    TypedDictNodeResourceConstraintKwargs,
)
from .typed_dict_output_format_options_kwargs import TypedDictOutputFormatOptionsKwargs
from .typed_dict_performance_metric_data import TypedDictPerformanceMetricData
from .typed_dict_property_metadata import TypedDictPropertyMetadata
from .typed_dict_result_factory_kwargs import TypedDictResultFactoryKwargs
from .typed_dict_ssl_context_options import TypedDictSSLContextOptions
from .typed_dict_trace_info_data import TypedDictTraceInfoData

__all__ = [
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
