"""
Environment field accessor with type coercion.

Specialized accessor for environment properties with automatic type conversion.
"""

from .model_field_accessor import ModelFieldAccessor


class ModelEnvironmentAccessor(ModelFieldAccessor):
    """Specialized accessor for environment properties with type coercion."""

    def get_string(self, path: str, default: str = "") -> str:
        """Get string value with type coercion."""
        value = self.get_field(path, default)
        return str(value) if value is not None else default

    def get_int(self, path: str, default: int = 0) -> int:
        """Get integer value with type coercion."""
        value = self.get_field(path, default)
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and value.isdigit()
        ):
            return int(value)
        return default

    def get_float(self, path: str, default: float = 0.0) -> float:
        """Get float value with type coercion."""
        value = self.get_field(path, default)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    def get_bool(self, path: str, default: bool = False) -> bool:
        """Get boolean value with type coercion."""
        value = self.get_field(path, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ["true", "yes", "1", "on", "enabled"]
        if isinstance(value, (int, float)):
            return bool(value)
        return default

    def get_list(self, path: str, default: list[str] | None = None) -> list[str]:
        """Get list value with type coercion."""
        if default is None:
            default = []
        value = self.get_field(path, default)
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            # Support comma-separated values
            return [item.strip() for item in value.split(",") if item.strip()]
        return default


# Export for use
__all__ = ["ModelEnvironmentAccessor"]
