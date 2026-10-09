# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Common models for shared use across domains.

Models that are used across multiple domains
and are not specific to any particular functionality area.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model_coercion_mode import EnumCoercionMode
    from .model_dict_value_union import ModelDictValueUnion
    from .model_discriminated_value import ModelDiscriminatedValue
    from .model_envelope import (
        ModelEnvelope,
        get_chain_depth,
        validate_causation_chain,
        validate_envelope_fields,
    )
    from .model_envelope_payload import ModelEnvelopePayload
    from .model_error_context import ModelErrorContext
    from .model_flexible_value import ModelFlexibleValue
    from .model_graph_node_inputs import ModelGraphNodeInputs
    from .model_graph_node_parameter import ModelGraphNodeParameter
    from .model_graph_node_parameters import ModelGraphNodeParameters
    from .model_multi_type_value import ModelMultiTypeValue
    from .model_numeric_string_value import ModelNumericStringValue
    from .model_numeric_value import ModelNumericValue
    from .model_onex_warning import ModelOnexWarning
    from .model_optional_int import ModelOptionalInt
    from .model_output_mapping import ModelOutputMapping
    from .model_output_reference import ModelOutputReference
    from .model_query_parameters import ModelQueryParameters, QueryParameterValue
    from .model_registry_error import ModelRegistryError
    from .model_schema_value import ModelSchemaValue
    from .model_typed_mapping import ModelTypedMapping
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
    from .model_value_container import ModelValueContainer
    from .model_value_union import ModelValueUnion

__all__ = [
    "EnumCoercionMode",
    "ModelDictValueUnion",
    "ModelDiscriminatedValue",
    "ModelEnvelope",
    "ModelEnvelopePayload",
    "ModelErrorContext",
    "ModelFlexibleValue",
    "ModelGraphNodeParameter",
    "ModelGraphNodeParameters",
    "ModelMultiTypeValue",
    "ModelNumericValue",
    "ModelNumericStringValue",
    "ModelOnexWarning",
    "ModelOptionalInt",
    "ModelOutputMapping",
    "ModelOutputReference",
    "ModelQueryParameters",
    "ModelRegistryError",
    "ModelSchemaValue",
    "ModelTypedMapping",
    "ModelValidationIssue",
    "ModelValidationMetadata",
    "ModelValidationResult",
    "ModelValueContainer",
    "ModelValueUnion",
    # Type aliases
    "QueryParameterValue",
    # Envelope validation helpers
    "get_chain_depth",
    "validate_causation_chain",
    "validate_envelope_fields",
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "EnumCoercionMode": (
        "omnibase_core.models.common.model_coercion_mode",
        "EnumCoercionMode",
    ),
    "ModelDictValueUnion": (
        "omnibase_core.models.common.model_dict_value_union",
        "ModelDictValueUnion",
    ),
    "ModelDiscriminatedValue": (
        "omnibase_core.models.common.model_discriminated_value",
        "ModelDiscriminatedValue",
    ),
    "ModelEnvelope": ("omnibase_core.models.common.model_envelope", "ModelEnvelope"),
    "get_chain_depth": (
        "omnibase_core.models.common.model_envelope",
        "get_chain_depth",
    ),
    "validate_causation_chain": (
        "omnibase_core.models.common.model_envelope",
        "validate_causation_chain",
    ),
    "validate_envelope_fields": (
        "omnibase_core.models.common.model_envelope",
        "validate_envelope_fields",
    ),
    "ModelEnvelopePayload": (
        "omnibase_core.models.common.model_envelope_payload",
        "ModelEnvelopePayload",
    ),
    "ModelErrorContext": (
        "omnibase_core.models.common.model_error_context",
        "ModelErrorContext",
    ),
    "ModelFlexibleValue": (
        "omnibase_core.models.common.model_flexible_value",
        "ModelFlexibleValue",
    ),
    "ModelGraphNodeInputs": (
        "omnibase_core.models.common.model_graph_node_inputs",
        "ModelGraphNodeInputs",
    ),
    "ModelGraphNodeParameter": (
        "omnibase_core.models.common.model_graph_node_parameter",
        "ModelGraphNodeParameter",
    ),
    "ModelGraphNodeParameters": (
        "omnibase_core.models.common.model_graph_node_parameters",
        "ModelGraphNodeParameters",
    ),
    "ModelMultiTypeValue": (
        "omnibase_core.models.common.model_multi_type_value",
        "ModelMultiTypeValue",
    ),
    "ModelNumericStringValue": (
        "omnibase_core.models.common.model_numeric_string_value",
        "ModelNumericStringValue",
    ),
    "ModelNumericValue": (
        "omnibase_core.models.common.model_numeric_value",
        "ModelNumericValue",
    ),
    "ModelOnexWarning": (
        "omnibase_core.models.common.model_onex_warning",
        "ModelOnexWarning",
    ),
    "ModelOptionalInt": (
        "omnibase_core.models.common.model_optional_int",
        "ModelOptionalInt",
    ),
    "ModelOutputMapping": (
        "omnibase_core.models.common.model_output_mapping",
        "ModelOutputMapping",
    ),
    "ModelOutputReference": (
        "omnibase_core.models.common.model_output_reference",
        "ModelOutputReference",
    ),
    "ModelQueryParameters": (
        "omnibase_core.models.common.model_query_parameters",
        "ModelQueryParameters",
    ),
    "QueryParameterValue": (
        "omnibase_core.models.common.model_query_parameters",
        "QueryParameterValue",
    ),
    "ModelRegistryError": (
        "omnibase_core.models.common.model_registry_error",
        "ModelRegistryError",
    ),
    "ModelSchemaValue": (
        "omnibase_core.models.common.model_schema_value",
        "ModelSchemaValue",
    ),
    "ModelTypedMapping": (
        "omnibase_core.models.common.model_typed_mapping",
        "ModelTypedMapping",
    ),
    "ModelConfigSchemaProperty": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelConfigSchemaProperty",
    ),
    "ModelCustomHealthMetrics": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelCustomHealthMetrics",
    ),
    "ModelEffectMetadata": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelEffectMetadata",
    ),
    "ModelEventSubscriptionConfig": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelEventSubscriptionConfig",
    ),
    "ModelGraphNodeData": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelGraphNodeData",
    ),
    "ModelIntentPayload": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelIntentPayload",
    ),
    "ModelIntrospectionCustomMetrics": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelIntrospectionCustomMetrics",
    ),
    "ModelMixinConfigSchema": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelMixinConfigSchema",
    ),
    "ModelNodeCapabilitiesMetadata": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelNodeCapabilitiesMetadata",
    ),
    "ModelNodeRegistrationMetadata": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelNodeRegistrationMetadata",
    ),
    "ModelOperationData": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelOperationData",
    ),
    "ModelReducerMetadata": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelReducerMetadata",
    ),
    "ModelRequestMetadata": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelRequestMetadata",
    ),
    "ModelShutdownMetrics": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelShutdownMetrics",
    ),
    "ModelToolMetadataFields": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelToolMetadataFields",
    ),
    "ModelToolResultData": (
        "omnibase_core.models.common.model_typed_metadata",
        "ModelToolResultData",
    ),
    "ModelValidationIssue": (
        "omnibase_core.models.common.model_validation_result",
        "ModelValidationIssue",
    ),
    "ModelValidationMetadata": (
        "omnibase_core.models.common.model_validation_result",
        "ModelValidationMetadata",
    ),
    "ModelValidationResult": (
        "omnibase_core.models.common.model_validation_result",
        "ModelValidationResult",
    ),
    "ModelValueContainer": (
        "omnibase_core.models.common.model_value_container",
        "ModelValueContainer",
    ),
    "ModelValueUnion": (
        "omnibase_core.models.common.model_value_union",
        "ModelValueUnion",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        # A submodule that the old eager __init__ loaded as a side effect
        # stays reachable as ``package.submodule``: import it on first access.
        if (
            name.isidentifier()
            and not name.startswith("__")
            and importlib.util.find_spec(f"{__name__}.{name}") is not None
        ):
            return importlib.import_module(f"{__name__}.{name}")
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
