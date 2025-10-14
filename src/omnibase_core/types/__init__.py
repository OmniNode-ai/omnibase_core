"""
ONEX Types Module.

This module contains TypedDict definitions and type constraints following ONEX patterns.
TypedDicts provide type safety for dictionary structures without runtime overhead.
Type constraints provide protocols and type variables for better generic programming.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module's __init__.py is loaded whenever ANY submodule is imported (e.g., types.core_types).
To avoid circular dependencies, imports from .constraints are now LAZY-LOADED.

Import Chain:
1. types.core_types (minimal types, no external deps)
2. errors.error_codes → imports types.core_types → loads THIS __init__.py
3. models.common.model_schema_value → imports errors.error_codes
4. types.constraints → TYPE_CHECKING import of errors.error_codes
5. models.* → imports types.constraints

If this module directly imports from .constraints at module level, it creates:
error_codes → types.__init__ → constraints → (circular back to error_codes via models)

Solution: Use TYPE_CHECKING and __getattr__ for lazy loading, similar to ModelBaseCollection.
"""

from typing import TYPE_CHECKING

# All constraint imports are now lazy-loaded via __getattr__ to prevent circular imports
if TYPE_CHECKING:
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
        ModelBaseCollection,
        ModelBaseFactory,
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

# Core types for breaking circular dependencies
from .core_types import (
    BasicErrorContext,
    ProtocolErrorContext,
    ProtocolSchemaValue,
)
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
    # Core types (no dependencies)
    "BasicErrorContext",
    "ProtocolErrorContext",
    "ProtocolSchemaValue",
    # Type constraints and protocols
    "ModelBaseCollection",
    "ModelBaseFactory",
    "BaseCollection",
    "BaseFactory",
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
    """
    Lazy import for constraints module to avoid circular imports.

    All constraint imports are lazy-loaded to prevent circular dependency:
    error_codes → types.__init__ → constraints → models → error_codes
    """
    # List of all constraint exports that should be lazy-loaded
    constraint_exports = {
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
    }

    # ModelBaseCollection and ModelBaseFactory come from models.base, not constraints
    if name in ("ModelBaseCollection", "ModelBaseFactory"):
        from omnibase_core.models.base import ModelBaseCollection, ModelBaseFactory

        globals()["ModelBaseCollection"] = ModelBaseCollection
        globals()["ModelBaseFactory"] = ModelBaseFactory
        return globals()[name]

    # All other constraint exports come from .constraints
    if name in constraint_exports:
        # Import from constraints module
        from omnibase_core.types import constraints

        attr = getattr(constraints, name)
        globals()[name] = attr
        return attr

    msg = f"module {__name__!r} has no attribute {name!r}"
    # error-ok: AttributeError is standard Python pattern for __getattr__
    raise AttributeError(msg)
