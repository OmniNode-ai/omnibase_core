from typing import Any, Optional

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_schema import ModelSchema


class ModelTypedProperties(BaseModel):
    """
    DEPRECATED: Modern standards wrapper.

    This class is maintained for current standards only.
    New code should use ModelSchema.properties directly.
    """

    properties: dict[str, ModelSchema] = Field(
        default_factory=dict,
        description="Property definitions with full type information",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to legacy dict[str, Any]format for current standards."""
        return {name: prop.to_dict() for name, prop in self.properties.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Optional["ModelTypedProperties"]:
        """Create from legacy dict[str, Any]ionary format."""
        if data is None:
            return None

        properties = {}
        for name, prop_data in data.items():
            if isinstance(prop_data, dict):
                schema = ModelSchema.from_dict(prop_data)
                if schema is not None:
                    properties[name] = schema

        return cls(properties=properties)
