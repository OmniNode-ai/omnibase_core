"""
Result field accessor for CLI results and output data.

Specialized accessor for handling CLI execution results and metadata.
"""

from __future__ import annotations

from ..common.model_schema_value import ModelSchemaValue
from ..infrastructure.model_result import Result
from .model_field_accessor import ModelFieldAccessor


class ModelResultAccessor(ModelFieldAccessor):
    """Specialized accessor for CLI results and output data."""

    def get_result_value(
        self,
        key: str,
        default: ModelSchemaValue = None,
    ) -> Result[ModelSchemaValue, str]:
        """Get result value from results or metadata fields."""
        # Try results first
        results_value = self.get_field(f"results.{key}")
        if results_value.is_ok():
            return results_value

        # Try metadata second
        metadata_value = self.get_field(f"metadata.{key}")
        if metadata_value.is_ok():
            return metadata_value

        # If both failed, return default if provided, otherwise error
        if default is not None:
            return Result.ok(default)
        return Result.err(f"Result value '{key}' not found in results or metadata")

    def set_result_value(self, key: str, value: ModelSchemaValue) -> bool:
        """Set result value in results field."""
        return self.set_field(f"results.{key}", value)

    def set_metadata_value(self, key: str, value: ModelSchemaValue) -> bool:
        """Set metadata value in metadata field."""
        return self.set_field(f"metadata.{key}", value)


# Export for use
__all__ = ["ModelResultAccessor"]
