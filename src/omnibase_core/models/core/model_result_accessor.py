"""
Result field accessor for CLI results and output data.

Specialized accessor for handling CLI execution results and metadata.
"""

from __future__ import annotations

from typing import cast

from omnibase_core.core.type_constraints import PrimitiveValueType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue

from .model_field_accessor import ModelFieldAccessor


class ModelResultAccessor(ModelFieldAccessor):
    """Specialized accessor for CLI results and output data."""

    def get_result_value(
        self,
        key: str,
        default: PrimitiveValueType | None = None,
    ) -> PrimitiveValueType | None:
        """Get result value from results or metadata fields. Returns raw value or default."""
        # Try results first
        results_value = self.get_field(f"results.{key}")
        if results_value.is_ok():
            return cast(PrimitiveValueType, results_value.unwrap().to_value())

        # Try metadata second
        metadata_value = self.get_field(f"metadata.{key}")
        if metadata_value.is_ok():
            return cast(PrimitiveValueType, metadata_value.unwrap().to_value())

        # If both failed, return default
        return default

    def set_result_value(
        self, key: str, value: PrimitiveValueType | ModelSchemaValue
    ) -> bool:
        """Set result value in results field. Accepts raw values or ModelSchemaValue."""
        if isinstance(value, ModelSchemaValue):
            schema_value = value
        else:
            schema_value = ModelSchemaValue.from_value(value)
        return self.set_field(f"results.{key}", schema_value)

    def set_metadata_value(
        self, key: str, value: PrimitiveValueType | ModelSchemaValue
    ) -> bool:
        """Set metadata value in metadata field. Accepts raw values or ModelSchemaValue."""
        if isinstance(value, ModelSchemaValue):
            schema_value = value
        else:
            schema_value = ModelSchemaValue.from_value(value)
        return self.set_field(f"metadata.{key}", schema_value)


# Export for use
__all__ = ["ModelResultAccessor"]
