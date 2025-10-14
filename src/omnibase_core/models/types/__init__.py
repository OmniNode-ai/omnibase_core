"""
ONEX Type System

This package previously contained loose union type aliases.
These have been removed in favor of strongly-typed Pydantic models.

For dynamic values, use:
- ModelSchemaValue: from omnibase_core.models.common.model_schema_value
- ModelCliValue: from omnibase_core.models.infrastructure.model_cli_value

ONEX Principle: Always use concrete Pydantic models with discriminated unions,
never loose type aliases like str | int | float | bool.
"""

__all__: list[str] = []
