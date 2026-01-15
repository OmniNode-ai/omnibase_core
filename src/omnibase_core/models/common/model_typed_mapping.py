"""
ModelTypedMapping

Strongly-typed mapping to replace Dict[str, Any] patterns.

This model provides a type-safe alternative to generic dictionaries,
where each value is properly typed and validated.

Security Features:
- Maximum depth limit to prevent DoS attacks via deep nesting
- Automatic type validation to prevent data injection

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from __future__ import annotations

from typing import ClassVar, cast

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_value_container import ModelValueContainer
from omnibase_core.models.errors.model_onex_error import ModelOnexError
from omnibase_core.models.types import JsonSerializable


class ModelTypedMapping(BaseModel):
    """
    Strongly-typed mapping to replace Dict[str, Any] patterns.

    This model provides a type-safe alternative to generic dict[str, Any]ionaries,
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
        """Set a string value using ONEX-compatible direct __init__ calls."""
        self.data[key] = ModelValueContainer(value=value)

    def set_int(self, key: str, value: int) -> None:
        """Set an integer value using ONEX-compatible direct __init__ calls."""
        self.data[key] = ModelValueContainer(value=value)

    def set_float(self, key: str, value: float) -> None:
        """Set a float value using ONEX-compatible direct __init__ calls."""
        self.data[key] = ModelValueContainer(value=value)

    def set_bool(self, key: str, value: bool) -> None:
        """Set a boolean value using ONEX-compatible direct __init__ calls."""
        self.data[key] = ModelValueContainer(value=value)

    def set_list(self, key: str, value: list[JsonSerializable]) -> None:
        """Set a list value using ONEX-compatible direct __init__ calls."""
        self.data[key] = ModelValueContainer(value=value)

    def set_dict(self, key: str, value: dict[str, JsonSerializable]) -> None:
        """Set a dict value with depth checking for security using ONEX-compatible direct __init__ calls."""
        if self.current_depth > self.MAX_DEPTH:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Maximum nesting depth ({self.MAX_DEPTH}) exceeded to prevent DoS attacks",
            )
        self.data[key] = ModelValueContainer(value=value)

    def set_value(self, key: str, value: object) -> None:
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
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Unsupported type for key '{key}': {type(value)}",
            )

    def get_value(self, key: str, default: object = None) -> object:
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
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value for key '{key}' is not a string, got {container.type_name}",
            )
        return cast("str", container.value)

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Get an integer value with type safety."""

        container = self.data.get(key)
        if container is None:
            return default
        if not container.is_type(int):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value for key '{key}' is not an int, got {container.type_name}",
            )
        return cast("int", container.value)

    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        """Get a boolean value with type safety."""

        container = self.data.get(key)
        if container is None:
            return default
        if not container.is_type(bool):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value for key '{key}' is not a bool, got {container.type_name}",
            )
        return cast("bool", container.value)

    def has_key(self, key: str) -> bool:
        """Check if a key exists in the mapping."""
        return key in self.data

    def keys(self) -> list[str]:
        """Get all keys in the mapping."""
        return list(self.data.keys())

    def to_python_dict(self) -> dict[str, object]:
        """Convert to a regular Python dictionary with native types."""
        return {key: container.value for key, container in self.data.items()}

    # ✅ Factory method from_python_dict removed for ONEX compliance
    # Use ONEX pattern: Create instance with ModelTypedMapping() then populate with set_value()
    # Example:
    #   mapping = ModelTypedMapping()
    #   for key, value in data.items():
    #       mapping.set_value(key, value)

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

        except (
            Exception
        ):  # fallback-ok: validation method, False indicates validation failure
            return False

    def get_errors(self) -> list[str]:
        """
        Get validation errors for all containers and mapping constraints.

        Aggregates errors from all value containers plus mapping-level validation.

        Returns:
            list[str]: Comprehensive list[Any]of all validation errors
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

        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as e:
            errors.append(f"Mapping validation error: {e!s}")

        return errors

    def _validate_mapping_constraints(self) -> bool:
        """Validate mapping-level constraints."""
        try:
            # Size limits (prevent DoS)
            if len(self.data) > 10000:
                return False

            # Key validation (keys are always str from type dict[str, ModelValueContainer])
            for key in self.data:
                if len(key) == 0 or len(key) > 200:
                    return False
                # Keys should not contain null bytes or control characters
                if "\x00" in key or any(ord(c) < 32 for c in key if c not in "\t\n\r"):
                    return False

            return True

        except (
            Exception
        ):  # fallback-ok: validation method, False indicates validation failure
            return False

    def _get_mapping_constraint_errors(self) -> list[str]:
        """Get mapping-level constraint error messages."""
        errors: list[str] = []

        try:
            # Size validation
            if len(self.data) > 10000:
                errors.append("Mapping exceeds maximum size of 10000 entries")

            # Key validation (keys are always str from type dict[str, ModelValueContainer])
            for key in self.data:
                if len(key) == 0:
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

        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as e:
            errors.append(f"Key validation error: {e!s}")

        return errors

    def validate_all_containers(self) -> dict[str, list[str]]:
        """
        Get detailed validation results for all containers.

        Returns:
            dict[str, list[str]]: Mapping of key -> list[Any]of validation errors
                                 (empty list[Any]if container is valid)
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
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.ITEM_NOT_REGISTERED,
                message=f"Key '{key}' not found in mapping",
            )

        return self.data[key].is_valid()
