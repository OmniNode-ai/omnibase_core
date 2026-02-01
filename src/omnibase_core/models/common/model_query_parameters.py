"""
Typed query parameters model for effect operations.

This module provides a strongly-typed model for query parameters,
replacing dict[str, str] patterns with explicit type validation
and helper methods for query string generation.

The ``ModelQueryParameters`` class supports multiple value types
(str, int, float, bool, list[str]) and provides URL-safe query string
generation with proper encoding.

Example:
    >>> from omnibase_core.models.common.model_query_parameters import (
    ...     ModelQueryParameters,
    ... )
    >>> params = ModelQueryParameters.from_dict({
    ...     "limit": 10,
    ...     "offset": 0,
    ...     "active": True,
    ... })
    >>> params.to_query_string()
    'limit=10&offset=0&active=true'

Security:
    - ``MAX_PARAMETERS = 100`` prevents DoS via parameter flooding
    - URL encoding via ``urllib.parse.urlencode`` prevents injection attacks
    - Type validation ensures only safe value types are accepted

See Also:
    - :class:`ModelEnvelopePayload`: Typed event payload model.
"""

from __future__ import annotations

from typing import ClassVar, Self
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode
from omnibase_core.models.errors.model_onex_error import ModelOnexError

# Type alias for query parameter values (URL query strings)
# Different from centralized ParameterValue: allows None (unset), excludes dict (no nested structures)
QueryParameterValue = str | int | float | bool | list[str] | None


class ModelQueryParameters(BaseModel):
    """
    Typed query parameters for effect operations.

    Replaces dict[str, str] parameters field with a typed container
    that supports multiple value types while maintaining type safety.

    Features:
    - Multiple value types (str, int, float, bool, list[str])
    - Query string generation with URL encoding
    - Type-safe parameter access with typed getters
    - Security constraints (max parameter count)

    Example:
        >>> params = ModelQueryParameters.from_dict({"limit": 10, "offset": 0})
        >>> params.items["limit"]
        10
        >>> params.to_dict()
        {'limit': 10, 'offset': 0}
        >>> params.to_query_string()
        'limit=10&offset=0'
    """

    model_config = ConfigDict(
        extra="forbid", from_attributes=True, validate_assignment=True
    )

    # Security constant - prevent DoS via large parameter sets
    MAX_PARAMETERS: ClassVar[int] = 100

    items: dict[str, QueryParameterValue] = Field(
        default_factory=dict,
        description="Query parameters as key-value pairs",
    )

    @model_validator(mode="after")
    def _validate_parameter_count(self) -> Self:
        """Validate that parameter count doesn't exceed maximum."""
        if len(self.items) > self.MAX_PARAMETERS:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Parameter count ({len(self.items)}) exceeds maximum ({self.MAX_PARAMETERS})",
                parameter_count=len(self.items),
                max_parameters=self.MAX_PARAMETERS,
            )
        return self

    @classmethod
    def from_dict(cls, data: dict[str, QueryParameterValue]) -> Self:
        """Create from a dictionary of parameters.

        Args:
            data: Dictionary of parameter key-value pairs.

        Returns:
            New ModelQueryParameters instance.
        """
        return cls(items=data)

    @classmethod
    def from_string_dict(cls, data: dict[str, str]) -> Self:
        """Create from a string dictionary.

        Args:
            data: Dictionary of parameter names to string values.

        Returns:
            New ModelQueryParameters instance.
        """
        # Convert to QueryParameterValue dict to satisfy type checker
        items: dict[str, QueryParameterValue] = dict(data)
        return cls(items=items)

    def to_dict(self) -> dict[str, QueryParameterValue]:
        """Convert to dictionary format preserving original types.

        Returns:
            Dictionary of parameter key-value pairs.
        """
        return self.items.copy()

    def to_string_dict(self) -> dict[str, str]:
        """Convert to dict[str, str] for API compatibility.

        Returns:
            Dictionary with string keys and values.
        """
        result: dict[str, str] = {}
        for key, value in self.items.items():
            if value is not None:
                result[key] = self._value_to_string(value)
        return result

    def to_query_string(self) -> str:
        """Convert parameters to URL query string.

        Returns:
            URL-encoded query string (e.g., "page=1&limit=10").
        """
        pairs: list[tuple[str, str]] = []
        for key, value in self.items.items():
            if value is not None:
                pairs.append((key, self._value_to_string(value)))
        return urlencode(pairs)

    @staticmethod
    def _value_to_string(value: QueryParameterValue) -> str:
        """Convert a parameter value to string representation.

        Args:
            value: Parameter value to convert.

        Returns:
            String representation suitable for URL encoding.
        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, list):
            return ",".join(value)
        return str(value)

    def get(self, key: str, default: QueryParameterValue = None) -> QueryParameterValue:
        """Get a parameter value by key.

        Args:
            key: Parameter key to look up.
            default: Default value if key not found.

        Returns:
            Parameter value or default.
        """
        return self.items.get(key, default)

    def get_string(self, key: str, default: str | None = None) -> str | None:
        """Get a parameter value as string.

        Args:
            key: Parameter name to retrieve.
            default: Default value if parameter not found.

        Returns:
            Parameter value as string or default.
        """
        value = self.items.get(key)
        if value is None:
            return default
        return self._value_to_string(value)

    def get_int(self, key: str, default: int | None = None) -> int | None:
        """Get a parameter value as integer.

        Args:
            key: Parameter name to retrieve.
            default: Default value if parameter not found or not convertible.

        Returns:
            Parameter value as int or default.
        """
        value = self.items.get(key)
        if value is None:
            return default
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return default
        return default

    def get_float(self, key: str, default: float | None = None) -> float | None:
        """Get a parameter value as float.

        Args:
            key: Parameter name to retrieve.
            default: Default value if parameter not found or not convertible.

        Returns:
            Parameter value as float or default.
        """
        value = self.items.get(key)
        if value is None:
            return default
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    def get_bool(self, key: str, default: bool | None = None) -> bool | None:
        """Get a parameter value as boolean.

        Args:
            key: Parameter name to retrieve.
            default: Default value if parameter not found or not convertible.

        Returns:
            Parameter value as bool or default.
        """
        value = self.items.get(key)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("true", "1", "yes", "on"):
                return True
            if v in ("false", "0", "no", "off"):
                return False
            return default
        if isinstance(value, int):
            return value != 0
        return default

    def has(self, key: str) -> bool:
        """Check if parameter exists.

        Args:
            key: Parameter name to check.

        Returns:
            True if parameter exists, False otherwise.
        """
        return key in self.items

    def set(self, key: str, value: QueryParameterValue) -> ModelQueryParameters:
        """Set a parameter value, returning a new instance.

        Args:
            key: Parameter name.
            value: Parameter value.

        Returns:
            New ModelQueryParameters instance with updated parameter.
        """
        new_items = self.items.copy()
        new_items[key] = value
        return ModelQueryParameters(items=new_items)

    def remove(self, key: str) -> ModelQueryParameters:
        """Remove a parameter by name, returning a new instance.

        Args:
            key: Parameter name to remove.

        Returns:
            New ModelQueryParameters instance without the parameter.
        """
        new_items = {k: v for k, v in self.items.items() if k != key}
        return ModelQueryParameters(items=new_items)

    def __len__(self) -> int:
        """Return the number of parameters."""
        return len(self.items)

    def __bool__(self) -> bool:
        """Return True if there are any parameters.

        Warning:
            This differs from standard Pydantic behavior where ``bool(model)``
            always returns ``True``. An empty parameters collection returns
            ``False``, enabling idiomatic emptiness checks.

        Returns:
            bool: True if there are parameters, False if empty.

        Example:
            >>> params = ModelQueryParameters(items={"page": 1})
            >>> if params:
            ...     print("Has parameters")
            Has parameters

            >>> empty = ModelQueryParameters()
            >>> if not empty:
            ...     print("No parameters")
            No parameters
        """
        return bool(self.items)

    def __contains__(self, key: str) -> bool:
        """Check if parameter name exists."""
        return self.has(key)


__all__ = ["ModelQueryParameters", "QueryParameterValue"]
