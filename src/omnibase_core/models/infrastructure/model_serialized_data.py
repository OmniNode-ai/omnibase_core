"""
Serialized Data Model.

Strongly-typed model for serialization results, replacing dict[str, Any]
return types in serialize() methods.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_schema_value import ModelSchemaValue


class ModelSerializedData(BaseModel):
    """
    Typed model for serialized data.

    Replaces dict[str, Any] return type in serialize() methods.
    Uses ModelSchemaValue for proper type safety while maintaining
    JSON compatibility.
    """

    # Store serialized fields using typed values
    fields: dict[str, ModelSchemaValue] = Field(
        default_factory=dict,
        description="Serialized fields as typed schema values",
    )

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )

    @classmethod
    def from_model_dump(cls, data: dict[str, object]) -> ModelSerializedData:
        """Create from a Pydantic model_dump() result."""
        fields = {
            key: ModelSchemaValue.from_value(value) for key, value in data.items()
        }
        return cls(fields=fields)

    def to_dict(self) -> dict[str, object]:
        """Convert back to plain dictionary for JSON serialization."""
        return {key: value.to_value() for key, value in self.fields.items()}

    def get(self, key: str, default: object = None) -> object:
        """Get a field value by key."""
        schema_value = self.fields.get(key)
        if schema_value is None:
            return default
        return schema_value.to_value()

    def __contains__(self, key: str) -> bool:
        """Check if a field exists."""
        return key in self.fields


__all__ = ["ModelSerializedData"]
