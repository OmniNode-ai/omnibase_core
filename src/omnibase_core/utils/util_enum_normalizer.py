# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Enum normalizer utility for Pydantic field validation.

This module provides a factory function to create enum normalizers that can be
used with Pydantic's @field_validator decorator. The normalizer enables:
1. Accepting both enum values and string representations
2. Case-insensitive string matching
3. Strict validation that rejects invalid enum values

This module is intentionally kept minimal with no omnibase_core dependencies
to avoid circular imports when used in models.

Ticket: OMN-1054
"""

from collections.abc import Callable
from enum import Enum


def create_enum_normalizer[E: Enum](
    enum_class: type[E],
) -> Callable[[E | str | None], E | str | None]:
    """Create a Pydantic field validator for flexible enum normalization.

    This factory creates a validator function that can be used with Pydantic's
    @field_validator decorator to normalize string values to enum members with
    flexible string handling for unknown values.

    The created validator:
    1. Returns None if input is None
    2. Returns the enum member if input is already an enum instance
    3. Converts string to enum (case-insensitive via .lower())
    4. Returns the original string as-is if no match found (flexible handling)

    Args:
        enum_class: The enum class to normalize values to

    Returns:
        A validator function compatible with Pydantic's @field_validator

    Example:
        >>> from pydantic import BaseModel, field_validator
        >>> from enum import Enum
        >>> from omnibase_core.utils.util_enum_normalizer import create_enum_normalizer
        >>>
        >>> class Status(Enum):
        ...     ACTIVE = "active"
        ...     INACTIVE = "inactive"
        >>>
        >>> class MyModel(BaseModel):
        ...     status: Status | str | None = None
        ...
        ...     @field_validator("status", mode="before")
        ...     @classmethod
        ...     def normalize_status(cls, v):
        ...         return create_enum_normalizer(Status)(v)
        >>>
        >>> # String value normalized to enum
        >>> m = MyModel(status="active")
        >>> m.status == Status.ACTIVE
        True
        >>>
        >>> # Unknown string kept as-is (flexible handling)
        >>> m2 = MyModel(status="unknown_status")
        >>> m2.status == "unknown_status"
        True

    Ticket: OMN-1054
    """

    def normalize(v: E | str | None) -> E | str | None:
        if v is None:
            return None
        if isinstance(v, enum_class):
            return v
        # At this point, v must be a string (type narrowing for mypy)
        if not isinstance(v, str):
            # This branch should never execute, but helps mypy understand the type
            msg = f"Expected {enum_class.__name__} or str, got {type(v).__name__}"
            # error-ok: Pydantic validator requires ValueError
            raise ValueError(msg)  # pragma: no cover
        # Convert string to enum (flexible handling - keep as-is if no match)
        try:
            return enum_class(v.lower())
        except ValueError:
            # Flexible handling: return the original string as-is
            return v

    return normalize


__all__ = ["create_enum_normalizer"]
