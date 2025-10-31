"""
Common models for shared use across domains.

This module contains models that are used across multiple domains
and are not specific to any particular functionality area.
"""

from .model_coercion_mode import EnumCoercionMode
from .model_dict_value_union import ModelDictValueUnion
from .model_discriminated_value import ModelDiscriminatedValue
from .model_error_context import ModelErrorContext
from .model_flexible_value import ModelFlexibleValue
from .model_multi_type_value import ModelMultiTypeValue
from .model_numeric_string_value import ModelNumericStringValue
from .model_numeric_value import ModelNumericValue
from .model_optional_int import ModelOptionalInt
from .model_schema_value import ModelSchemaValue
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
    "ModelErrorContext",
    "ModelFlexibleValue",
    "ModelMultiTypeValue",
    "ModelNumericValue",
    "ModelNumericStringValue",
    "ModelOptionalInt",
    "ModelSchemaValue",
    "ModelValidationIssue",
    "ModelValidationMetadata",
    "ModelValidationResult",
    "ModelValueUnion",
]
