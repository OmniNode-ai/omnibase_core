"""
Generic properties model to replace Dict[str, Any] usage for properties fields.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.types import PropertyValue


class ModelGenericProperties(BaseModel):
    """
    Generic properties container with typed fields.
    Replaces Dict[str, Any] for properties fields across the codebase.
    """

    # String properties (most common)
    string_properties: dict[str, str] = Field(
        default_factory=dict,
        description="String key-value properties",
    )

    # Numeric properties
    numeric_properties: dict[str, int | float] = Field(
        default_factory=dict,
        description="Numeric key-value properties",
    )

    # Boolean flags
    boolean_properties: dict[str, bool] = Field(
        default_factory=dict,
        description="Boolean key-value properties",
    )

    # List properties
    list_properties: dict[str, list[str]] = Field(
        default_factory=dict,
        description="List-valued properties",
    )

    # Nested properties (for complex cases)
    nested_properties: dict[str, dict[str, str]] = Field(
        default_factory=dict,
        description="Nested key-value properties",
    )

    model_config = ConfigDict(extra="forbid")  # Strict validation

    def to_dict(self) -> dict[str, PropertyValue]:
        """Convert to flat dictionary for backward compatibility."""
        # Custom flattening logic for backward compatibility
        result = {}
        result.update(self.string_properties)
        result.update(self.numeric_properties)
        result.update(self.boolean_properties)
        result.update(self.list_properties)
        result.update(self.nested_properties)
        return result

    @classmethod
    def from_dict(
        cls,
        data: dict[str, PropertyValue] | None,
    ) -> Optional["ModelGenericProperties"]:
        """Create from dictionary with type inference."""
        if data is None:
            return None

        obj = cls()
        for key, value in data.items():
            if isinstance(value, str):
                obj.string_properties[key] = value
            elif isinstance(value, bool):
                obj.boolean_properties[key] = value
            elif isinstance(value, int | float):
                obj.numeric_properties[key] = value
            elif isinstance(value, list) and all(isinstance(v, str) for v in value):
                obj.list_properties[key] = value
            elif isinstance(value, dict) and all(
                isinstance(v, str) for v in value.values()
            ):
                obj.nested_properties[key] = value

        return obj

    def get(
        self, key: str, default: PropertyValue | None = None
    ) -> PropertyValue | None:
        """Get property value by key."""
        for prop_dict in [
            self.string_properties,
            self.numeric_properties,
            self.boolean_properties,
            self.list_properties,
            self.nested_properties,
        ]:
            if key in prop_dict:
                return prop_dict[key]
        return default
