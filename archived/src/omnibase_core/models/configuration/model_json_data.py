"""
ONEX-Compliant JSON Data Model for Configuration System

Phase 3I remediation: Eliminated factory methods and conversion anti-patterns.
Strong typing with generic container patterns following ONEX standards.
"""

from enum import Enum
from typing import Any, Union

from pydantic import BaseModel, Field, validator


class JsonValueType(str, Enum):
    """ONEX-compliant JSON value type enumeration."""

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    NULL = "null"


class ModelJsonField(BaseModel):
    """
    ONEX-compliant strongly typed JSON field with protocol constraints.

    Uses discriminated union pattern for type safety without factory methods.
    """

    field_type: JsonValueType = Field(
        ...,
        description="JSON field value type",
    )

    # Union field with strong typing - exactly one will be set based on field_type
    string_value: str | None = Field(
        default=None,
        description="String value when field_type=STRING",
        min_length=0,
        max_length=10000,
    )

    number_value: float | None = Field(
        default=None,
        description="Number value when field_type=NUMBER",
    )

    boolean_value: bool | None = Field(
        default=None,
        description="Boolean value when field_type=BOOLEAN",
    )

    array_values: list[str] | None = Field(
        None,
        description="Array values when field_type=ARRAY",
    )

    # ONEX validation constraints
    @validator("string_value")
    def validate_string_type_consistency(cls, v, values):
        """Ensure string_value is set only when field_type=STRING."""
        field_type = values.get("field_type")
        if field_type == JsonValueType.STRING and v is None:
            raise ValueError("string_value must be provided when field_type=STRING")
        if field_type != JsonValueType.STRING and v is not None:
            raise ValueError(f"string_value must be None when field_type={field_type}")
        return v

    @validator("number_value")
    def validate_number_type_consistency(cls, v, values):
        """Ensure number_value is set only when field_type=NUMBER."""
        field_type = values.get("field_type")
        if field_type == JsonValueType.NUMBER and v is None:
            raise ValueError("number_value must be provided when field_type=NUMBER")
        if field_type != JsonValueType.NUMBER and v is not None:
            raise ValueError(f"number_value must be None when field_type={field_type}")
        return v

    @validator("boolean_value")
    def validate_boolean_type_consistency(cls, v, values):
        """Ensure boolean_value is set only when field_type=BOOLEAN."""
        field_type = values.get("field_type")
        if field_type == JsonValueType.BOOLEAN and v is None:
            raise ValueError("boolean_value must be provided when field_type=BOOLEAN")
        if field_type != JsonValueType.BOOLEAN and v is not None:
            raise ValueError(f"boolean_value must be None when field_type={field_type}")
        return v

    @validator("array_values")
    def validate_array_type_consistency(cls, v, values):
        """Ensure array_values is set only when field_type=ARRAY."""
        field_type = values.get("field_type")
        if field_type == JsonValueType.ARRAY and v is None:
            raise ValueError("array_values must be provided when field_type=ARRAY")
        if field_type != JsonValueType.ARRAY and v is not None:
            raise ValueError(f"array_values must be None when field_type={field_type}")
        return v

    def get_typed_value(self) -> Union[str, float, bool, list[str], None]:
        """ONEX-compliant value accessor with strong typing."""
        match self.field_type:
            case JsonValueType.STRING:
                return self.string_value
            case JsonValueType.NUMBER:
                return self.number_value
            case JsonValueType.BOOLEAN:
                return self.boolean_value
            case JsonValueType.ARRAY:
                return self.array_values
            case JsonValueType.NULL:
                return None
            case _:
                raise ValueError(f"Unknown field_type: {self.field_type}")


class ModelJsonData(BaseModel):
    """
    ONEX-compliant strongly typed JSON data model.

    Provides structured JSON data handling with proper constructor patterns
    and immutable design following ONEX standards.
    """

    fields: dict[str, ModelJsonField] = Field(
        default_factory=dict,
        description="Strongly typed JSON fields with ONEX compliance",
    )

    # Optional metadata for validation and context
    schema_version: str = Field(
        default="1.0",
        description="JSON data schema version",
        pattern="^\\d+\\.\\d+$",
    )

    total_field_count: int = Field(
        default=0,
        description="Total number of fields for validation",
        ge=0,
    )

    # ONEX validation constraints
    @validator("fields")
    def validate_field_consistency(cls, v, values):
        """Ensure field count matches actual fields."""
        if len(v) != values.get("total_field_count", 0):
            raise ValueError(
                f"Field count mismatch: expected {values.get('total_field_count', 0)}, got {len(v)}"
            )
        return v

    @validator("total_field_count", pre=True, always=True)
    def calculate_field_count(cls, v, values):
        """Auto-calculate field count for validation."""
        fields = values.get("fields", {})
        return len(fields) if isinstance(fields, dict) else v

    def get_field_value(
        self, field_name: str
    ) -> Union[str, float, bool, list[str], None]:
        """ONEX-compliant field value accessor."""
        if field_name not in self.fields:
            raise KeyError(f"Field '{field_name}' not found")
        return self.fields[field_name].get_typed_value()

    def has_field(self, field_name: str) -> bool:
        """Check if field exists in the JSON data."""
        return field_name in self.fields

    def get_field_type(self, field_name: str) -> JsonValueType:
        """Get the type of a specific field."""
        if field_name not in self.fields:
            raise KeyError(f"Field '{field_name}' not found")
        return self.fields[field_name].field_type
