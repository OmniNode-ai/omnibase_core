from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

"""
Common models for shared use across domains.

This module contains models that are used across multiple domains
and are not specific to any particular functionality area.
"""

from omnibase_core.errors.error_codes import ModelOnexError

from .model_error_context import ModelErrorContext
from .model_flexible_value import ModelFlexibleValue
from .model_numeric_value import ModelNumericValue
from .model_schema_value import ModelSchemaValue
from .model_validation_result import (
    ModelValidationIssue,
    ModelValidationMetadata,
    ModelValidationResult,
)

__all__ = [
    "ModelErrorContext",
    "ModelFlexibleValue",
    "ModelNumericValue",
    "ModelOnexError",
    "ModelSchemaValue",
    "ModelValidationIssue",
    "ModelValidationMetadata",
    "ModelValidationResult",
]
