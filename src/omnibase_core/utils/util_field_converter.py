"""
FieldConverter

Represents a field conversion strategy.

This replaces hardcoded if/elif chains with a declarative,
extensible converter registry pattern.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_error_context import ModelErrorContext
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Use ModelSchemaValue directly for ONEX compliance


@dataclass(frozen=True)
class FieldConverter[T]:
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
        except (AttributeError, TypeError, ValueError) as e:
            # Catch type conversion errors or attribute access issues
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
        except ModelOnexError:
            # Re-raise ModelOnexError from validator without wrapping
            raise
