"""
Scalar Value Model.

Strongly typed scalar value model replacing Union[str, int, float, bool].
"""

from typing import Any, Literal, get_args

from pydantic import BaseModel, Field, field_validator, model_validator


class ModelScalarValue(BaseModel):
    """
    Type-safe scalar value wrapper.

    Provides structured scalar value handling replacing
    Union[str, int, float, bool] with type-safe value container.
    """

    value: str | int | float | bool = Field(..., description="The scalar value")
    value_type: Literal["string", "integer", "float", "boolean"] = Field(
        ..., description="Type of the scalar value"
    )

    @model_validator(mode="before")
    @classmethod
    def set_value_type(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Automatically set value_type based on the value."""
        if "value" in values and "value_type" not in values:
            value = values["value"]
            if isinstance(value, bool):
                values["value_type"] = "boolean"
            elif isinstance(value, int):
                values["value_type"] = "integer"
            elif isinstance(value, float):
                values["value_type"] = "float"
            elif isinstance(value, str):
                values["value_type"] = "string"
        return values

    @field_validator("value_type")
    @classmethod
    def validate_type_match(cls, v: str, info) -> str:
        """Validate that value_type matches the actual value type."""
        if "value" in info.data:
            value = info.data["value"]
            expected_type = None
            if isinstance(value, bool):
                expected_type = "boolean"
            elif isinstance(value, int):
                expected_type = "integer"
            elif isinstance(value, float):
                expected_type = "float"
            elif isinstance(value, str):
                expected_type = "string"

            if expected_type and v != expected_type:
                raise ValueError(
                    f"value_type '{v}' does not match actual type '{expected_type}'"
                )
        return v

    def get_as_string(self) -> str:
        """Get value as string."""
        return str(self.value)

    def get_as_int(self) -> int | None:
        """Get value as integer."""
        if isinstance(self.value, int):
            return self.value
        if isinstance(self.value, bool):
            return 1 if self.value else 0
        if isinstance(self.value, float):
            return int(self.value)
        if isinstance(self.value, str):
            try:
                return int(self.value)
            except ValueError:
                return None
        return None

    def get_as_float(self) -> float | None:
        """Get value as float."""
        if isinstance(self.value, (int, float)):
            return float(self.value)
        if isinstance(self.value, bool):
            return 1.0 if self.value else 0.0
        if isinstance(self.value, str):
            try:
                return float(self.value)
            except ValueError:
                return None
        return None

    def get_as_bool(self) -> bool:
        """Get value as boolean."""
        if isinstance(self.value, bool):
            return self.value
        if isinstance(self.value, str):
            return self.value.lower() in ("true", "yes", "1", "on")
        if isinstance(self.value, (int, float)):
            return self.value != 0
        return False

    def is_numeric(self) -> bool:
        """Check if value is numeric."""
        return self.value_type in ("integer", "float")

    @classmethod
    def from_string(cls, value: str) -> "ModelScalarValue":
        """Create scalar value from string."""
        return cls(value=value, value_type="string")

    @classmethod
    def from_int(cls, value: int) -> "ModelScalarValue":
        """Create scalar value from integer."""
        return cls(value=value, value_type="integer")

    @classmethod
    def from_float(cls, value: float) -> "ModelScalarValue":
        """Create scalar value from float."""
        return cls(value=value, value_type="float")

    @classmethod
    def from_bool(cls, value: bool) -> "ModelScalarValue":
        """Create scalar value from boolean."""
        return cls(value=value, value_type="boolean")

    @classmethod
    def from_any(cls, value: Any) -> "ModelScalarValue":
        """Create scalar value from any supported type."""
        if isinstance(value, bool):
            return cls.from_bool(value)
        elif isinstance(value, int):
            return cls.from_int(value)
        elif isinstance(value, float):
            return cls.from_float(value)
        elif isinstance(value, str):
            return cls.from_string(value)
        else:
            raise ValueError(f"Unsupported type for scalar value: {type(value)}")