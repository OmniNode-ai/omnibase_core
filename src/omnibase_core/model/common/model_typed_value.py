"""
Generic Value Container Models

Proper generic implementation to replace loose Union types throughout the codebase.
Uses generic containers with protocol constraints instead of discriminated unions,
following ONEX architecture patterns for type safety.

This replaces patterns like Union[str, int, float, bool, dict, list] with
type-safe generic containers that preserve exact type information.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import ClassVar, Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, Field, field_validator


# Protocol definitions (MUST start with "Protocol")
@runtime_checkable
class ProtocolJsonSerializable(Protocol):
    """Protocol for values that can be JSON serialized."""

    # Built-in types that implement this: str, int, float, bool, list, dict, None


@runtime_checkable
class ProtocolValidatable(Protocol):
    """Protocol for values that can validate themselves."""

    def is_valid(self) -> bool:
        """Check if the value is valid."""
        ...

    def get_errors(self) -> list[str]:
        """Get validation errors."""
        ...


# Constrained TypeVars for type safety
SerializableValue = TypeVar(
    "SerializableValue", str, int, float, bool, list, dict, type(None)
)

ValidatableValue = TypeVar("ValidatableValue", bound=ProtocolValidatable)


class ModelValueContainer(BaseModel, Generic[SerializableValue]):
    """
    Generic container that preserves exact type information.

    Replaces loose Union types with type-safe generic containers.
    No wrapper classes needed - uses Python's native types directly.
    """

    value: SerializableValue = Field(..., description="The contained value")
    metadata: dict[str, str] = Field(
        default_factory=dict, description="Optional string metadata"
    )

    @property
    def python_type(self) -> type:
        """Get the actual Python type of the contained value."""
        return type(self.value)

    @property
    def type_name(self) -> str:
        """Get human-readable type name."""
        return self.python_type.__name__

    def is_type(self, expected_type: type[SerializableValue]) -> bool:
        """Type-safe runtime type checking."""
        return isinstance(self.value, expected_type)

    def is_json_serializable(self) -> bool:
        """Check if the value can be JSON serialized."""
        try:
            json.dumps(self.value)
            return True
        except (TypeError, ValueError):
            return False

    @field_validator("value")
    @classmethod
    def validate_serializable(cls, v: SerializableValue) -> SerializableValue:
        """Validate that the value is JSON serializable."""
        try:
            json.dumps(v)
            return v
        except (TypeError, ValueError) as e:
            raise ValueError(f"Value is not JSON serializable: {e}")

    # Type-safe factory methods
    @classmethod
    def create_string(cls, value: str, **metadata: str) -> "ModelValueContainer[str]":
        """Create a string value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_int(cls, value: int, **metadata: str) -> "ModelValueContainer[int]":
        """Create an integer value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_float(
        cls, value: float, **metadata: str
    ) -> "ModelValueContainer[float]":
        """Create a float value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_bool(cls, value: bool, **metadata: str) -> "ModelValueContainer[bool]":
        """Create a boolean value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_list(cls, value: list, **metadata: str) -> "ModelValueContainer[list]":
        """Create a list value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_dict(cls, value: dict, **metadata: str) -> "ModelValueContainer[dict]":
        """Create a dict value container."""
        return cls(value=value, metadata=metadata)


class ModelTypedMapping(BaseModel):
    """
    Strongly-typed mapping to replace Dict[str, Any] patterns.

    This model provides a type-safe alternative to generic dictionaries,
    where each value is properly typed and validated.

    Security Features:
    - Maximum depth limit to prevent DoS attacks via deep nesting
    - Automatic type validation to prevent data injection
    """

    # Security constant - prevent DoS via deep nesting
    MAX_DEPTH: ClassVar[int] = 10

    data: dict[str, ModelValueContainer[SerializableValue]] = Field(
        default_factory=dict,
        description="Mapping of keys to typed value containers",
    )

    current_depth: int = Field(
        default=0,
        description="Current nesting depth for DoS prevention",
        exclude=True,  # Don't include in serialization
    )

    def set_string(self, key: str, value: str) -> None:
        """Set a string value."""
        self.data[key] = ModelValueContainer.create_string(value)

    def set_int(self, key: str, value: int) -> None:
        """Set an integer value."""
        self.data[key] = ModelValueContainer.create_int(value)

    def set_float(self, key: str, value: float) -> None:
        """Set a float value."""
        self.data[key] = ModelValueContainer.create_float(value)

    def set_bool(self, key: str, value: bool) -> None:
        """Set a boolean value."""
        self.data[key] = ModelValueContainer.create_bool(value)

    def set_list(self, key: str, value: list) -> None:
        """Set a list value."""
        self.data[key] = ModelValueContainer.create_list(value)

    def set_dict(self, key: str, value: dict) -> None:
        """Set a dict value with depth checking for security."""
        if self.current_depth > self.MAX_DEPTH:
            raise ValueError(
                f"Maximum nesting depth ({self.MAX_DEPTH}) exceeded to prevent DoS attacks"
            )
        self.data[key] = ModelValueContainer.create_dict(value)

    def set_value(self, key: str, value: SerializableValue) -> None:
        """
        Set a value with automatic type detection.

        Args:
            key: The key to set
            value: The value to set (automatically typed)
        """
        if isinstance(value, str):
            self.set_string(key, value)
        elif isinstance(value, bool):  # Check bool before int
            self.set_bool(key, value)
        elif isinstance(value, int):
            self.set_int(key, value)
        elif isinstance(value, float):
            self.set_float(key, value)
        elif isinstance(value, list):
            self.set_list(key, value)
        elif isinstance(value, dict):
            self.set_dict(key, value)
        elif value is None:
            # Skip None values for now - could add explicit None handling later
            pass
        else:
            raise ValueError(f"Unsupported type for key '{key}': {type(value)}")

    def get_value(
        self, key: str, default: SerializableValue | None = None
    ) -> SerializableValue | None:
        """Get a value from the mapping."""
        if key not in self.data:
            return default
        return self.data[key].value

    def get_string(self, key: str, default: str | None = None) -> str | None:
        """Get a string value with type safety."""
        container = self.data.get(key)
        if container is None:
            return default
        if not container.is_type(str):
            raise ValueError(
                f"Value for key '{key}' is not a string, got {container.type_name}"
            )
        return container.value  # Type checker knows this is str

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Get an integer value with type safety."""
        container = self.data.get(key)
        if container is None:
            return default
        if not container.is_type(int):
            raise ValueError(
                f"Value for key '{key}' is not an int, got {container.type_name}"
            )
        return container.value  # Type checker knows this is int

    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        """Get a boolean value with type safety."""
        container = self.data.get(key)
        if container is None:
            return default
        if not container.is_type(bool):
            raise ValueError(
                f"Value for key '{key}' is not a bool, got {container.type_name}"
            )
        return container.value  # Type checker knows this is bool

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the mapping."""
        return key in self.data

    def keys(self) -> list[str]:
        """Get all keys in the mapping."""
        return list(self.data.keys())

    def to_python_dict(self) -> dict[str, SerializableValue]:
        """Convert to a regular Python dictionary with native types."""
        return {key: container.value for key, container in self.data.items()}

    @classmethod
    def from_python_dict(
        cls, data: dict[str, SerializableValue], depth: int = 0
    ) -> "ModelTypedMapping":
        """
        Create a typed mapping from a regular Python dictionary.

        Args:
            data: Dictionary with JSON-serializable values
            depth: Current nesting depth (for DoS prevention)

        Returns:
            ModelTypedMapping with typed containers

        Raises:
            ValueError: If maximum depth exceeded or unsupported type found
        """
        if depth > cls.MAX_DEPTH:
            raise ValueError(
                f"Maximum nesting depth ({cls.MAX_DEPTH}) exceeded to prevent DoS attacks"
            )

        instance = cls(current_depth=depth)
        for key, value in data.items():
            # Type-safe assignment based on Python type
            if isinstance(value, str):
                instance.set_string(key, value)
            elif isinstance(value, bool):  # Check bool before int
                instance.set_bool(key, value)
            elif isinstance(value, int):
                instance.set_int(key, value)
            elif isinstance(value, float):
                instance.set_float(key, value)
            elif isinstance(value, list):
                instance.set_list(key, value)
            elif isinstance(value, dict):
                # Recursively create nested mapping with depth + 1
                nested_mapping = cls.from_python_dict(value, depth + 1)
                instance.data[key] = ModelValueContainer.create_dict(
                    nested_mapping.to_python_dict()
                )
            elif value is None:
                # For None values, we'll store as a special case
                # This is the only legitimate use of a "null" representation
                continue  # Skip None values for now
            else:
                raise ValueError(f"Unsupported type for key '{key}': {type(value)}")
        return instance


# Type aliases for common patterns
StringContainer = ModelValueContainer[str]
IntContainer = ModelValueContainer[int]
FloatContainer = ModelValueContainer[float]
BoolContainer = ModelValueContainer[bool]
ListContainer = ModelValueContainer[list]
DictContainer = ModelValueContainer[dict]


# ARCHITECTURAL PRINCIPLE: Strong Typing Only
#
# ❌ NO string paths - always use Path objects
# ❌ NO string versions - always use ModelSemVer objects
# ❌ NO Union[Path, str] fallbacks - choose one type and stick to it
# ❌ NO "convenience" conversion methods - use proper types from the start
#
# ✅ file_path: Path (not str | Path)
# ✅ version: ModelSemVer (not str | ModelSemVer)
# ✅ timestamp: datetime (not str | datetime)
#
# This prevents type confusion, platform issues, and API inconsistencies.
