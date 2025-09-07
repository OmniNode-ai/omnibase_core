"""
Strongly typed state value models.

Replaces Union[str, int, float, bool, Dict[str, Any], None] patterns
with discriminated Pydantic models for better type safety.
"""

from enum import Enum
from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_scalar_value import (
    ModelBooleanValue,
    ModelFloatValue,
    ModelIntegerValue,
    ModelStringValue,
)


class StateValueType(str, Enum):
    """Enumeration of state value types."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    OBJECT = "object"
    NULL = "null"


class ModelObjectValue(BaseModel):
    """Object/dictionary state value."""

    type: Literal["object"] = Field(default="object", description="Value type discriminator")
    value: Dict[str, Any] = Field(..., description="Object value")


class ModelNullValue(BaseModel):
    """Null state value."""

    type: Literal["null"] = Field(default="null", description="Value type discriminator")
    value: None = Field(default=None, description="Null value")


# Discriminated union for state values
ModelStateValue = Union[
    ModelStringValue,
    ModelIntegerValue,
    ModelFloatValue,
    ModelBooleanValue,
    ModelObjectValue,
    ModelNullValue,
]


class ModelStateValueWrapper(BaseModel):
    """
    Wrapper for state values with automatic type detection.
    
    This model automatically determines the correct state value type based on input.
    Replaces: Union[str, int, float, bool, Dict[str, Any], None]
    """

    state: ModelStateValue = Field(..., discriminator="type")

    @classmethod
    def from_value(
        cls, value: Union[str, int, float, bool, Dict[str, Any], None]
    ) -> "ModelStateValueWrapper":
        """Create a wrapper from a raw state value."""
        if value is None:
            return cls(state=ModelNullValue())
        elif isinstance(value, bool):
            # Check bool before int because bool is a subclass of int
            return cls(state=ModelBooleanValue(value=value))
        elif isinstance(value, int):
            return cls(state=ModelIntegerValue(value=value))
        elif isinstance(value, float):
            return cls(state=ModelFloatValue(value=value))
        elif isinstance(value, str):
            return cls(state=ModelStringValue(value=value))
        elif isinstance(value, dict):
            return cls(state=ModelObjectValue(value=value))
        else:
            raise ValueError(f"Unsupported state value type: {type(value)}")

    def get_value(self) -> Union[str, int, float, bool, Dict[str, Any], None]:
        """Extract the raw state value."""
        if isinstance(self.state, ModelNullValue):
            return None
        return self.state.value

    def get_type(self) -> StateValueType:
        """Get the state value type."""
        return StateValueType(self.state.type)

    def is_null(self) -> bool:
        """Check if the value is null."""
        return isinstance(self.state, ModelNullValue)

    def is_scalar(self) -> bool:
        """Check if the value is a scalar (not object or null)."""
        return self.state.type in ["string", "integer", "float", "boolean"]

    def is_object(self) -> bool:
        """Check if the value is an object."""
        return isinstance(self.state, ModelObjectValue)