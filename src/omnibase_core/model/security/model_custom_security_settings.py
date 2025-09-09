"""
ModelCustomSecuritySettings: Custom security settings model.

This model provides structured custom security settings without using Any types.
"""

from pydantic import BaseModel, Field


class ModelCustomSecuritySettings(BaseModel):
    """Custom security settings model."""

    string_settings: dict[str, str] = Field(
        default_factory=dict,
        description="String security settings",
    )
    integer_settings: dict[str, int] = Field(
        default_factory=dict,
        description="Integer security settings",
    )
    boolean_settings: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean security settings",
    )
    list_settings: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List security settings",
    )

    def add_setting(self, key: str, value) -> None:
        """Add a custom security setting with automatic type detection."""
        if isinstance(value, str):
            self.string_settings[key] = value
        elif isinstance(value, int):
            self.integer_settings[key] = value
        elif isinstance(value, bool):
            self.boolean_settings[key] = value
        elif isinstance(value, list) and all(isinstance(item, str) for item in value):
            self.list_settings[key] = value
        else:
            # Default to string representation for unknown types
            self.string_settings[key] = str(value)

    def get_setting(self, key: str, default=None):
        """Get a custom security setting."""
        if key in self.string_settings:
            return self.string_settings[key]
        if key in self.integer_settings:
            return self.integer_settings[key]
        if key in self.boolean_settings:
            return self.boolean_settings[key]
        if key in self.list_settings:
            return self.list_settings[key]
        return default

    def has_setting(self, key: str) -> bool:
        """Check if a setting exists."""
        return (
            key in self.string_settings
            or key in self.integer_settings
            or key in self.boolean_settings
            or key in self.list_settings
        )

    def to_dict(self) -> dict[str, object]:
        """Convert to dictionary for backwards compatibility."""
        # Custom flattening logic for security settings
        result = {}
        result.update(self.string_settings)
        result.update(self.integer_settings)
        result.update(self.boolean_settings)
        result.update(self.list_settings)
        return result
