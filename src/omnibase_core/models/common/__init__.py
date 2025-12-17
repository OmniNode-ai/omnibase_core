"""
Common models for shared use across domains.

This module contains models that are used across multiple domains
and are not specific to any particular functionality area.
"""

from .model_coercion_mode import EnumCoercionMode
from .model_dict_value_union import ModelDictValueUnion
from .model_discriminated_value import ModelDiscriminatedValue
from .model_envelope_payload import ModelEnvelopePayload, PayloadDataValue
from .model_error_context import ModelErrorContext
from .model_flexible_value import ModelFlexibleValue
from .model_graph_node_inputs import ModelGraphNodeInputs
from .model_graph_node_parameter import ModelGraphNodeParameter
from .model_graph_node_parameters import ModelGraphNodeParameters
from .model_multi_type_value import ModelMultiTypeValue
from .model_numeric_string_value import ModelNumericStringValue
from .model_numeric_value import ModelNumericValue
from .model_optional_int import ModelOptionalInt
from .model_output_mapping import ModelOutputMapping
from .model_output_reference import ModelOutputReference
from .model_query_parameters import ModelQueryParameters, ParameterValue
from .model_schema_value import ModelSchemaValue
from .model_typed_metadata import (
    ModelConfigSchemaProperty,
    ModelCustomHealthMetrics,
    ModelEffectMetadata,
    ModelEventSubscriptionConfig,
    ModelGraphNodeData,
    ModelIntentPayload,
    ModelIntrospectionCustomMetrics,
    ModelMixinConfigSchema,
    ModelNodeCapabilitiesMetadata,
    ModelNodeRegistrationMetadata,
    ModelOperationData,
    ModelReducerMetadata,
    ModelRequestMetadata,
    ModelShutdownMetrics,
    ModelToolMetadataFields,
    ModelToolResultData,
)
from .model_validation_result import (
    ModelValidationIssue,
    ModelValidationMetadata,
    ModelValidationResult,
)
from .model_value_union import ModelValueUnion

__all__ = [
    "EnumCoercionMode",
    "ModelDictValueUnion",
    "ModelDiscriminatedValue",
    "ModelEnvelopePayload",
    "ModelErrorContext",
    "ModelFlexibleValue",
    "ModelGraphNodeParameter",
    "ModelGraphNodeParameters",
    "ModelMultiTypeValue",
    "ModelNumericValue",
    "ModelNumericStringValue",
    "ModelOptionalInt",
    "ModelOutputMapping",
    "ModelOutputReference",
    "ModelQueryParameters",
    "ModelSchemaValue",
    "ModelValidationIssue",
    "ModelValidationMetadata",
    "ModelValidationResult",
    "ModelValueUnion",
    # Type aliases
    "ParameterValue",
    "PayloadDataValue",
    # Typed metadata models
    "ModelConfigSchemaProperty",
    "ModelCustomHealthMetrics",
    "ModelEffectMetadata",
    "ModelEventSubscriptionConfig",
    "ModelGraphNodeData",
    "ModelGraphNodeInputs",
    "ModelIntentPayload",
    "ModelIntrospectionCustomMetrics",
    "ModelMixinConfigSchema",
    "ModelNodeCapabilitiesMetadata",
    "ModelNodeRegistrationMetadata",
    "ModelOperationData",
    "ModelReducerMetadata",
    "ModelRequestMetadata",
    "ModelShutdownMetrics",
    "ModelToolMetadataFields",
    "ModelToolResultData",
]
