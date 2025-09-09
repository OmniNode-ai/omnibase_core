"""
Strongly-Typed Value Models

Discriminated union models to replace generic Union types throughout the codebase.
These models provide type safety, validation, and clear semantics for values
that can be of different types.
"""

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class EnumValueType(str, Enum):
    """Enumeration of supported value types."""

    string = "string"
    integer = "integer"
    float = "float"
    boolean = "boolean"
    datetime = "datetime"
    list_string = "list_string"
    null = "null"
    dict = "dict"
    list = "list"


class ModelStringValue(BaseModel):
    """String value with validation."""

    type: Literal["string"] = "string"
    value: str = Field(..., description="String value")
    
    @field_validator("value")
    @classmethod
    def validate_string(cls, v: str) -> str:
        """Validate string value."""
        if not isinstance(v, str):
            raise ValueError(f"Expected string, got {type(v).__name__}")
        return v


class ModelIntegerValue(BaseModel):
    """Integer value with validation."""

    type: Literal["integer"] = "integer"
    value: int = Field(..., description="Integer value")
    min_value: int | None = Field(None, description="Optional minimum value")
    max_value: int | None = Field(None, description="Optional maximum value")
    
    @model_validator(mode="after")
    def validate_range(self) -> "ModelIntegerValue":
        """Validate value is within range."""
        if self.min_value is not None and self.value < self.min_value:
            raise ValueError(f"Value {self.value} is below minimum {self.min_value}")
        if self.max_value is not None and self.value > self.max_value:
            raise ValueError(f"Value {self.value} is above maximum {self.max_value}")
        return self


class ModelFloatValue(BaseModel):
    """Float value with validation."""

    type: Literal["float"] = "float"
    value: float = Field(..., description="Float value")
    min_value: float | None = Field(None, description="Optional minimum value")
    max_value: float | None = Field(None, description="Optional maximum value")
    precision: int | None = Field(None, description="Optional decimal precision")
    
    @model_validator(mode="after")
    def validate_range_and_precision(self) -> "ModelFloatValue":
        """Validate value is within range and has correct precision."""
        if self.min_value is not None and self.value < self.min_value:
            raise ValueError(f"Value {self.value} is below minimum {self.min_value}")
        if self.max_value is not None and self.value > self.max_value:
            raise ValueError(f"Value {self.value} is above maximum {self.max_value}")
        if self.precision is not None:
            self.value = round(self.value, self.precision)
        return self


class ModelBooleanValue(BaseModel):
    """Boolean value with validation."""

    type: Literal["boolean"] = "boolean"
    value: bool = Field(..., description="Boolean value")


class ModelDateTimeValue(BaseModel):
    """DateTime value with validation."""

    type: Literal["datetime"] = "datetime"
    value: datetime = Field(..., description="DateTime value")
    format: str | None = Field(None, description="Optional datetime format string")
    timezone: str | None = Field(None, description="Optional timezone")


class ModelListStringValue(BaseModel):
    """List of strings with validation."""

    type: Literal["list_string"] = "list_string"
    value: list[str] = Field(..., description="List of string values")
    min_length: int | None = Field(None, description="Minimum list length")
    max_length: int | None = Field(None, description="Maximum list length")
    unique: bool = Field(False, description="Whether values must be unique")
    
    @model_validator(mode="after")
    def validate_list(self) -> "ModelListStringValue":
        """Validate list constraints."""
        if self.min_length is not None and len(self.value) < self.min_length:
            raise ValueError(f"List has {len(self.value)} items, minimum is {self.min_length}")
        if self.max_length is not None and len(self.value) > self.max_length:
            raise ValueError(f"List has {len(self.value)} items, maximum is {self.max_length}")
        if self.unique and len(self.value) != len(set(self.value)):
            raise ValueError("List values must be unique")
        return self


class ModelNullValue(BaseModel):
    """Null value representation."""

    type: Literal["null"] = "null"
    value: None = Field(None, description="Null value")


class ModelDictValue(BaseModel):
    """Dictionary value with recursive typing."""

    type: Literal["dict"] = "dict"
    value: dict[str, Any] = Field(..., description="Dictionary value")
    schema: dict[str, Any] | None = Field(None, description="Optional JSON schema for validation")


class ModelListValue(BaseModel):
    """Generic list value with recursive typing."""

    type: Literal["list"] = "list"
    value: list[Any] = Field(..., description="List value")
    item_type: EnumValueType | None = Field(None, description="Optional type constraint for items")
    min_length: int | None = Field(None, description="Minimum list length")
    max_length: int | None = Field(None, description="Maximum list length")
    
    @model_validator(mode="after")
    def validate_list(self) -> "ModelListValue":
        """Validate list constraints."""
        if self.min_length is not None and len(self.value) < self.min_length:
            raise ValueError(f"List has {len(self.value)} items, minimum is {self.min_length}")
        if self.max_length is not None and len(self.value) > self.max_length:
            raise ValueError(f"List has {len(self.value)} items, maximum is {self.max_length}")
        return self


# Discriminated union for all typed values
ModelTypedValue = Annotated[
    Union[
        ModelStringValue,
        ModelIntegerValue,
        ModelFloatValue,
        ModelBooleanValue,
        ModelDateTimeValue,
        ModelListStringValue,
        ModelNullValue,
        ModelDictValue,
        ModelListValue,
    ],
    Field(discriminator="type"),
]


class ModelTypedValueContainer(BaseModel):
    """
    Container for typed values with automatic type detection.
    
    This model can automatically convert Python values to the appropriate
    typed model, or accept pre-typed models directly.
    """

    value: ModelTypedValue = Field(..., description="The typed value")
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata")
    
    @classmethod
    def from_python_value(cls, value: Any, **kwargs: Any) -> "ModelTypedValueContainer":
        """
        Create a typed value container from a Python value.
        
        Args:
            value: Python value to convert
            **kwargs: Additional metadata
            
        Returns:
            ModelTypedValueContainer with the appropriate typed value
        """
        typed_value: ModelTypedValue
        
        if value is None:
            typed_value = ModelNullValue(value=None)
        elif isinstance(value, bool):  # Check bool before int (bool is subclass of int)
            typed_value = ModelBooleanValue(value=value)
        elif isinstance(value, int):
            typed_value = ModelIntegerValue(value=value)
        elif isinstance(value, float):
            typed_value = ModelFloatValue(value=value)
        elif isinstance(value, str):
            typed_value = ModelStringValue(value=value)
        elif isinstance(value, datetime):
            typed_value = ModelDateTimeValue(value=value)
        elif isinstance(value, list):
            # Check if it's a list of strings
            if all(isinstance(item, str) for item in value):
                typed_value = ModelListStringValue(value=value)
            else:
                typed_value = ModelListValue(value=value)
        elif isinstance(value, dict):
            typed_value = ModelDictValue(value=value)
        else:
            # Fallback to string representation
            typed_value = ModelStringValue(value=str(value))
        
        return cls(value=typed_value, metadata=kwargs if kwargs else None)
    
    def to_python_value(self) -> Any:
        """
        Convert the typed value back to a Python value.
        
        Returns:
            The Python value
        """
        if isinstance(self.value, ModelNullValue):
            return None
        return self.value.value
    
    @property
    def value_type(self) -> EnumValueType:
        """Get the type of the contained value."""
        return EnumValueType(self.value.type)


class ModelTypedMapping(BaseModel):
    """
    Strongly-typed mapping to replace Dict[str, Any] patterns.
    
    This model provides a type-safe alternative to generic dictionaries,
    where each value is properly typed and validated.
    """

    data: dict[str, ModelTypedValue] = Field(
        default_factory=dict,
        description="Mapping of keys to typed values",
    )
    
    def set_value(self, key: str, value: Any) -> None:
        """
        Set a value in the mapping with automatic type conversion.
        
        Args:
            key: The key to set
            value: The value to set (will be automatically typed)
        """
        container = ModelTypedValueContainer.from_python_value(value)
        self.data[key] = container.value
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """
        Get a value from the mapping, converting to Python type.
        
        Args:
            key: The key to get
            default: Default value if key not found
            
        Returns:
            The Python value or default
        """
        if key not in self.data:
            return default
        
        typed_value = self.data[key]
        if isinstance(typed_value, ModelNullValue):
            return None
        return typed_value.value
    
    def has_key(self, key: str) -> bool:
        """Check if a key exists in the mapping."""
        return key in self.data
    
    def keys(self) -> list[str]:
        """Get all keys in the mapping."""
        return list(self.data.keys())
    
    def to_dict(self) -> dict[str, Any]:
        """Convert the typed mapping to a regular Python dictionary."""
        result = {}
        for key, typed_value in self.data.items():
            if isinstance(typed_value, ModelNullValue):
                result[key] = None
            else:
                result[key] = typed_value.value
        return result
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModelTypedMapping":
        """
        Create a typed mapping from a regular Python dictionary.
        
        Args:
            data: Dictionary to convert
            
        Returns:
            ModelTypedMapping with typed values
        """
        typed_data = {}
        for key, value in data.items():
            container = ModelTypedValueContainer.from_python_value(value)
            typed_data[key] = container.value
        return cls(data=typed_data)