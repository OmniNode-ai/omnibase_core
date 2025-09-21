"""
Result field accessor for CLI results and output data.

Specialized accessor for handling CLI execution results and metadata.
"""

from __future__ import annotations

from typing import cast

from .model_field_accessor import ModelFieldAccessor


class ModelResultAccessor(ModelFieldAccessor):
    """Specialized accessor for CLI results and output data."""

    def get_result_value(
        self, key: str, default: str | int | bool | float | None = None
    ) -> str | int | bool | float | None:
        """Get result value from results or metadata fields."""
        # Try results first
        value = self.get_field(f"results.{key}")
        if value is not None and isinstance(value, (str, int, bool, float)):
            return value

        # Try metadata second
        value = self.get_field(f"metadata.{key}")
        if value is not None and isinstance(value, (str, int, bool, float)):
            return value

        return default

    def set_result_value(self, key: str, value: str | int | bool | float) -> bool:
        """Set result value in results field."""
        return self.set_field(f"results.{key}", value)

    def set_metadata_value(self, key: str, value: str | int | bool) -> bool:
        """Set metadata value in metadata field."""
        return self.set_field(f"metadata.{key}", value)


# Export for use
__all__ = ["ModelResultAccessor"]
