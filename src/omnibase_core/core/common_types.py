"""
Common types for ONEX core modules.

Strong typing patterns for ONEX architecture compliance.
"""

from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, field_validator

# Type aliases to reduce union usage
ScalarPrimitive = Union[str, int, float, bool]
OptionalScalarPrimitive = Optional[ScalarPrimitive]


class ModelScalarValue(BaseModel):
    """Strongly typed scalar value for message data and metadata."""

    value: ScalarPrimitive = Field(..., description="The scalar value")

    @property
    def type_hint(self) -> str:
        """Auto-generated type hint based on the actual value type."""
        return type(self.value).__name__

    @classmethod
    def create_string(cls, value: str) -> "ModelScalarValue":
        """Create a string scalar value."""
        return cls(value=value)

    @classmethod
    def create_int(cls, value: int) -> "ModelScalarValue":
        """Create an integer scalar value."""
        return cls(value=value)

    @classmethod
    def create_float(cls, value: float) -> "ModelScalarValue":
        """Create a float scalar value."""
        return cls(value=value)

    @classmethod
    def create_bool(cls, value: bool) -> "ModelScalarValue":
        """Create a boolean scalar value."""
        return cls(value=value)

    @classmethod
    def from_primitive(cls, value: ScalarPrimitive) -> "ModelScalarValue":
        """Migration helper for existing primitive values."""
        return cls(value=value)

    def to_primitive(self) -> ScalarPrimitive:
        """Extract primitive value for backward compatibility."""
        return self.value


class ModelStateValue(BaseModel):
    """Strongly typed state value with optional nested structure."""

    scalar_value: OptionalScalarPrimitive = Field(
        None, description="Simple scalar value"
    )
    dict_value: Optional[Dict[str, Any]] = Field(None, description="Dictionary value")
    is_null: bool = Field(False, description="Whether this represents a null value")

    @field_validator("scalar_value", "dict_value", "is_null")
    @classmethod
    def validate_only_one_value_type(cls, v, info):
        """Ensure only one value type is set at a time."""
        if info.context is None:
            return v

        # During validation, check that only one value is provided
        values = info.data or {}
        value_count = sum(
            [
                values.get("scalar_value") is not None,
                values.get("dict_value") is not None,
                values.get("is_null", False),
            ]
        )

        # Allow exactly one value type to be set
        if value_count > 1:
            raise ValueError(
                "ModelStateValue can only have one of: scalar_value, dict_value, or is_null=True"
            )

        return v

    @classmethod
    def create_scalar(cls, value: ScalarPrimitive) -> "ModelStateValue":
        """Create a state value from a scalar."""
        return cls(scalar_value=value)

    @classmethod
    def create_dict(cls, value: Dict[str, Any]) -> "ModelStateValue":
        """Create a state value from a dictionary."""
        return cls(dict_value=value)

    @classmethod
    def create_null(cls) -> "ModelStateValue":
        """Create a null state value."""
        return cls(is_null=True)

    def get_value(self) -> Union[ScalarPrimitive, Dict[str, Any], None]:
        """Get the actual value, regardless of type."""
        if self.is_null:
            return None
        if self.scalar_value is not None:
            return self.scalar_value
        if self.dict_value is not None:
            return self.dict_value
        return None


# Legacy alias for backward compatibility
ScalarValue = ModelScalarValue
