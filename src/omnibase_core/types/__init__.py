"""
ONEX TypedDict definitions module.

This module contains all TypedDict definitions following ONEX patterns.
TypedDicts provide type safety for dictionary structures without runtime overhead.
"""

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
