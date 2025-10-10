from __future__ import annotations

from typing import Callable, Generic, TypeVar

from pydantic import Field

from omnibase_core.errors.model_onex_error import ModelOnexError

"""
FieldConverter

Represents a field conversion strategy.

This replaces hardcoded if/elif chains with a declarative,
extensible converter registry pattern.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""


from collections.abc import Callable as CallableABC
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

from omnibase_core.errors.error_codes import EnumCoreErrorCode
from omnibase_core.errors.model_onex_error import ModelOnexError
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

# Use ModelSchemaValue directly for ONEX compliance

T = TypeVar("T")


@dataclass(frozen=True)
class FieldConverter(Generic[T]):
    """
    Represents a field conversion strategy.

    This replaces hardcoded if/elif chains with a declarative,
    extensible converter registry pattern.
    """

    field_name: str
    converter: Callable[[str], T]
    default_value: T | None = None
    validator: Callable[[T], bool] | None = None

    def convert(self, value: str) -> T:
        """
        Convert string value to typed value.

        Args:
            value: String value to convert

        Returns:
            Converted typed value

        Raises:
            ModelOnexError: If conversion fails
        """
        try:
            result = self.converter(value)

            # Validate if validator provided
            if self.validator and not self.validator(result):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Validation failed for field {self.field_name}",
                    details=ModelErrorContext.with_context(
                        {
                            "field_name": ModelSchemaValue.from_value(self.field_name),
                            "value": ModelSchemaValue.from_value(value),
                            "converted_value": ModelSchemaValue.from_value(str(result)),
                        },
                    ),
                )

            return result
        except Exception as e:
            if isinstance(e, ModelOnexError):
                raise

            # Use default if available
            if self.default_value is not None:
                return self.default_value

            raise ModelOnexError(
                error_code=EnumCoreErrorCode.CONVERSION_ERROR,
                message=f"Failed to convert field {self.field_name}: {e!s}",
                details=ModelErrorContext.with_context(
                    {
                        "field_name": ModelSchemaValue.from_value(self.field_name),
                        "value": ModelSchemaValue.from_value(value),
                        "error": ModelSchemaValue.from_value(str(e)),
                    },
                ),
            )
