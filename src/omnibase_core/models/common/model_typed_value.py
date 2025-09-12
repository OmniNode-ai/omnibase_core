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
from typing import Any, ClassVar, Generic, Protocol, TypeVar, runtime_checkable

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


# Type alias for JSON-serializable values
SerializableValue = str | int | float | bool | list[Any] | dict[str, Any] | None

ValidatableValue = TypeVar("ValidatableValue", bound=ProtocolValidatable)


class ModelValueContainer(BaseModel):
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

    def is_type(self, expected_type: type) -> bool:
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
    def validate_serializable(cls, v: Any) -> Any:
        """Validate that the value is JSON serializable."""
        try:
            json.dumps(v)
            return v
        except (TypeError, ValueError) as e:
            raise ValueError(f"Value is not JSON serializable: {e}")

    # Type-safe factory methods
    @classmethod
    def create_string(cls, value: str, **metadata: str) -> "ModelValueContainer":
        """Create a string value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_int(cls, value: int, **metadata: str) -> "ModelValueContainer":
        """Create an integer value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_float(cls, value: float, **metadata: str) -> "ModelValueContainer":
        """Create a float value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_bool(cls, value: bool, **metadata: str) -> "ModelValueContainer":
        """Create a boolean value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_list(cls, value: list[Any], **metadata: str) -> "ModelValueContainer":
        """Create a list value container."""
        return cls(value=value, metadata=metadata)

    @classmethod
    def create_dict(
        cls, value: dict[str, Any], **metadata: str
    ) -> "ModelValueContainer":
        """Create a dict value container."""
        return cls(value=value, metadata=metadata)

    # === ProtocolValidatable Implementation ===

    def is_valid(self) -> bool:
        """
        Check if the contained value is valid.

        Performs comprehensive validation including:
        - JSON serialization capability
        - Type consistency
        - Value constraints for specific types
        - Metadata validation

        Returns:
            bool: True if the value is valid, False otherwise
        """
        try:
            # 1. Check JSON serialization (already validated in field_validator, but double-check)
            if not self.is_json_serializable():
                return False

            # 2. Type-specific validation
            if not self._validate_type_specific_constraints():
                return False

            # 3. Metadata validation
            if not self._validate_metadata():
                return False

            return True

        except Exception:
            return False

    def get_errors(self) -> list[str]:
        """
        Get validation errors for the contained value.

        Provides detailed error messages for debugging and user feedback.

        Returns:
            list[str]: List of validation error messages (empty if valid)
        """
        errors: list[str] = []

        try:
            # 1. JSON serialization check
            if not self.is_json_serializable():
                errors.append(
                    f"Value of type {self.type_name} is not JSON serializable"
                )

            # 2. Type-specific validation errors
            type_errors = self._get_type_specific_errors()
            errors.extend(type_errors)

            # 3. Metadata validation errors
            metadata_errors = self._get_metadata_errors()
            errors.extend(metadata_errors)

        except Exception as e:
            errors.append(f"Validation error: {str(e)}")

        return errors

    def _validate_type_specific_constraints(self) -> bool:
        """Validate type-specific constraints for the contained value."""
        # String validation
        if isinstance(self.value, str):
            # No empty strings in production containers (configurable)
            if len(self.value) == 0 and self.metadata.get("allow_empty") != "true":
                return False

        # Numeric validation
        elif isinstance(self.value, (int, float)):
            # Check for valid numeric ranges
            if isinstance(self.value, float):
                # Check for NaN and infinity
                import math

                if math.isnan(self.value) or math.isinf(self.value):
                    return False

        # List validation
        elif isinstance(self.value, list):
            # Check list depth and content
            if len(self.value) > 10000:  # Prevent DoS
                return False
            # Validate all items are JSON serializable
            try:
                json.dumps(self.value)
            except (TypeError, ValueError):
                return False

        # Dict validation
        elif isinstance(self.value, dict):
            # Check dict size and key types
            if len(self.value) > 1000:  # Prevent DoS
                return False
            # All keys must be strings for JSON compatibility
            if not all(isinstance(key, str) for key in self.value.keys()):
                return False

        return True

    def _validate_metadata(self) -> bool:
        """Validate metadata dictionary."""
        try:
            # Metadata must be string-to-string mapping
            if not all(
                isinstance(k, str) and isinstance(v, str)
                for k, v in self.metadata.items()
            ):
                return False

            # Size limits
            if len(self.metadata) > 100:  # Prevent DoS
                return False

            # Key/value length limits
            for key, value in self.metadata.items():
                if len(key) > 100 or len(value) > 1000:
                    return False

            return True

        except Exception:
            return False

    def _get_type_specific_errors(self) -> list[str]:
        """Get type-specific validation error messages."""
        errors: list[str] = []

        # String validation errors
        if isinstance(self.value, str):
            if len(self.value) == 0 and self.metadata.get("allow_empty") != "true":
                errors.append(
                    "Empty strings not allowed (set allow_empty='true' in metadata to override)"
                )

        # Numeric validation errors
        elif isinstance(self.value, (int, float)):
            if isinstance(self.value, float):
                import math

                if math.isnan(self.value):
                    errors.append("Float value cannot be NaN")
                elif math.isinf(self.value):
                    errors.append("Float value cannot be infinite")

        # List validation errors
        elif isinstance(self.value, list):
            if len(self.value) > 10000:
                errors.append("List exceeds maximum length of 10000 items")
            try:
                json.dumps(self.value)
            except (TypeError, ValueError) as e:
                errors.append(f"List contains non-serializable items: {e}")

        # Dict validation errors
        elif isinstance(self.value, dict):
            if len(self.value) > 1000:
                errors.append("Dict exceeds maximum size of 1000 entries")
            non_string_keys = [
                repr(k) for k in self.value.keys() if not isinstance(k, str)
            ]
            if non_string_keys:
                errors.append(
                    f"Dict contains non-string keys: {', '.join(non_string_keys)}"
                )

        return errors

    def _get_metadata_errors(self) -> list[str]:
        """Get metadata validation error messages."""
        errors: list[str] = []

        try:
            # Type checking
            for key, value in self.metadata.items():
                if not isinstance(key, str):
                    errors.append(f"Metadata key {repr(key)} is not a string")
                if not isinstance(value, str):
                    errors.append(f"Metadata value for key '{key}' is not a string")

            # Size limits
            if len(self.metadata) > 100:
                errors.append("Metadata exceeds maximum size of 100 entries")

            # Length limits
            for key, value in self.metadata.items():
                if isinstance(key, str) and len(key) > 100:
                    errors.append(
                        f"Metadata key '{key}' exceeds maximum length of 100 characters"
                    )
                if isinstance(value, str) and len(value) > 1000:
                    errors.append(
                        f"Metadata value for key '{key}' exceeds maximum length of 1000 characters"
                    )

        except Exception as e:
            errors.append(f"Metadata validation error: {str(e)}")

        return errors


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

    data: dict[str, ModelValueContainer] = Field(
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

    def set_list(self, key: str, value: list[Any]) -> None:
        """Set a list value."""
        self.data[key] = ModelValueContainer.create_list(value)

    def set_dict(self, key: str, value: dict[str, Any]) -> None:
        """Set a dict value with depth checking for security."""
        if self.current_depth > self.MAX_DEPTH:
            raise ValueError(
                f"Maximum nesting depth ({self.MAX_DEPTH}) exceeded to prevent DoS attacks"
            )
        self.data[key] = ModelValueContainer.create_dict(value)

    def set_value(self, key: str, value: Any) -> None:
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

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a value from the mapping."""
        if key not in self.data:
            return default
        return self.data[key].value

    def get_string(self, key: str, default: str | None = None) -> str | None:
        """Get a string value with type safety."""
        from typing import cast

        container = self.data.get(key)
        if container is None:
            return default
        if not container.is_type(str):
            raise ValueError(
                f"Value for key '{key}' is not a string, got {container.type_name}"
            )
        return cast(str, container.value)

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Get an integer value with type safety."""
        from typing import cast

        container = self.data.get(key)
        if container is None:
            return default
        if not container.is_type(int):
            raise ValueError(
                f"Value for key '{key}' is not an int, got {container.type_name}"
            )
        return cast(int, container.value)

    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        """Get a boolean value with type safety."""
        from typing import cast

        container = self.data.get(key)
        if container is None:
            return default
        if not container.is_type(bool):
            raise ValueError(
                f"Value for key '{key}' is not a bool, got {container.type_name}"
            )
        return cast(bool, container.value)

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the mapping."""
        return key in self.data

    def keys(self) -> list[str]:
        """Get all keys in the mapping."""
        return list(self.data.keys())

    def to_python_dict(self) -> dict[str, Any]:
        """Convert to a regular Python dictionary with native types."""
        return {key: container.value for key, container in self.data.items()}

    @classmethod
    def from_python_dict(
        cls, data: dict[str, Any], depth: int = 0
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

    # === ProtocolValidatable Implementation ===

    def is_valid(self) -> bool:
        """
        Check if all contained values in the mapping are valid.

        Performs aggregate validation across all value containers,
        checking both individual container validity and mapping constraints.

        Returns:
            bool: True if all containers and the mapping itself are valid
        """
        try:
            # 1. Validate depth constraint
            if self.current_depth > self.MAX_DEPTH:
                return False

            # 2. Validate all individual containers
            for container in self.data.values():
                if not container.is_valid():
                    return False

            # 3. Validate mapping-level constraints
            if not self._validate_mapping_constraints():
                return False

            return True

        except Exception:
            return False

    def get_errors(self) -> list[str]:
        """
        Get validation errors for all containers and mapping constraints.

        Aggregates errors from all value containers plus mapping-level validation.

        Returns:
            list[str]: Comprehensive list of all validation errors
        """
        errors: list[str] = []

        try:
            # 1. Check depth constraint
            if self.current_depth > self.MAX_DEPTH:
                errors.append(
                    f"Mapping depth {self.current_depth} exceeds maximum depth {self.MAX_DEPTH}"
                )

            # 2. Collect errors from all containers
            for key, container in self.data.items():
                container_errors = container.get_errors()
                for error in container_errors:
                    errors.append(f"Key '{key}': {error}")

            # 3. Add mapping-level constraint errors
            mapping_errors = self._get_mapping_constraint_errors()
            errors.extend(mapping_errors)

        except Exception as e:
            errors.append(f"Mapping validation error: {str(e)}")

        return errors

    def _validate_mapping_constraints(self) -> bool:
        """Validate mapping-level constraints."""
        try:
            # Size limits (prevent DoS)
            if len(self.data) > 10000:
                return False

            # Key validation
            for key in self.data.keys():
                if not isinstance(key, str):
                    return False
                if len(key) == 0 or len(key) > 200:
                    return False
                # Keys should not contain null bytes or control characters
                if "\x00" in key or any(ord(c) < 32 for c in key if c not in "\t\n\r"):
                    return False

            return True

        except Exception:
            return False

    def _get_mapping_constraint_errors(self) -> list[str]:
        """Get mapping-level constraint error messages."""
        errors: list[str] = []

        try:
            # Size validation
            if len(self.data) > 10000:
                errors.append("Mapping exceeds maximum size of 10000 entries")

            # Key validation
            for key in self.data.keys():
                if not isinstance(key, str):
                    errors.append(f"Key {repr(key)} is not a string")
                elif len(key) == 0:
                    errors.append("Empty key not allowed")
                elif len(key) > 200:
                    errors.append(
                        f"Key '{key}' exceeds maximum length of 200 characters"
                    )
                elif "\x00" in key:
                    errors.append(f"Key '{key}' contains null byte")
                elif any(ord(c) < 32 for c in key if c not in "\t\n\r"):
                    control_chars = [
                        hex(ord(c)) for c in key if ord(c) < 32 and c not in "\t\n\r"
                    ]
                    errors.append(
                        f"Key '{key}' contains control characters: {', '.join(control_chars)}"
                    )

        except Exception as e:
            errors.append(f"Key validation error: {str(e)}")

        return errors

    def validate_all_containers(self) -> dict[str, list[str]]:
        """
        Get detailed validation results for all containers.

        Returns:
            dict[str, list[str]]: Mapping of key -> list of validation errors
                                 (empty list if container is valid)
        """
        validation_results = {}

        for key, container in self.data.items():
            validation_results[key] = container.get_errors()

        return validation_results

    def get_invalid_containers(self) -> dict[str, list[str]]:
        """
        Get only containers that have validation errors.

        Returns:
            dict[str, list[str]]: Mapping of key -> validation errors
                                 (only includes containers with errors)
        """
        invalid_containers = {}

        for key, container in self.data.items():
            errors = container.get_errors()
            if errors:
                invalid_containers[key] = errors

        return invalid_containers

    def is_container_valid(self, key: str) -> bool:
        """
        Check if a specific container is valid.

        Args:
            key: Key of the container to check

        Returns:
            bool: True if container exists and is valid

        Raises:
            KeyError: If key does not exist
        """
        if key not in self.data:
            raise KeyError(f"Key '{key}' not found in mapping")

        return self.data[key].is_valid()


# Type aliases for common patterns
StringContainer = ModelValueContainer
IntContainer = ModelValueContainer
FloatContainer = ModelValueContainer
BoolContainer = ModelValueContainer
ListContainer = ModelValueContainer
DictContainer = ModelValueContainer


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
