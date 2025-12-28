"""
Generic properties model to replace Dict[str, Any] usage for properties fields.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.types import PropertyValue


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
        """Convert to flat dictionary for current standards."""
        # Custom flattening logic for current standards
        result: dict[str, PropertyValue] = {}
        result.update(self.string_properties)
        result.update(self.numeric_properties)
        result.update(self.boolean_properties)
        result.update(self.list_properties)
        result.update(self.nested_properties)
        return result

    @classmethod
    def from_flat_dict(
        cls, data: dict[str, PropertyValue] | None
    ) -> ModelGenericProperties | None:
        """
        Create ModelGenericProperties from flat dictionary with automatic type categorization.

        Uses proper Pydantic validation and construction patterns.
        This replaces the old from_dict() factory method with ONEX-compatible implementation.

        Args:
            data: Flat dictionary with mixed property types, or None

        Returns:
            ModelGenericProperties instance or None if data is None

        Example:
            >>> props = ModelGenericProperties.from_flat_dict({
            ...     "name": "example",
            ...     "count": 42,
            ...     "enabled": True,
            ...     "tags": ["a", "b", "c"],
            ...     "config": {"key": "value"}
            ... })
        """
        if data is None:
            return None

        # Categorize properties by type
        categorized_data = cls._categorize_properties(data)

        # Use Pydantic's model_validate for proper validation
        return cls.model_validate(categorized_data)

    @staticmethod
    def _categorize_properties(
        data: dict[str, PropertyValue],
    ) -> dict[str, dict[str, PropertyValue]]:
        """
        Categorize mixed property data into typed property dict[str, Any]ionaries.

        This is a helper method that automatically sorts properties by type
        for use with the typed property fields.
        """
        categorized: dict[str, dict[str, PropertyValue]] = {
            "string_properties": {},
            "numeric_properties": {},
            "boolean_properties": {},
            "list_properties": {},
            "nested_properties": {},
        }

        for key, value in data.items():
            if isinstance(value, str):
                categorized["string_properties"][key] = value
            elif isinstance(value, bool):
                categorized["boolean_properties"][key] = value
            elif isinstance(value, (int, float)):
                categorized["numeric_properties"][key] = value
            elif isinstance(value, list) and all(isinstance(v, str) for v in value):
                categorized["list_properties"][key] = value
            elif isinstance(value, dict) and all(
                isinstance(v, str) for v in value.values()
            ):
                categorized["nested_properties"][key] = value

        return categorized

    def get(
        self, key: str, default: PropertyValue | None = None
    ) -> PropertyValue | None:
        """Get property value by key."""
        # Check each property dict[str, Any]individually due to type constraints
        if key in self.string_properties:
            return self.string_properties[key]
        if key in self.numeric_properties:
            return self.numeric_properties[key]
        if key in self.boolean_properties:
            return self.boolean_properties[key]
        if key in self.list_properties:
            return self.list_properties[key]
        if key in self.nested_properties:
            return self.nested_properties[key]
        return default
