"""
Strongly typed scalar value models.

Replaces Union[str, int, float, bool] patterns with discriminated Pydantic models
for better type safety and validation.
"""

from enum import Enum
from typing import Literal, Union

from pydantic import BaseModel, Field, model_validator


class ScalarType(str, Enum):
    """Enumeration of scalar value types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"


class ModelStringValue(BaseModel):
    """String scalar value."""

    type: Literal["string"] = Field(default="string", description="Value type discriminator")
    value: str = Field(..., description="String value")


class ModelIntegerValue(BaseModel):
    """Integer scalar value."""

    type: Literal["integer"] = Field(default="integer", description="Value type discriminator")
    value: int = Field(..., description="Integer value")


class ModelFloatValue(BaseModel):
    """Float scalar value."""

    type: Literal["float"] = Field(default="float", description="Value type discriminator")
    value: float = Field(..., description="Float value")


class ModelBooleanValue(BaseModel):
    """Boolean scalar value."""

    type: Literal["boolean"] = Field(default="boolean", description="Value type discriminator")
    value: bool = Field(..., description="Boolean value")


# Discriminated union for scalar values
ModelScalarValue = Union[
    ModelStringValue,
    ModelIntegerValue,
    ModelFloatValue,
    ModelBooleanValue,
]


class ModelScalarValueWrapper(BaseModel):
    """
    Wrapper for scalar values with automatic type detection.
    
    This model automatically determines the correct scalar type based on the input value.
    Replaces: Union[str, int, float, bool]
    """

    scalar: ModelScalarValue = Field(..., discriminator="type")

    @classmethod
    def from_value(cls, value: Union[str, int, float, bool]) -> "ModelScalarValueWrapper":
        """Create a wrapper from a raw scalar value."""
        if isinstance(value, bool):
            # Check bool before int because bool is a subclass of int
            return cls(scalar=ModelBooleanValue(value=value))
        elif isinstance(value, int):
            return cls(scalar=ModelIntegerValue(value=value))
        elif isinstance(value, float):
            return cls(scalar=ModelFloatValue(value=value))
        elif isinstance(value, str):
            return cls(scalar=ModelStringValue(value=value))
        else:
            raise ValueError(f"Unsupported scalar type: {type(value)}")

    def get_value(self) -> Union[str, int, float, bool]:
        """Extract the raw scalar value."""
        return self.scalar.value

    def get_type(self) -> ScalarType:
        """Get the scalar type."""
        return ScalarType(self.scalar.type)