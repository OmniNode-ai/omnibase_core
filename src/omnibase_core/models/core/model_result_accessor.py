"""
Result field accessor for CLI results and output data.

Specialized accessor for handling CLI execution results and metadata.
"""

from __future__ import annotations

from typing import cast

from ..common.model_schema_value import ModelSchemaValue
from .model_field_accessor import ModelFieldAccessor


class ModelResultAccessor(ModelFieldAccessor):
    """Specialized accessor for CLI results and output data."""

    def get_result_value(
        self, key: str, default: ModelSchemaValue | None = None
    ) -> ModelSchemaValue | None:
        """Get result value from results or metadata fields."""
        # Try results first
        value = self.get_field(f"results.{key}")
        if value is not None:
            return value

        # Try metadata second
        value = self.get_field(f"metadata.{key}")
        if value is not None:
            return value

        return default

    def set_result_value(self, key: str, value: ModelSchemaValue) -> bool:
        """Set result value in results field."""
        return self.set_field(f"results.{key}", value)

    def set_metadata_value(self, key: str, value: ModelSchemaValue) -> bool:
        """Set metadata value in metadata field."""
        return self.set_field(f"metadata.{key}", value)


# Export for use
__all__ = ["ModelResultAccessor"]
