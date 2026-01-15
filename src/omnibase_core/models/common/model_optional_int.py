"""
ModelOptionalInt

Type-safe optional integer with float-to-int coercion support.

This model provides a structured alternative to Union[None, float, int]
patterns with explicit handling of optional integer values and configurable
float coercion behavior.

Features:
- Type-safe optional integer storage
- Float-to-int coercion with configurable rounding modes
- Rust-style Option API (unwrap, unwrap_or, unwrap_or_else)
- Explicit None handling
- Comprehensive validation with detailed error messages
- Full mypy strict mode compliance

Usage Examples:
    # Create from integer
    >>> value = ModelOptionalInt(value=42)
    >>> assert value.unwrap() == 42

    # Create from None
    >>> empty = ModelOptionalInt(value=None)
    >>> assert empty.is_none() is True
    >>> assert empty.unwrap_or(10) == 10

    # Float coercion with exact values
    >>> from_float = ModelOptionalInt(value=3.0)
    >>> assert from_float.unwrap() == 3

    # Float rounding modes
    >>> rounded = ModelOptionalInt(
    ...     value=3.7,
    ...     coercion_mode=EnumCoercionMode.ROUND
    ... )
    >>> assert rounded.unwrap() == 4

Validation Modes:
    - STRICT: Only exact floats (3.0 → 3, but 3.5 raises error)
    - FLOOR: Floor division (3.7 → 3)
    - CEIL: Ceiling division (3.2 → 4)
    - ROUND: Standard rounding (3.5 → 4, 3.4 → 3)

IMPORT ORDER CONSTRAINTS (Critical - Do Not Break):
This module is part of a carefully managed import chain to avoid circular dependencies.

Safe Runtime Imports (OK to import at module level):
- Standard library modules only
- omnibase_core.errors modules
- omnibase_core.models.common.model_coercion_mode (EnumCoercionMode)
- pydantic modules
"""

import logging
import math
from collections.abc import Callable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.common.model_coercion_mode import EnumCoercionMode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Module-level logger for coercion observability
_logger = logging.getLogger(__name__)


class ModelOptionalInt(BaseModel):
    """
    Type-safe optional integer with float-to-int coercion support.

    Provides structured alternative to Union[None, float, int] patterns
    with explicit handling of optional integer values and configurable
    float coercion behavior.

    Attributes:
        value: Optional integer value (None or int)
        coercion_mode: Float-to-int conversion mode (default: STRICT)
        metadata: Optional metadata for the value (string-to-string mapping)

    Examples:
        # Basic usage
        >>> value = ModelOptionalInt(value=42)
        >>> assert value.is_some() is True
        >>> assert value.unwrap() == 42

        # None handling
        >>> empty = ModelOptionalInt(value=None)
        >>> assert empty.is_none() is True
        >>> assert empty.unwrap_or(10) == 10

        # Float coercion (exact values)
        >>> from_float = ModelOptionalInt(value=3.0)
        >>> assert from_float.unwrap() == 3

        # Float rounding
        >>> rounded = ModelOptionalInt(
        ...     value=3.7,
        ...     coercion_mode=EnumCoercionMode.ROUND
        ... )
        >>> assert rounded.unwrap() == 4

        # Unwrap with fallback
        >>> maybe_value = ModelOptionalInt(value=None)
        >>> result = maybe_value.unwrap_or_else(lambda: 100)
        >>> assert result == 100
    """

    value: int | None = Field(
        default=None,
        description="Optional integer value",
    )

    coercion_mode: EnumCoercionMode = Field(
        default=EnumCoercionMode.STRICT,
        description="Float-to-int conversion mode",
    )

    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional string metadata",
    )

    @model_validator(mode="before")
    @classmethod
    def coerce_float_to_int(cls, data: object) -> dict[str, object]:
        """
        Validate and coerce value to optional integer.

        Handles None, int, and float values with configurable coercion modes.
        Float values are validated based on the coercion_mode setting.

        Args:
            data: Input data (dict or value)

        Returns:
            dict[str, object]: Validated data with coerced value

        Raises:
            ModelOnexError: If value is invalid or coercion fails
        """
        # Ensure data is a dict
        if not isinstance(data, dict):
            data = {"value": data}

        # Type narrowing for mypy strict mode
        validated_data: dict[str, object] = data

        # Get value and coercion mode
        v = validated_data.get("value")
        coercion_mode_value = validated_data.get(
            "coercion_mode", EnumCoercionMode.STRICT
        )

        # Convert string to enum if necessary
        if isinstance(coercion_mode_value, str):
            try:
                coercion_mode = EnumCoercionMode(coercion_mode_value)
            except ValueError:
                coercion_mode = EnumCoercionMode.STRICT
        else:
            coercion_mode = coercion_mode_value  # type: ignore[assignment]

        # Handle None - no coercion needed
        if v is None:
            validated_data["value"] = None
            return validated_data

        # Handle boolean (reject - must use int explicitly)
        if isinstance(v, bool):
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Boolean values not allowed for optional int (use 0 or 1 explicitly)",
                context={
                    "value": str(v),
                    "value_type": "bool",
                },
            )

        # Handle integer - no coercion needed
        if isinstance(v, int):
            validated_data["value"] = v
            return validated_data

        # Handle float with coercion
        if isinstance(v, float):
            # Reject special float values
            if math.isnan(v) or math.isinf(v):
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message="Float value cannot be NaN or infinity",
                    context={
                        "value": str(v),
                        "is_nan": math.isnan(v),
                        "is_inf": math.isinf(v),
                    },
                )

            # Apply coercion based on mode
            if coercion_mode == EnumCoercionMode.STRICT:
                # Only exact floats allowed (e.g., 3.0)
                if v != int(v):
                    raise ModelOnexError(
                        error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                        message=f"Float value {v} is not an exact integer (use FLOOR, CEIL, or ROUND mode for non-exact values)",
                        context={
                            "value": str(v),
                            "coercion_mode": "strict",
                            "fractional_part": str(v - int(v)),
                        },
                    )
                coerced_value = int(v)
                validated_data["value"] = coerced_value
                _logger.debug(
                    "Coercion: field=value target_type=int original_type=float "
                    "original_value=%s coercion_mode=STRICT -> coerced to %d (exact float)",
                    v,
                    coerced_value,
                )

            elif coercion_mode == EnumCoercionMode.FLOOR:
                coerced_value = math.floor(v)
                validated_data["value"] = coerced_value
                _logger.debug(
                    "Coercion: field=value target_type=int original_type=float "
                    "original_value=%s coercion_mode=FLOOR -> coerced to %d",
                    v,
                    coerced_value,
                )

            elif coercion_mode == EnumCoercionMode.CEIL:
                coerced_value = math.ceil(v)
                validated_data["value"] = coerced_value
                _logger.debug(
                    "Coercion: field=value target_type=int original_type=float "
                    "original_value=%s coercion_mode=CEIL -> coerced to %d",
                    v,
                    coerced_value,
                )

            elif coercion_mode == EnumCoercionMode.ROUND:
                coerced_value = round(v)
                validated_data["value"] = coerced_value
                _logger.debug(
                    "Coercion: field=value target_type=int original_type=float "
                    "original_value=%s coercion_mode=ROUND -> coerced to %d",
                    v,
                    coerced_value,
                )

            else:
                # Should never reach here
                raise ModelOnexError(
                    error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                    message=f"Unknown coercion mode: {coercion_mode}",
                    context={
                        "coercion_mode": str(coercion_mode),
                    },
                )

            return validated_data

        # Unsupported type
        raise ModelOnexError(
            error_code=EnumCoreErrorCode.VALIDATION_ERROR,
            message=f"Cannot convert {type(v).__name__} to optional int",
            context={
                "value_type": type(v).__name__,
                "supported_types": "None, int, float",
            },
        )

    # === Rust-style Option API ===

    def unwrap(self) -> int:
        """
        Get the value, raising error if None.

        Returns:
            int: The stored value

        Raises:
            ModelOnexError: If value is None

        Examples:
            >>> value = ModelOptionalInt(value=42)
            >>> assert value.unwrap() == 42

            >>> empty = ModelOptionalInt(value=None)
            >>> empty.unwrap()  # Raises ModelOnexError
            Traceback (most recent call last):
                ...
            omnibase_core.errors.model_onex_error.ModelOnexError: ...
        """
        if self.value is None:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message="Called unwrap() on None value",
                context={
                    "hint": "Use unwrap_or() or unwrap_or_else() for safe unwrapping",
                },
            )
        return self.value

    def unwrap_or(self, default: int) -> int:
        """
        Get the value or return default if None.

        Args:
            default: Default value to return if None

        Returns:
            int: The stored value or default

        Examples:
            >>> value = ModelOptionalInt(value=42)
            >>> assert value.unwrap_or(10) == 42

            >>> empty = ModelOptionalInt(value=None)
            >>> assert empty.unwrap_or(10) == 10
        """
        return self.value if self.value is not None else default

    def unwrap_or_else(self, func: Callable[[], int]) -> int:
        """
        Get the value or compute default if None.

        Args:
            func: Function to compute default value

        Returns:
            int: The stored value or computed default

        Examples:
            >>> value = ModelOptionalInt(value=42)
            >>> assert value.unwrap_or_else(lambda: 100) == 42

            >>> empty = ModelOptionalInt(value=None)
            >>> assert empty.unwrap_or_else(lambda: 100) == 100
        """
        return self.value if self.value is not None else func()

    # === Helper Methods ===

    def is_none(self) -> bool:
        """
        Check if value is None.

        Returns:
            bool: True if value is None, False otherwise

        Examples:
            >>> value = ModelOptionalInt(value=42)
            >>> assert value.is_none() is False

            >>> empty = ModelOptionalInt(value=None)
            >>> assert empty.is_none() is True
        """
        return self.value is None

    def is_some(self) -> bool:
        """
        Check if value is present (not None).

        Returns:
            bool: True if value is present, False if None

        Examples:
            >>> value = ModelOptionalInt(value=42)
            >>> assert value.is_some() is True

            >>> empty = ModelOptionalInt(value=None)
            >>> assert empty.is_some() is False
        """
        return self.value is not None

    def get_value_or(self, default: int) -> int:
        """
        Get the value or return default if None (alias for unwrap_or).

        Args:
            default: Default value to return if None

        Returns:
            int: The stored value or default

        Examples:
            >>> value = ModelOptionalInt(value=42)
            >>> assert value.get_value_or(10) == 42

            >>> empty = ModelOptionalInt(value=None)
            >>> assert empty.get_value_or(10) == 10
        """
        return self.unwrap_or(default)

    def map(self, func: Callable[[int], int]) -> "ModelOptionalInt":
        """
        Apply function to value if present.

        Args:
            func: Function to apply to value

        Returns:
            ModelOptionalInt: New instance with transformed value or None

        Examples:
            >>> value = ModelOptionalInt(value=42)
            >>> doubled = value.map(lambda x: x * 2)
            >>> assert doubled.unwrap() == 84

            >>> empty = ModelOptionalInt(value=None)
            >>> still_empty = empty.map(lambda x: x * 2)
            >>> assert still_empty.is_none() is True
        """
        if self.value is not None:
            return ModelOptionalInt(
                value=func(self.value),
                coercion_mode=self.coercion_mode,
                metadata=self.metadata.copy(),
            )
        return ModelOptionalInt(
            value=None,
            coercion_mode=self.coercion_mode,
            metadata=self.metadata.copy(),
        )

    def as_dict(self) -> dict[str, object]:
        """
        Convert to dictionary representation.

        Returns:
            dict[str, object]: Dictionary with value, coercion_mode, and metadata

        Examples:
            >>> value = ModelOptionalInt(value=42)
            >>> data = value.as_dict()
            >>> assert data["value"] == 42
            >>> assert data["coercion_mode"] == "strict"
        """
        return {
            "value": self.value,
            "coercion_mode": self.coercion_mode.value,
            "metadata": self.metadata,
        }

    def __bool__(self) -> bool:
        """Boolean representation based on value presence.

        Warning:
            This differs from standard Pydantic behavior where ``bool(model)``
            always returns ``True``. Here, ``bool(optional)`` returns ``False``
            when the value is ``None``, enabling idiomatic presence checks.
            Note that ``0`` is a valid value and returns ``True``.

        Returns:
            bool: True if value is present (not None), False if None.

        Example:
            >>> value = ModelOptionalInt(value=42)
            >>> assert bool(value) is True

            >>> zero = ModelOptionalInt(value=0)
            >>> assert bool(zero) is True  # 0 is a valid value

            >>> empty = ModelOptionalInt(value=None)
            >>> assert bool(empty) is False
        """
        return self.is_some()

    def __str__(self) -> str:
        """String representation."""
        if self.value is None:
            return "OptionalInt(None)"
        return f"OptionalInt({self.value})"

    def __repr__(self) -> str:
        """Detailed representation."""
        return (
            f"ModelOptionalInt(value={self.value!r}, "
            f"coercion_mode={self.coercion_mode.value!r})"
        )

    model_config = ConfigDict(
        extra="ignore",
        validate_assignment=True,
    )


__all__ = ["ModelOptionalInt", "EnumCoercionMode"]
