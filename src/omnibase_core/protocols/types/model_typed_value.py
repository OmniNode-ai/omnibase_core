"""
Strongly-typed Pydantic models for handling typed values.

Replaces Union[str, int, float, bool, dict, list] patterns with
discriminated union models for better type safety.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, field_validator


class ValueType(str, Enum):
    """Enumeration of supported value types."""
    
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATETIME = "datetime"
    LIST = "list"
    DICT = "dict"
    NULL = "null"


class ModelStringValue(BaseModel):
    """Model for string values."""
    
    type: Literal[ValueType.STRING] = ValueType.STRING
    value: str = Field(..., description="String value")


class ModelIntegerValue(BaseModel):
    """Model for integer values."""
    
    type: Literal[ValueType.INTEGER] = ValueType.INTEGER
    value: int = Field(..., description="Integer value")


class ModelFloatValue(BaseModel):
    """Model for float values."""
    
    type: Literal[ValueType.FLOAT] = ValueType.FLOAT
    value: float = Field(..., description="Float value")


class ModelBooleanValue(BaseModel):
    """Model for boolean values."""
    
    type: Literal[ValueType.BOOLEAN] = ValueType.BOOLEAN
    value: bool = Field(..., description="Boolean value")


class ModelDateTimeValue(BaseModel):
    """Model for datetime values."""
    
    type: Literal[ValueType.DATETIME] = ValueType.DATETIME
    value: datetime = Field(..., description="DateTime value")
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ModelListValue(BaseModel):
    """Model for list values."""
    
    type: Literal[ValueType.LIST] = ValueType.LIST
    value: list[Any] = Field(..., description="List value")
    
    @field_validator('value')
    @classmethod
    def validate_list(cls, v: Any) -> list:
        """Ensure value is a list."""
        if not isinstance(v, list):
            raise ValueError(f"Expected list, got {type(v)}")
        return v


class ModelDictValue(BaseModel):
    """Model for dictionary values."""
    
    type: Literal[ValueType.DICT] = ValueType.DICT
    value: dict[str, Any] = Field(..., description="Dictionary value")
    
    @field_validator('value')
    @classmethod
    def validate_dict(cls, v: Any) -> dict:
        """Ensure value is a dict."""
        if not isinstance(v, dict):
            raise ValueError(f"Expected dict, got {type(v)}")
        return v


class ModelNullValue(BaseModel):
    """Model for null values."""
    
    type: Literal[ValueType.NULL] = ValueType.NULL
    value: None = Field(None, description="Null value")


# Discriminated union for all value types
ModelTypedValue = Union[
    ModelStringValue,
    ModelIntegerValue,
    ModelFloatValue,
    ModelBooleanValue,
    ModelDateTimeValue,
    ModelListValue,
    ModelDictValue,
    ModelNullValue
]


class ModelTypedValueWrapper(BaseModel):
    """
    Wrapper model that automatically determines the correct typed value model.
    
    This provides a convenient way to create typed values without manually
    specifying the type.
    """
    
    value: Any = Field(..., description="The value to wrap")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")
    
    def to_typed_value(self) -> ModelTypedValue:
        """Convert to the appropriate typed value model."""
        if self.value is None:
            return ModelNullValue(value=None)
        elif isinstance(self.value, bool):
            return ModelBooleanValue(value=self.value)
        elif isinstance(self.value, int):
            return ModelIntegerValue(value=self.value)
        elif isinstance(self.value, float):
            return ModelFloatValue(value=self.value)
        elif isinstance(self.value, str):
            return ModelStringValue(value=self.value)
        elif isinstance(self.value, datetime):
            return ModelDateTimeValue(value=self.value)
        elif isinstance(self.value, list):
            return ModelListValue(value=self.value)
        elif isinstance(self.value, dict):
            return ModelDictValue(value=self.value)
        else:
            raise ValueError(f"Unsupported value type: {type(self.value)}")
    
    @classmethod
    def from_raw(cls, value: Any, metadata: dict[str, Any] | None = None) -> "ModelTypedValueWrapper":
        """Create a typed value wrapper from a raw value."""
        return cls(value=value, metadata=metadata or {})