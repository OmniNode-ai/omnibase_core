"""
ModelCustomSecuritySettings: Custom security settings model.

This model provides structured custom security settings without using Any types.
"""

from pydantic import BaseModel, Field

# Type alias for security setting values stored in this model.
# Intentionally constrained to exactly the types this model stores:
# - str, int, bool: Basic setting types
# - list[str]: List of strings (e.g., allowed origins, permissions)
# - None: For missing settings (default return)
#
# This is more precise than JsonPrimitive (excludes float) or
# ToolParameterValue (excludes None, includes dict[str, str]).
# union-ok: domain-specific type alias for security settings
SecuritySettingValue = str | int | bool | list[str] | None


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

    def add_setting(self, key: str, value: SecuritySettingValue) -> None:
        """Add a custom security setting with automatic type detection.

        Note: bool check must come before int check because bool is a subclass of int.
        """
        if value is None:
            # None values are valid but not stored - use get_setting's default
            return
        if isinstance(value, bool):
            self.boolean_settings[key] = value
        elif isinstance(value, str):
            self.string_settings[key] = value
        elif isinstance(value, int):
            self.integer_settings[key] = value
        elif isinstance(value, list):
            self.list_settings[key] = value

    def get_setting(
        self, key: str, default: SecuritySettingValue = None
    ) -> SecuritySettingValue:
        """Get a custom security setting.

        Args:
            key: The setting key to retrieve.
            default: Default value if setting not found. Must be a valid
                SecuritySettingValue (str, int, bool, list[str], or None).

        Returns:
            The setting value from the appropriate typed dictionary,
            or the default value if not found.
        """
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
        """Convert to dictionary for current standards."""
        return {
            **self.string_settings,
            **self.integer_settings,
            **self.boolean_settings,
            **self.list_settings,
        }
