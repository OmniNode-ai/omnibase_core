"""
Common types for ONEX core modules.

Strong typing patterns for ONEX architecture compliance.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class ModelScalarValue(BaseModel):
    """Strongly typed scalar value for message data and metadata."""
    
    value: str | int | float | bool = Field(..., description="The scalar value")
    type_hint: str = Field(..., description="Type of the scalar value")

    @classmethod
    def create_string(cls, value: str) -> "ModelScalarValue":
        """Create a string scalar value."""
        return cls(value=value, type_hint="str")
    
    @classmethod
    def create_int(cls, value: int) -> "ModelScalarValue":
        """Create an integer scalar value."""
        return cls(value=value, type_hint="int")
    
    @classmethod
    def create_float(cls, value: float) -> "ModelScalarValue":
        """Create a float scalar value."""
        return cls(value=value, type_hint="float")
    
    @classmethod
    def create_bool(cls, value: bool) -> "ModelScalarValue":
        """Create a boolean scalar value."""
        return cls(value=value, type_hint="bool")


class ModelStateValue(BaseModel):
    """Strongly typed state value with optional nested structure."""
    
    scalar_value: Optional[str | int | float | bool] = Field(None, description="Simple scalar value")
    dict_value: Optional[Dict[str, Any]] = Field(None, description="Dictionary value")
    is_null: bool = Field(False, description="Whether this represents a null value")
    
    @classmethod
    def create_scalar(cls, value: str | int | float | bool) -> "ModelStateValue":
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
    
    def get_value(self) -> str | int | float | bool | Dict[str, Any] | None:
        """Get the actual value, regardless of type."""
        if self.is_null:
            return None
        if self.scalar_value is not None:
            return self.scalar_value
        if self.dict_value is not None:
            return self.dict_value
        return None


# Legacy aliases for backward compatibility - will be deprecated
ScalarValue = ModelScalarValue
