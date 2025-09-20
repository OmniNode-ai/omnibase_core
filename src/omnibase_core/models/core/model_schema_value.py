"""
Model for representing schema values with proper type safety.

This model replaces Any type usage in schema definitions by providing
a structured representation of possible schema values using discriminated
unions and factory patterns with generic type support.
"""

from typing import Literal, Union, Any, Generic, TypeVar, Protocol, Callable
from pydantic import BaseModel, Field

# Type variables for factory patterns
T = TypeVar("T")  # Input type
R = TypeVar("R")  # Result type


class ConvertibleToSchema(Protocol):
    """Protocol for types that can be converted to ModelSchemaValue."""

    def to_schema_value(self) -> "ModelSchemaValue":
        """Convert this object to a ModelSchemaValue."""
        ...


class ModelSchemaValueString(BaseModel):
    """String value type."""
    value_type: Literal["string"] = "string"
    string_value: str = Field(..., description="String value")


class ModelSchemaValueNumber(BaseModel):
    """Number value type."""
    value_type: Literal["number"] = "number"
    number_value: int | float = Field(..., description="Numeric value")


class ModelSchemaValueBoolean(BaseModel):
    """Boolean value type."""
    value_type: Literal["boolean"] = "boolean"
    boolean_value: bool = Field(..., description="Boolean value")


class ModelSchemaValueNull(BaseModel):
    """Null value type."""
    value_type: Literal["null"] = "null"
    null_value: Literal[True] = True


class ModelSchemaValueArray(BaseModel):
    """Array value type."""
    value_type: Literal["array"] = "array"
    array_value: list["ModelSchemaValue"] = Field(..., description="Array of values")


class ModelSchemaValueObject(BaseModel):
    """Object value type."""
    value_type: Literal["object"] = "object"
    object_value: dict[str, "ModelSchemaValue"] = Field(..., description="Object with key-value pairs")


# Discriminated union type
ModelSchemaValue = Union[
    ModelSchemaValueString,
    ModelSchemaValueNumber,
    ModelSchemaValueBoolean,
    ModelSchemaValueNull,
    ModelSchemaValueArray,
    ModelSchemaValueObject,
]


class ModelSchemaValueFactory(Generic[T]):
    """
    Generic factory for creating ModelSchemaValue instances from Python values.

    Provides type-safe conversion methods with generic support for custom types.
    """

    # Type mappings for factory pattern
    _TYPE_HANDLERS: dict[type, Callable[[Any], ModelSchemaValue]] = {
        type(None): lambda v: ModelSchemaValueNull(),
        bool: lambda v: ModelSchemaValueBoolean(boolean_value=v),
        str: lambda v: ModelSchemaValueString(string_value=v),
        int: lambda v: ModelSchemaValueNumber(number_value=v),
        float: lambda v: ModelSchemaValueNumber(number_value=v),
        list: lambda v: ModelSchemaValueArray(
            array_value=[ModelSchemaValueFactory.from_value(item) for item in v]
        ),
        dict: lambda v: ModelSchemaValueObject(
            object_value={k: ModelSchemaValueFactory.from_value(val) for k, val in v.items()}
        ),
    }

    # Custom type converters registry
    _CUSTOM_CONVERTERS: dict[type, Callable[[Any], ModelSchemaValue]] = {}

    @classmethod
    def from_value(cls, value: Any) -> ModelSchemaValue:
        """
        Create ModelSchemaValue from a Python value using factory pattern.

        Args:
            value: Python value to convert

        Returns:
            ModelSchemaValue instance (discriminated union)
        """
        value_type = type(value)

        # Handle boolean first since bool is a subclass of int
        if isinstance(value, bool):
            return cls._TYPE_HANDLERS[bool](value)

        # Check for direct type match
        if value_type in cls._TYPE_HANDLERS:
            return cls._TYPE_HANDLERS[value_type](value)

        # Handle subclasses of numeric types
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return ModelSchemaValueNumber(number_value=value)

        # Handle list-like objects
        if hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
            return ModelSchemaValueArray(
                array_value=[cls.from_value(item) for item in value]
            )

        # Handle dict-like objects
        if hasattr(value, 'items'):
            return ModelSchemaValueObject(
                object_value={str(k): cls.from_value(v) for k, v in value.items()}
            )

        # Check for custom converters
        for registered_type, converter in cls._CUSTOM_CONVERTERS.items():
            if isinstance(value, registered_type):
                return converter(value)

        # Check for ConvertibleToSchema protocol
        if hasattr(value, 'to_schema_value') and callable(getattr(value, 'to_schema_value')):
            return value.to_schema_value()

        # Convert unknown types to string representation
        return ModelSchemaValueString(string_value=str(value))

    @classmethod
    def to_value(cls, schema_value: ModelSchemaValue) -> Any:
        """
        Convert ModelSchemaValue back to Python value.

        Args:
            schema_value: ModelSchemaValue instance to convert

        Returns:
            Python value
        """
        match schema_value:
            case ModelSchemaValueNull():
                return None
            case ModelSchemaValueBoolean() as bv:
                return bv.boolean_value
            case ModelSchemaValueString() as sv:
                return sv.string_value
            case ModelSchemaValueNumber() as nv:
                return nv.number_value
            case ModelSchemaValueArray() as av:
                return [cls.to_value(item) for item in av.array_value]
            case ModelSchemaValueObject() as ov:
                return {k: cls.to_value(v) for k, v in ov.object_value.items()}
            case _:
                raise ValueError(f"Unknown schema value type: {type(schema_value)}")

    @classmethod
    def register_converter(cls, type_class: type[T], converter: Callable[[T], ModelSchemaValue]) -> None:
        """
        Register a custom converter for a specific type.

        Args:
            type_class: The type to register a converter for
            converter: Function to convert instances of type_class to ModelSchemaValue
        """
        cls._CUSTOM_CONVERTERS[type_class] = converter

    @classmethod
    def unregister_converter(cls, type_class: type[T]) -> bool:
        """
        Unregister a custom converter.

        Args:
            type_class: The type to unregister

        Returns:
            True if converter was removed, False if not found
        """
        if type_class in cls._CUSTOM_CONVERTERS:
            del cls._CUSTOM_CONVERTERS[type_class]
            return True
        return False

    @classmethod
    def has_converter(cls, type_class: type[T]) -> bool:
        """
        Check if a custom converter is registered for a type.

        Args:
            type_class: The type to check

        Returns:
            True if converter is registered
        """
        return type_class in cls._CUSTOM_CONVERTERS

    @classmethod
    def get_supported_types(cls) -> set[type]:
        """
        Get all supported types (built-in and custom).

        Returns:
            Set of all supported types
        """
        return set(cls._TYPE_HANDLERS.keys()) | set(cls._CUSTOM_CONVERTERS.keys())

    @classmethod
    def create_typed_converter(cls, target_type: type[R]) -> Callable[[T], R]:
        """
        Create a type-safe converter function.

        Args:
            target_type: The target type to convert to

        Returns:
            Converter function that maintains type safety
        """
        def converter(value: T) -> R:
            schema_value = cls.from_value(value)
            python_value = cls.to_value(schema_value)

            # Type conversion with validation
            if target_type == str:
                return str(python_value)  # type: ignore
            elif target_type == int:
                if isinstance(python_value, (int, float)):
                    return int(python_value)  # type: ignore
                elif isinstance(python_value, str):
                    return int(float(python_value))  # type: ignore
            elif target_type == float:
                if isinstance(python_value, (int, float)):
                    return float(python_value)  # type: ignore
                elif isinstance(python_value, str):
                    return float(python_value)  # type: ignore
            elif target_type == bool:
                if isinstance(python_value, bool):
                    return python_value  # type: ignore
                elif isinstance(python_value, str):
                    return python_value.lower() in ('true', '1', 'yes', 'on')  # type: ignore
                else:
                    return bool(python_value)  # type: ignore
            elif target_type == list:
                if isinstance(python_value, list):
                    return python_value  # type: ignore
                else:
                    return [python_value]  # type: ignore
            elif target_type == dict:
                if isinstance(python_value, dict):
                    return python_value  # type: ignore
                else:
                    return {"value": python_value}  # type: ignore

            # Fallback: try direct conversion
            try:
                return target_type(python_value)  # type: ignore
            except (ValueError, TypeError) as e:
                raise ValueError(f"Cannot convert {type(python_value)} to {target_type}: {e}")

        return converter

    @classmethod
    def batch_convert(cls, values: list[T]) -> list[ModelSchemaValue]:
        """
        Convert multiple values in batch.

        Args:
            values: List of values to convert

        Returns:
            List of converted ModelSchemaValue instances
        """
        return [cls.from_value(value) for value in values]

    @classmethod
    def batch_to_values(cls, schema_values: list[ModelSchemaValue]) -> list[Any]:
        """
        Convert multiple schema values back to Python values.

        Args:
            schema_values: List of ModelSchemaValue instances

        Returns:
            List of Python values
        """
        return [cls.to_value(schema_value) for schema_value in schema_values]


# Convenience functions for backward compatibility
def from_value(value: Any) -> ModelSchemaValue:
    """Create ModelSchemaValue from Python value."""
    return ModelSchemaValueFactory.from_value(value)


def to_value(schema_value: ModelSchemaValue) -> Any:
    """Convert ModelSchemaValue to Python value."""
    return ModelSchemaValueFactory.to_value(schema_value)