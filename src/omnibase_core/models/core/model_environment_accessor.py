"""
Environment field accessor with type coercion.

Specialized accessor for environment properties with automatic type conversion.
"""

from __future__ import annotations

from ..common.model_schema_value import ModelSchemaValue
from .model_field_accessor import ModelFieldAccessor


class ModelEnvironmentAccessor(ModelFieldAccessor):
    """Specialized accessor for environment properties with type coercion."""

    def get_string(self, path: str, default: str = "") -> str:
        """Get string value with type coercion."""
        schema_default = ModelSchemaValue.from_value(default)
        result = self.get_field(path, schema_default)
        if result.is_ok():
            value = result.unwrap()
            raw_value = value.to_value()
            return str(raw_value) if raw_value is not None else default
        return default

    def get_int(self, path: str, default: int = 0) -> int:
        """Get integer value with type coercion."""
        schema_default = ModelSchemaValue.from_value(default)
        result = self.get_field(path, schema_default)
        if result.is_ok():
            value = result.unwrap()
            raw_value = value.to_value()
            if isinstance(raw_value, (int, float)) or (
                isinstance(raw_value, str) and raw_value.isdigit()
            ):
                return int(raw_value)
        return default

    def get_float(self, path: str, default: float = 0.0) -> float:
        """Get float value with type coercion."""
        schema_default = ModelSchemaValue.from_value(default)
        result = self.get_field(path, schema_default)
        if result.is_ok():
            value = result.unwrap()
            raw_value = value.to_value()
            if isinstance(raw_value, (int, float)):
                return float(raw_value)
            if isinstance(raw_value, str):
                try:
                    return float(raw_value)
                except ValueError:
                    return default
        return default

    def get_bool(self, path: str, default: bool = False) -> bool:
        """Get boolean value with type coercion."""
        schema_default = ModelSchemaValue.from_value(default)
        result = self.get_field(path, schema_default)
        if result.is_ok():
            value = result.unwrap()
            raw_value = value.to_value()
            if isinstance(raw_value, bool):
                return raw_value
            if isinstance(raw_value, str):
                return raw_value.lower() in ["true", "yes", "1", "on", "enabled"]
            if isinstance(raw_value, (int, float)):
                return bool(raw_value)
        return default

    def get_list(self, path: str, default: list[str] | None = None) -> list[str]:
        """Get list value with type coercion."""
        if default is None:
            default = []
        schema_default = ModelSchemaValue.from_value(default)
        result = self.get_field(path, schema_default)
        if result.is_ok():
            value = result.unwrap()
            raw_value = value.to_value()
            if isinstance(raw_value, list):
                return [str(item) for item in raw_value]
            if isinstance(raw_value, str):
                # Support comma-separated values
                return [item.strip() for item in raw_value.split(",") if item.strip()]
        return default


# Export for use
__all__ = ["ModelEnvironmentAccessor"]
