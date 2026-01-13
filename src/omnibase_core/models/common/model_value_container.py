"""
ModelValueContainer

Generic container that preserves exact type information.

Replaces loose Union types with type-safe generic containers.
No wrapper classes needed - uses Python's native types directly.

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
===============================================
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
"""

from __future__ import annotations

import json
import math
from typing import Any

# Import protocols from omnibase_spi
from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Import standard type alias from ONEX types
from omnibase_core.models.types import JsonSerializable

ValidatableValue = type("ValidatableValue", (object,), {})


class ModelValueContainer(BaseModel):
    """
    Generic container that preserves exact type information.

    Replaces loose Union types with type-safe generic containers.
    No wrapper classes needed - uses Python's native types directly.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    value: JsonSerializable = Field(default=..., description="The contained value")
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
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Value is not JSON serializable: {e}",
            )

    # ✅ Factory methods removed for ONEX compliance
    # Use direct __init__ calls: ModelValueContainer(value=data, metadata={})
    # ONEX Pattern: YAML Contract → Pydantic Model → Direct __init__() only

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

        except (
            Exception
        ):  # fallback-ok: validation method, False indicates validation failure
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

        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as e:
            errors.append(f"Validation error: {e!s}")

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
            # Check list[Any]depth and content
            if len(self.value) > 10000:  # Prevent DoS
                return False
            # Validate all items are JSON serializable
            try:
                json.dumps(self.value)
            except (TypeError, ValueError):
                return False

        # Dict validation
        elif isinstance(self.value, dict):
            # Check dict[str, Any]size and key types
            if len(self.value) > 1000:  # Prevent DoS
                return False
            # All keys must be strings for JSON compatibility
            if not all(isinstance(key, str) for key in self.value):
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

        except (
            Exception
        ):  # fallback-ok: validation method, False indicates validation failure
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
            non_string_keys = [repr(k) for k in self.value if not isinstance(k, str)]
            if non_string_keys:
                errors.append(
                    f"Dict contains non-string keys: {', '.join(non_string_keys)}"
                )

        return errors

    def _get_metadata_errors(self) -> list[str]:
        """Get metadata validation error messages."""
        errors: list[str] = []

        try:
            # Type checking not needed - dict[str, str] annotation guarantees types
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

        except (AttributeError, KeyError, RuntimeError, TypeError, ValueError) as e:
            errors.append(f"Metadata validation error: {e!s}")

        return errors
