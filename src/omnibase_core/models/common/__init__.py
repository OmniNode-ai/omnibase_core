"""
Common models for shared use across domains.

This module contains models that are used across multiple domains
and are not specific to any particular functionality area.
"""

from .model_discriminated_value import ModelDiscriminatedValue
from .model_error_context import ModelErrorContext
from .model_flexible_value import ModelFlexibleValue
from .model_numeric_value import ModelNumericValue
from .model_schema_value import ModelSchemaValue
from .model_validation_result import (
    ModelValidationIssue,
    ModelValidationMetadata,
    ModelValidationResult,
)
from .model_value_union import ModelValueUnion

__all__ = [
    "ModelDiscriminatedValue",
    "ModelErrorContext",
    "ModelFlexibleValue",
    "ModelNumericValue",
    "ModelSchemaValue",
    "ModelValidationIssue",
    "ModelValidationMetadata",
    "ModelValidationResult",
    "ModelValueUnion",
]
