"""
YAML configuration section models.

Provides typed models for common YAML configuration sections,
replacing dict[str, Any] patterns in YAML configuration models.
"""

from pydantic import BaseModel, Field


class ModelYamlSection(BaseModel):
    """
    Typed model for YAML configuration sections.

    Replaces dict[str, Any] config/settings/options/parameters fields
    with strongly-typed string key-value pairs.
    """

    # Typed string properties
    string_values: dict[str, str] = Field(
        default_factory=dict,
        description="String configuration values",
    )
    int_values: dict[str, int] = Field(
        default_factory=dict,
        description="Integer configuration values",
    )
    float_values: dict[str, float] = Field(
        default_factory=dict,
        description="Float configuration values",
    )
    bool_values: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean configuration values",
    )
    list_values: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List of strings configuration values",
    )

    def get_string(self, key: str, default: str = "") -> str:
        """Get a string value by key."""
        return self.string_values.get(key, default)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get an integer value by key."""
        return self.int_values.get(key, default)

    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get a float value by key."""
        return self.float_values.get(key, default)

    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get a boolean value by key."""
        return self.bool_values.get(key, default)

    def get_list(self, key: str) -> list[str]:
        """Get a list value by key."""
        return self.list_values.get(key, [])


__all__ = ["ModelYamlSection"]
